import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const variants = cva("interactive inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold outline-none transition duration-200 focus-visible:ring-2 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-45 active:scale-[.98]", {
  variants: {
    variant: {
      primary: "bg-primary text-primary-foreground shadow-glow hover:bg-violet-500",
      secondary: "border border-border bg-white/[.05] text-foreground hover:bg-white/[.09]",
      ghost: "text-muted-foreground hover:bg-white/[.06] hover:text-foreground",
      danger: "bg-red-500/15 text-red-200 hover:bg-red-500/25"
    },
    size: { md: "h-10 px-4", sm: "h-8 px-3 text-xs", icon: "h-10 w-10 px-0" }
  },
  defaultVariants: { variant: "primary", size: "md" }
});

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> {}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => <button ref={ref} className={cn(variants({ variant, size }), className)} {...props} />);
Button.displayName = "Button";
