"use client";

import { type CSSProperties, useMemo } from "react";
import "./styles.css";

export interface IProps {
  name: string;
  src?: string | null;
  size?: number;
}

// .nw-avatar — image with an initials fallback. Never flips in RTL. Exactly one
// element carries the accessible name: the <img> (alt) when there's a src, else
// the wrapper (role=img + aria-label) for the initials.
export default function Avatar({ name, src, size = 40 }: IProps) {
  const style = useMemo<CSSProperties>(() => ({ inlineSize: size, blockSize: size }), [size]);

  const initials = useMemo(
    () =>
      name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((p) => p.charAt(0).toUpperCase())
        .join(""),
    [name],
  );

  return useMemo(() => {
    if (src) {
      return (
        <span className="nw-avatar" style={style}>
          <img src={src} alt={name} className="nw-avatar-img" width={size} height={size} />
        </span>
      );
    }

    return (
      <span className="nw-avatar" style={style} role="img" aria-label={name}>
        <span className="nw-avatar-initials" aria-hidden="true">
          {initials}
        </span>
      </span>
    );
  }, [src, name, size, style, initials]);
}
