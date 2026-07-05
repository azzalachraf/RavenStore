import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-border bg-black/20 px-3 text-sm text-foreground shadow-inner outline-none transition duration-200 hover:border-white/20 focus:border-primary/60 focus:ring-2 focus:ring-primary/20 placeholder:text-muted-foreground",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
