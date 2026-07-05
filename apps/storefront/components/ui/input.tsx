import * as React from "react";
import { cn } from "@/lib/utils";
export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => <input ref={ref} className={cn("h-11 w-full rounded-md border border-border bg-black/20 px-3 text-sm shadow-inner outline-none transition duration-200 placeholder:text-muted-foreground hover:border-white/20 focus:border-violet-400/60 focus:ring-2 focus:ring-violet-400/15", className)} {...props} />);
Input.displayName = "Input";
