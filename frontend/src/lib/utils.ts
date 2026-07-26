import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names, with later Tailwind utilities winning over earlier ones.
 * `clsx` handles the conditionals, `twMerge` resolves conflicts like
 * `px-2 px-4` that plain string concatenation would leave both of.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
