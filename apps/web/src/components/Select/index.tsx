"use client";

import { type ReactNode, type SelectHTMLAttributes, useId } from "react";
import "./styles.css";

export interface SelectOption {
  value: string;
  label: ReactNode;
}

export interface IProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  options: SelectOption[];
}

// .nw-select — same label/hint/error shell as Input (§9), styled as a select.
export default function Select({ label, hint, error, options, id, ...props }: IProps) {
  const reactId = useId();
  const selectId = id ?? reactId;
  const errorId = `${selectId}-error`;
  const hintId = `${selectId}-hint`;
  const describedBy = error ? errorId : hint ? hintId : undefined;

  return (
    <div className="nw-field">
      {label ? (
        <label htmlFor={selectId} className="nw-label">
          {label}
        </label>
      ) : null}
      <select
        id={selectId}
        className={`nw-select${error ? " nw-select--error" : ""}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
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
