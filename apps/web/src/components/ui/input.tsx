import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-10 w-full rounded-lg bg-surface-container-low px-3 text-body-default text-on-surface placeholder:text-outline focus:bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";
