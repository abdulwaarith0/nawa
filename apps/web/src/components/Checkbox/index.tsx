"use client";

import { type InputHTMLAttributes, type ReactNode, useId } from "react";
import "./styles.css";

export interface IProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: ReactNode;
}

// .nw-checkbox — native checkbox + optional inline label. Kept a plain
// <input type="checkbox"> (not a custom-rendered box) so it stays keyboard-
// and screen-reader-native for free.
export default function Checkbox({ label, id, className, ...props }: IProps) {
  const reactId = useId();
  const inputId = id ?? reactId;
  const input = (
    <input
      id={inputId}
      type="checkbox"
      className={`nw-checkbox${className ? ` ${className}` : ""}`}
      {...props}
    />
  );

  if (!label) return input;

  return (
    <label htmlFor={inputId} className="nw-checkbox-label">
      {input}
      {label}
    </label>
  );
}
