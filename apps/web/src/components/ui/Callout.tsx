type Tone = "info" | "success";

const ICON: Record<Tone, string> = { info: "ℹ", success: "✓" };

// .nw-callout — static informational panel (§9). Never dismissible, never amber.
export function Callout({
  tone = "info",
  children,
}: {
  tone?: Tone;
  children: React.ReactNode;
}) {
  return (
    <div className="nw-callout" data-tone={tone} role="note">
      <span className="nw-callout-icon" aria-hidden="true">
        {ICON[tone]}
      </span>
      <div>{children}</div>
    </div>
  );
}
