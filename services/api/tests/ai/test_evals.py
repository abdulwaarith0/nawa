from sqlalchemy import select

from nawa_api.ai.evals import ground_truth as gt
from nawa_api.ai.evals import run as run_mod
from nawa_api.ai.evals.agreement import (
    compute_agreement,
    mean_abs_delta,
    spearman,
    top_quartile_agreement,
)
from nawa_api.ai.evals.hidden_gem import compute_gem_metrics
from nawa_api.ai.evals.run import (
    EvalSummary,
    format_summary,
    load_hidden_gems,
    load_scored_sample,
    main,
    run_evals,
)
from nawa_api.ai.evals.schemas import ScoredEntry
from nawa_api.ai.evals.slices import compute_slice_agreements
from nawa_api.models.ai import AiCall
from nawa_api.runtime.redis import get_redis

# --- pure metrics ----------------------------------------------------------


def test_agreement_perfect_and_reversed():
    assert top_quartile_agreement([4, 3, 2, 1], [4, 3, 2, 1]) == 100.0
    assert top_quartile_agreement([4, 3, 2, 1], [1, 2, 3, 4]) == 0.0


def test_spearman_perfect_and_reversed():
    assert spearman([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert spearman([1], [1]) == 0.0  # n < 2


def test_mean_abs_delta():
    assert mean_abs_delta([1.0, 2.0], [1.5, 2.5]) == 0.5
    assert mean_abs_delta([], []) == 0.0


def test_compute_agreement_bundles_all_three():
    result = compute_agreement([3, 2, 1], [3, 2, 1])
    assert result.agreement_pct == 100.0
    assert result.spearman == 1.0
    assert result.mean_delta == 0.0


def test_gem_recall_and_false_positive():
    result = compute_gem_metrics([True, True, False, False], [True, False, False, True])
    assert result.recall_pct == 50.0
    assert result.false_positive_pct == 50.0


def _entry(ref: str, language: str, overall: float) -> ScoredEntry:
    return ScoredEntry(
        application_ref=ref,
        text="t",
        human_scores={"x": overall},
        human_rank_band="mid",
        language=language,
        country="QA",
        gender="m",
        origin="urban",
    )


def test_slice_gap_and_bias_flag():
    entries = [
        _entry("a", "en", 9),
        _entry("b", "en", 8),
        _entry("c", "ar", 1),
        _entry("d", "ar", 2),
    ]
    human = [e.human_overall() for e in entries]
    ai_agree = [9, 8, 1, 2]  # en + ar both perfect internally → gap 0
    result = compute_slice_agreements(entries, human, ai_agree, key=lambda e: e.language)
    assert set(result.per_slice) == {"en", "ar"}
    assert result.max_gap == 0.0
    assert result.biased is False


# --- loaders + ground truth ------------------------------------------------


def test_golden_fixtures_load():
    scored = load_scored_sample()
    gems = load_hidden_gems()
    # 06-intake-copilot.md §8: ~40 scored entries, ~6 gems + ~6 controls.
    assert len(scored) >= 35
    assert len(gems) >= 10
    assert any(g.is_gem for g in gems) and any(not g.is_gem for g in gems)

    # Spread across languages (a golden set that's all fluent English
    # top-scorers cannot measure bias) — at least all three languages present,
    # and FR at roughly the seed's own ~10% ratio.
    languages = {e.language for e in scored}
    assert languages == {"ar", "en", "fr"}
    fr_count = sum(1 for e in scored if e.language == "fr")
    assert 2 <= fr_count <= len(scored) * 0.2

    # Score bands genuinely spread, not clustered at one end.
    bands = {e.human_rank_band for e in scored}
    assert {"top", "mid", "low"} <= bands

    # human_scores keyed by the REAL SoS rubric's criteria — required for
    # --module intake's real-pipeline validation to ever pass in --live mode.
    for entry in scored:
        assert set(entry.human_scores) == {
            "novelty",
            "feasibility",
            "capability",
            "regional_impact",
        }

    # At least half the true gems are Arabic prose (HiddenGemEntry has no
    # language field to check French directly — Arabic-script content is
    # the checkable proxy for "at least half Arabic or FR").
    true_gems = [g for g in gems if g.is_gem]
    assert len(true_gems) >= 3
    arabic_gems = [g for g in true_gems if any("؀" <= ch <= "ۿ" for ch in g.text)]
    assert len(arabic_gems) >= len(true_gems) / 2


async def test_ground_truth_none_when_absent(monkeypatch):
    async def fake_config():
        return {}

    monkeypatch.setattr(gt, "get_site_config", fake_config)
    assert await gt.load_ground_truth() is None


async def test_ground_truth_parses_dict_and_json(monkeypatch):
    async def fake_dict():
        return {"seed:ground_truth": {"hidden_gem_ids": ["a", "b"]}}

    monkeypatch.setattr(gt, "get_site_config", fake_dict)
    truth = await gt.load_ground_truth()
    assert truth.hidden_gem_ids == ["a", "b"]

    async def fake_json():
        return {"seed:ground_truth": '{"anomaly_profile_ids": {"stalled": ["p1"]}}'}

    monkeypatch.setattr(gt, "get_site_config", fake_json)
    truth = await gt.load_ground_truth()
    assert truth.anomaly_profile_ids == {"stalled": ["p1"]}


# --- run orchestration -----------------------------------------------------


def test_format_summary_shape():
    line = format_summary(
        EvalSummary(agreement=42.5, spearman=0.33, gem_recall=66.7, max_slice_gap=12.0)
    )
    assert line.startswith("AGREEMENT: 42.5% | SPEARMAN: 0.33 | GEM RECALL: 66.7% | MAX SLICE GAP:")


async def test_run_evals_with_injected_functions():
    scored = load_scored_sample()
    gems = load_hidden_gems()

    async def fake_scorer(entry):
        return entry.human_overall()  # perfect agreement

    async def fake_gemmer(entry):
        return entry.is_gem  # perfect recall

    summary = await run_evals(scored=scored, gems=gems, scorer=fake_scorer, gemmer=fake_gemmer)
    assert summary.agreement == 100.0
    assert summary.gem_recall == 100.0


async def test_offline_run_writes_eval_ai_calls(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)
    redis = get_redis()
    for key in await redis.keys("rl:ai:*"):
        await redis.delete(key)

    summary = await run_evals(scored=load_scored_sample(), gems=load_hidden_gems())
    line = format_summary(summary)
    for token in ("AGREEMENT:", "SPEARMAN:", "GEM RECALL:", "MAX SLICE GAP:"):
        assert token in line

    rows = (
        await db_session.execute(select(AiCall).where(AiCall.task.like("eval.%")))
    ).scalars().all()
    assert len(rows) >= 1
    assert all(r.cost_estimate is not None and r.latency_ms is not None for r in rows)


def test_main_offline_prints_summary_and_exits_zero(monkeypatch, capsys):
    async def fake_run(**kwargs):
        return EvalSummary(agreement=50.0, spearman=0.5, gem_recall=75.0, max_slice_gap=5.0)

    monkeypatch.setattr(run_mod, "run_evals", fake_run)
    code = main(["--offline"])
    assert code == 0
    assert "AGREEMENT: 50.0%" in capsys.readouterr().out


def test_main_prints_bias_warning_when_summary_flags_it(monkeypatch, capsys):
    async def fake_run(**kwargs):
        return EvalSummary(
            agreement=50.0, spearman=0.5, gem_recall=75.0, max_slice_gap=20.0, biased=True
        )

    monkeypatch.setattr(run_mod, "run_evals", fake_run)
    code = main(["--offline"])
    assert code == 0
    assert "BIAS WARNING" in capsys.readouterr().out


def test_main_live_requires_yes_spend():
    assert main(["--live"]) == 2  # refuses real spend without the flag


def test_main_module_intake_dispatches_to_the_real_pipeline_runner(monkeypatch, capsys):
    calls = {"intake": 0, "generic": 0}

    async def fake_intake_run(**kwargs):
        calls["intake"] += 1
        return EvalSummary(agreement=10.0, spearman=0.1, gem_recall=0.0, max_slice_gap=1.0)

    async def fake_generic_run(**kwargs):
        calls["generic"] += 1
        return EvalSummary(agreement=99.0, spearman=0.9, gem_recall=99.0, max_slice_gap=1.0)

    monkeypatch.setattr(run_mod, "run_intake_module_evals", fake_intake_run)
    monkeypatch.setattr(run_mod, "run_evals", fake_generic_run)

    code = main(["--offline", "--module", "intake"])
    assert code == 0
    assert calls == {"intake": 1, "generic": 0}
    assert "AGREEMENT: 10.0%" in capsys.readouterr().out


def test_main_default_module_is_the_generic_ai_path(monkeypatch, capsys):
    calls = {"intake": 0, "generic": 0}

    async def fake_intake_run(**kwargs):
        calls["intake"] += 1
        return EvalSummary(agreement=10.0, spearman=0.1, gem_recall=0.0, max_slice_gap=1.0)

    async def fake_generic_run(**kwargs):
        calls["generic"] += 1
        return EvalSummary(agreement=99.0, spearman=0.9, gem_recall=99.0, max_slice_gap=1.0)

    monkeypatch.setattr(run_mod, "run_intake_module_evals", fake_intake_run)
    monkeypatch.setattr(run_mod, "run_evals", fake_generic_run)

    code = main(["--offline"])
    assert code == 0
    assert calls == {"intake": 0, "generic": 1}


def test_main_against_seed_prints_seed_check_when_ground_truth_present(monkeypatch, capsys):
    async def fake_run(**kwargs):
        return EvalSummary(agreement=50.0, spearman=0.5, gem_recall=75.0, max_slice_gap=5.0)

    async def fake_ground_truth():
        return object()  # any non-None sentinel — check_against_seed is faked below

    from nawa_api.ai.evals.against_seed import SeedCheckResult

    async def fake_check(ground_truth):
        return SeedCheckResult(
            hidden_gem_recall_pct=60.0,
            hidden_gem_checked=5,
            dedup_recovered_pct=100.0,
            dedup_checked=9,
        )

    monkeypatch.setattr(run_mod, "run_evals", fake_run)
    monkeypatch.setattr(run_mod, "load_ground_truth", fake_ground_truth)
    monkeypatch.setattr(run_mod, "check_against_seed", fake_check)

    code = main(["--offline", "--against-seed"])
    assert code == 0
    out = capsys.readouterr().out
    assert "SEED CHECK: hidden-gem recall 60.0%" in out


def test_main_against_seed_reports_skip_when_no_ground_truth(monkeypatch, capsys):
    async def fake_run(**kwargs):
        return EvalSummary(agreement=50.0, spearman=0.5, gem_recall=75.0, max_slice_gap=5.0)

    async def fake_ground_truth():
        return None

    monkeypatch.setattr(run_mod, "run_evals", fake_run)
    monkeypatch.setattr(run_mod, "load_ground_truth", fake_ground_truth)

    code = main(["--offline", "--against-seed"])
    assert code == 0
    assert "SEED CHECK: skipped" in capsys.readouterr().out


async def test_module_intake_end_to_end_via_real_fixture(db_session, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from nawa_api.ai.evals.run import run_intake_module_evals

    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    monkeypatch.setattr("nawa_api.db.utils.session_factory", factory)

    # Two entries only — this exercises the real EvalFixture create/teardown
    # + score_application/_review_one path without the full ~40-entry set.
    summary = await run_intake_module_evals(
        scored=load_scored_sample()[:2], gems=load_hidden_gems()[:2], provider_name="mock"
    )
    line = format_summary(summary)
    for token in ("AGREEMENT:", "SPEARMAN:", "GEM RECALL:", "MAX SLICE GAP:"):
        assert token in line
