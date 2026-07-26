import { Slot } from "@radix-ui/react-slot";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Fireflies' buttons are squared off — a 4px radius, not a pill. That single
 * value does more for the visual match than any other token.
 */
const VARIANTS = {
  primary: "bg-brand-500 text-white hover:bg-brand-700 disabled:bg-brand-300",
  secondary:
    "bg-white text-grey-700 ring-1 ring-inset ring-grey-300 hover:bg-grey-50 disabled:text-grey-400",
  ghost: "bg-transparent text-grey-600 hover:bg-grey-100 hover:text-grey-900",
  subtle: "bg-brand-50 text-brand-700 hover:bg-brand-100",
  danger: "bg-danger-600 text-white hover:bg-danger-700",
} as const;

const SIZES = {
  sm: "h-8 px-3 text-[13px] gap-1.5",
  md: "h-9 px-3.5 text-sm gap-2",
  lg: "h-10 px-4 text-sm gap-2",
  icon: "h-8 w-8 justify-center",
} as const;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
  /** Render as the child element instead of a <button> — used for links. */
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", size = "md", asChild, ...props },
  ref,
) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-sm font-medium transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500",
        "disabled:cursor-not-allowed disabled:opacity-70",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  );
});
