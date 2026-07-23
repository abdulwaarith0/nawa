// .nw-progress — onboarding bar / milestone meter (§9). Logical fill direction
// (follows reading direction), role=progressbar with a localized aria-valuetext.
export function Progress({
  value,
  max = 100,
  valueText,
  label,
}: {
  value: number;
  max?: number;
  valueText?: string;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      className="nw-progress"
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuetext={valueText}
      aria-label={label}
    >
      <div className="nw-progress-fill" style={{ inlineSize: `${pct}%` }} />
    </div>
  );
}
