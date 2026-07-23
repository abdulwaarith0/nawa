import { useId } from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  // Opt-in dir="auto" for free-text fields where users may type either language.
  dirAuto?: boolean;
}

// .nw-input — label above, hint/error below, all text-align: start. Error state
// links the message to the input via aria-describedby and sets aria-invalid.
export function Input({ label, hint, error, dirAuto, id, ...props }: InputProps) {
  const reactId = useId();
  const inputId = id ?? reactId;
  const errorId = `${inputId}-error`;
  const hintId = `${inputId}-hint`;
  const describedBy = error ? errorId : hint ? hintId : undefined;

  return (
    <div className="nw-field">
      {label ? (
        <label htmlFor={inputId} className="nw-label">
          {label}
        </label>
      ) : null}
      <input
        id={inputId}
        className={`nw-input${error ? " nw-input--error" : ""}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        dir={dirAuto ? "auto" : undefined}
        {...props}
      />
      {error ? (
        <p id={errorId} className="nw-input-error-text" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={hintId} className="nw-hint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
