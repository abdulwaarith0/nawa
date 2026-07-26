"use client";

import Spinner from "@/components/Spinner";
import { type ButtonHTMLAttributes, useMemo } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline";

export interface IProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

// .nw-btn — there is deliberately NO amber variant; AI actions use standard
// variants inside amber-attributed containers (§9). Loading swaps the label for
// a spinner while preserving width, and disables the button.
export default function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  className,
  type = "button",
  ...props
}: IProps) {
  const classes = useMemo(
    () => `nw-btn nw-btn-${variant}${className ? ` ${className}` : ""}`,
    [variant, className],
  );

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <>
          <Spinner />
          <span style={{ visibility: "hidden", position: "absolute" }}>{children}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}
