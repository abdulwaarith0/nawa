"use client";

import { Routes } from "@nawa/contracts";
import { ClipboardCheck, Route, Sparkles, Users } from "lucide-react";
import { type ReactNode, useMemo } from "react";
import "./styles.css";

// The four product pillars, in lifecycle order (intake → journey → community →
// reports). Bilingual titles mirror the hero's AR/EN pairing; the landing is a
// public page shown before a locale is chosen, so both scripts appear together
// rather than through the console's locale switch.
interface Pillar {
  icon: ReactNode;
  titleEn: string;
  titleAr: string;
  body: string;
}

const PILLARS: Pillar[] = [
  {
    icon: <Sparkles size={20} aria-hidden="true" />,
    titleEn: "Intelligent intake",
    titleAr: "استقبال ذكي",
    body: "AI drafts an explainable, cited ranking of every applicant — you keep the decision, with a reason and an audit entry.",
  },
  {
    icon: <Route size={20} aria-hidden="true" />,
    titleEn: "Journey tracking",
    titleAr: "متابعة الرحلة",
    body: "Follow each cohort through its milestones, with member progress and an assistant grounded in program knowledge.",
  },
  {
    icon: <Users size={20} aria-hidden="true" />,
    titleEn: "Community hub",
    titleAr: "مجتمع مترابط",
    body: "A living directory of founders, mentors, and opportunities — so the network can ask for and offer help.",
  },
  {
    icon: <ClipboardCheck size={20} aria-hidden="true" />,
    titleEn: "Automated reporting",
    titleAr: "تقارير تلقائية",
    body: "Portfolio and venture KPIs drafted for you, ready for review and approval — no more manual roll-ups.",
  },
];

// The marketing / hub landing feature module (design-system §8 surface map).
// Public, bilingual, and built entirely on the shared `.nw-*` design system so
// it reads as the same product as the console behind sign-in.
export default function MarketingWrapper() {
  return useMemo(
    () => (
      <main className="nw-mkt">
        <section className="nw-mkt-hero">
          <span className="nw-mkt-eyebrow">
            <Sparkles size={13} aria-hidden="true" />
            نواة · NAWA
          </span>
          <h1 className="nw-mkt-title" lang="ar">
            منصة ذكاء اصطناعي واحدة لكل برامج واحة قطر للعلوم والتكنولوجيا
          </h1>
          <p className="nw-mkt-lede">
            One AI platform running the shared lifecycle behind every program — intelligent
            intake, cohort journey tracking, a community hub, and automated reporting, all on one
            Founder Profile spine.
          </p>
          <div className="nw-mkt-cta">
            <a className="nw-btn nw-btn-primary" href={Routes.requestAccess}>
              Apply · تقديم
            </a>
            <a className="nw-btn nw-btn-secondary" href={Routes.login}>
              Sign in · تسجيل الدخول
            </a>
          </div>
        </section>

        <section className="nw-mkt-pillars" aria-label="What Nawa does">
          {PILLARS.map((p) => (
            <article key={p.titleEn} className="nw-card nw-mkt-pillar">
              <span className="nw-mkt-pillar-icon">{p.icon}</span>
              <h2 className="nw-mkt-pillar-title">
                {p.titleEn}
                <span className="nw-mkt-pillar-title-ar" lang="ar">
                  {p.titleAr}
                </span>
              </h2>
              <p className="nw-mkt-pillar-body">{p.body}</p>
            </article>
          ))}
        </section>
      </main>
    ),
    [],
  );
}
