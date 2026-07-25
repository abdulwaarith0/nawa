"use client";

import { Loading } from "@/components";
import { nextTarget } from "@/helpers/nextTarget";
import { useSession } from "@/hooks/Auth";
import { useT } from "@/i18n/useT";
import LocaleSwitcher from "@/layouts/LocaleSwitcher";
import { Routes } from "@nawa/contracts";
import { Check, ShieldCheck } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useMemo } from "react";
import "./styles.css";

export interface IProps {
  children: ReactNode;
  // Which auth.json top-level key's `story.*` block to render in the right panel.
  storyKey: "login" | "requestAccess";
}

// Full-bleed split-panel auth shell (design-qa.md / design-qa-request-access.md,
// ported from the approved apps/console design), used by both /login and
// /request-access. Guest-only (§13): a signed-in user landing here is bounced
// to their permission-based home before the form ever renders — no flash of
// the form. The edge middleware already does this for the common case; this
// is the client-side fallback (e.g. a session established after the page
// already streamed).
export default function AuthShell({ children, storyKey }: IProps) {
  const { user, isLoading, isSignedIn } = useSession();
  const router = useRouter();
  const t = useT("auth");

  useEffect(() => {
    if (!isLoading && isSignedIn) {
      router.replace(nextTarget(user?.effective));
    }
  }, [isLoading, isSignedIn, user, router]);

  const story = useMemo(
    () => ({
      eyebrow: t(`${storyKey}.story.eyebrow`),
      heading: t(`${storyKey}.story.heading`),
      lede: t(`${storyKey}.story.lede`),
      benefits: [
        t(`${storyKey}.story.benefit1`),
        t(`${storyKey}.story.benefit2`),
        t(`${storyKey}.story.benefit3`),
      ],
      trust: t(`${storyKey}.story.trust`),
    }),
    [t, storyKey],
  );

  return useMemo(() => {
    const showForm = !isLoading && !isSignedIn;
    return (
      <main className="nw-auth-page">
        <section className="nw-auth-shell">
          <div className="nw-auth-form-panel">
            <div className="nw-auth-topline">
              <a href={Routes.home} className="nw-auth-brand" lang="en">
                <img src="/brand/nawa-emblem.svg" alt="" />
                <span>Nawa</span>
              </a>
              <LocaleSwitcher />
            </div>
            <div className="nw-auth-form-wrap">{showForm ? children : <Loading />}</div>
          </div>

          <aside className="nw-auth-story" aria-label={story.eyebrow}>
            <div className="nw-auth-story-copy">
              <p className="nw-auth-story-eyebrow">{story.eyebrow}</p>
              <h2>{story.heading}</h2>
              <p className="nw-auth-story-lede">{story.lede}</p>
              <ul className="nw-auth-benefits">
                {story.benefits.map((benefit) => (
                  <li key={benefit}>
                    <span aria-hidden="true">
                      <Check size={14} />
                    </span>
                    {benefit}
                  </li>
                ))}
              </ul>
              <div className="nw-auth-trust">
                <ShieldCheck size={17} aria-hidden="true" />
                {story.trust}
              </div>
            </div>
            <figure className="nw-auth-preview">
              <figcaption>
                <span>{story.eyebrow}</span>
                <span className="nw-auth-live">
                  <i />
                </span>
              </figcaption>
              <Image
                src="/auth/nawa-dashboard-preview.png"
                alt=""
                width={2190}
                height={1165}
                priority
              />
            </figure>
          </aside>
        </section>
      </main>
    );
  }, [children, isLoading, isSignedIn, story]);
}
