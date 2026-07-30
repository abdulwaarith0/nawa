"use client";

import { formatDate } from "@/helpers/format";
import { useNotifications } from "@/hooks/Notifications";
import { useLocale } from "@/i18n/LocaleProvider";
import { useT } from "@/i18n/useT";
import { Bell } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

// Top-bar notification bell (design AppShell): unread dot + dropdown feed.
// Reads the real /notifications stream (see useNotifications for the backend
// contract). Shows the caught-up empty state until entries exist — no
// fabricated notices.
export default function NotificationBell() {
  const t = useT("console");
  const locale = useLocale();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  const onOpenNotice = useCallback(
    (id: string) => {
      markRead(id);
      setOpen(false);
    },
    [markRead],
  );

  const label =
    unreadCount > 0
      ? `${t("notifications.label")} — ${t("notifications.unread", { count: unreadCount })}`
      : t("notifications.label");

  return (
    <div className="nw-notif" ref={ref}>
      <button
        type="button"
        className="nw-notif-trigger"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Bell size={19} strokeWidth={1.7} aria-hidden="true" />
        {unreadCount > 0 ? <span className="nw-notif-dot" aria-hidden="true" /> : null}
      </button>
      {open ? (
        <div className="nw-notif-menu" role="menu">
          <div className="nw-notif-head">
            <span className="nw-notif-title">{t("notifications.title")}</span>
            {unreadCount > 0 ? (
              <button type="button" className="nw-notif-markall" onClick={() => markAllRead()}>
                {t("notifications.markAllRead")}
              </button>
            ) : null}
          </div>
          {notifications.length === 0 ? (
            <p className="nw-notif-empty">{t("notifications.empty")}</p>
          ) : (
            <ul className="nw-notif-list">
              {notifications.map((n) => {
                const inner = (
                  <>
                    {n.unread ? <span className="nw-notif-unread-dot" aria-hidden="true" /> : null}
                    <span className="nw-notif-item-txt">
                      <span className="nw-notif-item-title">{n.title}</span>
                      <span className="nw-notif-item-body">{n.body}</span>
                      <span className="nw-notif-item-time">
                        {formatDate(n.created_at, locale, {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                          hour12: false,
                        })}
                      </span>
                    </span>
                  </>
                );
                return (
                  <li key={n.id} data-unread={n.unread || undefined}>
                    {n.href ? (
                      <Link
                        href={n.href}
                        role="menuitem"
                        className="nw-notif-item"
                        onClick={() => onOpenNotice(n.id)}
                      >
                        {inner}
                      </Link>
                    ) : (
                      <button
                        type="button"
                        role="menuitem"
                        className="nw-notif-item"
                        onClick={() => markRead(n.id)}
                      >
                        {inner}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
