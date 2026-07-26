import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "h-9 w-full rounded-sm bg-white px-3 text-sm text-grey-900 ring-1 ring-inset ring-grey-300",
          "placeholder:text-grey-400",
          "focus:ring-2 focus:ring-brand-500 focus:outline-none",
          "disabled:bg-grey-50 disabled:text-grey-400",
          className,
        )}
        {...props}
      />
    );
  },
);

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-sm bg-white px-3 py-2 text-sm text-grey-900 ring-1 ring-inset ring-grey-300",
        "placeholder:text-grey-400",
        "focus:ring-2 focus:ring-brand-500 focus:outline-none",
        className,
      )}
      {...props}
    />
  );
});

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label className={cn("block text-[13px] font-medium text-grey-700", className)} {...props} />
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint ? <p className="text-xs text-grey-500">{hint}</p> : null}
    </div>
  );
}
