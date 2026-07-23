// .nw-avatar — image with an initials fallback. Never flips in RTL. Exactly one
// element carries the accessible name: the <img> (alt) when there's a src, else
// the wrapper (role=img + aria-label) for the initials.
export function Avatar({
  name,
  src,
  size = 40,
}: {
  name: string;
  src?: string | null;
  size?: number;
}) {
  const style = { inlineSize: size, blockSize: size };

  if (src) {
    return (
      <span className="nw-avatar" style={style}>
        <img src={src} alt={name} className="nw-avatar-img" width={size} height={size} />
      </span>
    );
  }

  const initials = name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p.charAt(0).toUpperCase())
    .join("");

  return (
    <span className="nw-avatar" style={style} role="img" aria-label={name}>
      <span className="nw-avatar-initials" aria-hidden="true">
        {initials}
      </span>
    </span>
  );
}
