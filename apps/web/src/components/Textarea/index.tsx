"use client";

import { type TextareaHTMLAttributes, useId } from "react";
import "./styles.css";

export interface IProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

// .nw-textarea — same label-above/hint-error-below contract as Input (§9).
export default function Textarea({ label, hint, error, id, ...props }: IProps) {
  const reactId = useId();
  const textareaId = id ?? reactId;
  const errorId = `${textareaId}-error`;
  const hintId = `${textareaId}-hint`;
  const describedBy = error ? errorId : hint ? hintId : undefined;

  return (
    <div className="nw-field">
      {label ? (
        <label htmlFor={textareaId} className="nw-label">
          {label}
        </label>
      ) : null}
      <textarea
        id={textareaId}
        className={`nw-input nw-textarea${error ? " nw-input--error" : ""}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
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
