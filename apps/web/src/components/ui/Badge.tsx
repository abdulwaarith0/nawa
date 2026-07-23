type Tone = "neutral" | "success" | "warning" | "danger" | "info";

// .nw-badge — semantic variants use *-100 bg + *-700 text. The AI badge is a
// separate component (never here), keeping the amber rule intact (§9).
export function Badge({
  tone = "neutral",
  icon,
  children,
}: {
  tone?: Tone;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <span className="nw-badge" data-tone={tone}>
      {icon}
      {children}
    </span>
  );
}
