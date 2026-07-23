export function Card({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`nw-card${className ? ` ${className}` : ""}`} {...props}>
      {children}
    </div>
  );
}
