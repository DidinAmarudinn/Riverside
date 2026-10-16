import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full font-body-medium font-semibold text-body-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-on-primary hover:bg-[#1c3d30]",
        teal: "bg-brand-teal text-white shadow-sm hover:bg-brand-teal-dark",
        secondary:
          "bg-surface-container-low text-on-surface hover:bg-surface-container-high",
        outline:
          "bg-transparent text-on-surface shadow-[inset_0_0_0_1.5px_var(--color-on-surface)] hover:bg-surface-container-low",
        ghost:
          "text-on-surface-variant hover:bg-surface-container hover:text-on-surface",
        danger: "bg-error text-on-error hover:brightness-95",
        success:
          "bg-status-green text-white shadow-sm hover:brightness-95",
      },
      size: {
        sm: "h-8 px-3.5 text-caption",
        md: "h-10 px-5",
        lg: "h-12 px-6 text-headline-sm",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { buttonVariants };
