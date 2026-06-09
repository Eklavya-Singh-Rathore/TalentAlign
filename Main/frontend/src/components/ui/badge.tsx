import React from "react";
import { cn } from "../../lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "success" | "warning" | "danger" | "outline";
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "primary",
  ...props
}) => {
  const baseStyle = "inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider border transition-all h-fit";
  
  const variants = {
    primary: "bg-blue-50 text-blue-700 border-blue-200/60",
    secondary: "bg-slate-100 text-slate-700 border-slate-200/60",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200/60",
    warning: "bg-amber-50 text-amber-700 border-amber-200/60",
    danger: "bg-red-50 text-red-700 border-red-200/60",
    outline: "bg-transparent text-slate-600 border-slate-200",
  };

  return (
    <span className={cn(baseStyle, variants[variant], className)} {...props} />
  );
};
