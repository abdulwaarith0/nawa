// Inline loading spinner. Non-directional (never flips in RTL).

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="nw-spinner" role="status" aria-live="polite" aria-label={label}>
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <circle
          cx="8"
          cy="8"
          r="6"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeDasharray="28"
          strokeDashoffset="10"
        />
      </svg>
    </span>
  );
}
