import { Spinner } from "./Spinner";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

// .nw-btn — there is deliberately NO amber variant; AI actions use standard
// variants inside amber-attributed containers (§9). Loading swaps the label for
// a spinner while preserving width, and disables the button.
export function Button({
  variant = "primary",
  loading = false,
  disabled,
  children,
  className,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`nw-btn nw-btn-${variant}${className ? ` ${className}` : ""}`}
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
