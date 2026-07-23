// The single source of breakpoint constants (design-system §12). Media-query
// literals live only in styles/base.css, anchored to these values.

export const BREAKPOINTS = {
  tablet: 768,
  desktop: 1024,
  wide: 1280,
} as const;
