from nawa_api.ai.pii import KnownEntities, PiiMapping, pseudonymize, rehydrate


def _roundtrip(text: str, known: KnownEntities) -> None:
    out, mapping = pseudonymize(text, known)
    assert rehydrate(out, mapping) == text


def test_roundtrip_english():
    text = "Amina El-Sayed (amina@example.qa, +974 3333 4444) leads Nawa Robotics."
    known = KnownEntities(
        persons=["Amina El-Sayed"], emails=["amina@example.qa"], orgs=["Nawa Robotics"]
    )
    _roundtrip(text, known)


def test_roundtrip_arabic_with_arabic_digits():
    text = "المؤسِّسة أمينة السيد، رقم الهاتف ٩٧٤٣٣٣٣٤٤٤٤ في واحة قطر."
    known = KnownEntities(persons=["أمينة السيد"], orgs=["واحة قطر"])
    _roundtrip(text, known)


def test_roundtrip_french_accents():
    text = "Le fondateur François Côté dirige Société Innov à Doha."
    known = KnownEntities(persons=["François Côté"], orgs=["Société Innov"])
    _roundtrip(text, known)


def test_roundtrip_mixed_direction():
    text = "Founder أمينة (email amina@x.io) — QID 12345678901 — joined Velocity."
    known = KnownEntities(persons=["أمينة"], emails=["amina@x.io"])
    _roundtrip(text, known)


def test_known_person_becomes_person_token():
    out, mapping = pseudonymize("Amina applied first.", KnownEntities(persons=["Amina"]))
    assert "PERSON_1" in out
    assert "Amina" not in out
    assert mapping.tokens["PERSON_1"] == "Amina"


def test_longest_match_first_replaces_full_name():
    out, mapping = pseudonymize(
        "Amina El-Sayed leads.", KnownEntities(persons=["Amina El-Sayed", "Amina"])
    )
    assert mapping.tokens["PERSON_1"] == "Amina El-Sayed"
    assert "Amina" not in out  # no dangling partial


def test_email_phone_org_id_categories():
    text = "mail me@x.io call +97433334444 at Nawa Labs, QID 12345678901"
    out, mapping = pseudonymize(text, KnownEntities(orgs=["Nawa Labs"]))
    prefixes = {t.split("_")[0] for t in mapping.tokens}
    assert {"EMAIL", "PHONE", "ORG", "ID"} <= prefixes
    assert rehydrate(out, mapping) == text


def test_stable_tokens_across_calls_with_prior():
    known = KnownEntities(persons=["Amina"])
    _, m1 = pseudonymize("Amina applied.", known)
    out2, m2 = pseudonymize("Amina scored well.", known, prior=m1)
    assert "PERSON_1" in out2
    assert m2.tokens["PERSON_1"] == "Amina"
    # No new PERSON token minted for the same subject.
    assert [t for t in m2.tokens if t.startswith("PERSON_")] == ["PERSON_1"]


def test_case_insensitive_detection_preserves_exact_span():
    out, mapping = pseudonymize("amina here", KnownEntities(persons=["Amina"]))
    assert "PERSON_1" in out
    assert mapping.tokens["PERSON_1"] == "amina"  # exact matched casing, round-trip safe
    assert rehydrate(out, mapping) == "amina here"


def test_multiple_distinct_persons_get_distinct_tokens():
    out, mapping = pseudonymize(
        "Amina and Zaid co-founded.", KnownEntities(persons=["Amina", "Zaid"])
    )
    assert mapping.tokens["PERSON_1"] != mapping.tokens["PERSON_2"]
    assert {"PERSON_1", "PERSON_2"} <= set(mapping.tokens)


def test_arabic_digit_phone_detected():
    out, mapping = pseudonymize("رقمي ٠٥٥١٢٣٤٥٦٧", KnownEntities())
    assert any(t.startswith("PHONE_") for t in mapping.tokens)
    assert rehydrate(out, mapping) == "رقمي ٠٥٥١٢٣٤٥٦٧"


def test_rehydrate_longest_token_first():
    mapping = PiiMapping(tokens={"PERSON_1": "Amina", "PERSON_10": "Zaid"})
    assert rehydrate("PERSON_10 and PERSON_1", mapping) == "Zaid and Amina"


def test_no_pii_leaves_text_untouched():
    out, mapping = pseudonymize("The rubric weights innovation at 40%.", KnownEntities())
    assert out == "The rubric weights innovation at 40%."
    assert mapping.tokens == {}


def test_blank_known_value_is_ignored():
    out, mapping = pseudonymize("Amina applied.", KnownEntities(persons=["Amina", "", "  "]))
    assert mapping.tokens["PERSON_1"] == "Amina"
    assert rehydrate(out, mapping) == "Amina applied."


def test_national_id_becomes_id_token_not_phone():
    out, mapping = pseudonymize("QID 12345678901 on file.", KnownEntities())
    assert any(t.startswith("ID_") for t in mapping.tokens)
    assert not any(t.startswith("PHONE_") for t in mapping.tokens)
