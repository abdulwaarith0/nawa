"use client";

import { type HTMLAttributes, useMemo } from "react";
import "./styles.css";

export type IProps = HTMLAttributes<HTMLDivElement>;

// .nw-card — elevated surface (§9).
export default function Card({ children, className, ...props }: IProps) {
  const classes = useMemo(() => `nw-card${className ? ` ${className}` : ""}`, [className]);

  return (
    <div className={classes} {...props}>
      {children}
    </div>
  );
}
