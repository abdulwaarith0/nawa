"use client";

import { useId, useRef, useState } from "react";
import { useLocale } from "../../i18n/LocaleProvider";

export interface TabItem {
  id: string;
  label: React.ReactNode;
  content: React.ReactNode;
}

// .nw-tabs — underline tabs with roving tabindex + arrow-key navigation.
// ArrowRight moves visually right in BOTH locales (mapped to next/prev by dir).
export function Tabs({ items, initialId }: { items: TabItem[]; initialId?: string }) {
  const locale = useLocale();
  const isRtl = locale === "ar";
  const [active, setActive] = useState(initialId ?? items[0]?.id);
  const baseId = useId();
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  const focusByIndex = (index: number) => {
    const clamped = (index + items.length) % items.length;
    const target = items[clamped];
    /* v8 ignore next -- clamped is always a valid index for a non-empty tab set */
    if (!target) return;
    setActive(target.id);
    tabRefs.current[target.id]?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    // In RTL, ArrowRight should move to the PREVIOUS tab (visually right).
    const forward = isRtl ? -1 : 1;
    if (e.key === "ArrowRight") {
      e.preventDefault();
      focusByIndex(index + forward);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      focusByIndex(index - forward);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusByIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusByIndex(items.length - 1);
    }
  };

  return (
    <div className="nw-tabs">
      <div role="tablist" className="nw-tablist">
        {items.map((item, index) => {
          const selected = item.id === active;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${item.id}`}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              ref={(el) => {
                tabRefs.current[item.id] = el;
              }}
              className="nw-tab"
              data-selected={selected}
              onClick={() => setActive(item.id)}
              onKeyDown={(e) => onKeyDown(e, index)}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {items.map((item) => (
        <div
          key={item.id}
          role="tabpanel"
          id={`${baseId}-panel-${item.id}`}
          aria-labelledby={`${baseId}-tab-${item.id}`}
          hidden={item.id !== active}
          className="nw-tabpanel"
        >
          {item.content}
        </div>
      ))}
    </div>
  );
}
