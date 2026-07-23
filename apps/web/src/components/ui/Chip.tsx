"use client";

import { useT } from "../../i18n/useT";

// .nw-chip — compact selectable/removable token (§9). States:
// default/selected/removable/disabled.
export function Chip({
  children,
  selected = false,
  disabled = false,
  onRemove,
  onSelect,
  removeLabel,
}: {
  children: React.ReactNode;
  selected?: boolean;
  disabled?: boolean;
  onRemove?: () => void;
  onSelect?: () => void;
  removeLabel?: string;
}) {
  const t = useT("common");
  const state = disabled ? "disabled" : selected ? "selected" : "default";
  return (
    <span className="nw-chip" data-state={state}>
      {onSelect ? (
        <button
          type="button"
          className="nw-chip-select"
          aria-pressed={selected}
          disabled={disabled}
          onClick={onSelect}
        >
          {children}
        </button>
      ) : (
        <span className="nw-chip-label">{children}</span>
      )}
      {onRemove ? (
        <button
          type="button"
          className="nw-chip-remove nw-icon-dir"
          aria-label={removeLabel ?? t("actions.close")}
          disabled={disabled}
          onClick={onRemove}
        >
          ✕
        </button>
      ) : null}
    </span>
  );
}
