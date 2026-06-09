import React from "react";
import { cn } from "../../lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  ...props
}) => {
  const baseStyle = "inline-flex items-center justify-center font-semibold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-primary hover:bg-primary/90 text-white border border-primary/20 shadow-[0_4px_12px_rgba(79,125,243,0.15)] focus:ring-primary",
    secondary: "bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-200 focus:ring-slate-500",
    outline: "bg-transparent hover:bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300 focus:ring-slate-500",
    ghost: "bg-transparent hover:bg-slate-100 text-slate-500 hover:text-slate-800 focus:ring-slate-500",
    danger: "bg-destructive hover:bg-destructive/90 text-white border border-destructive/20 shadow-md focus:ring-destructive",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-5 py-2.5 text-md",
  };

  return (
    <button
      disabled={disabled || loading}
      className={cn(baseStyle, variants[variant], sizes[size], className)}
      {...props}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-2.5 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {children}
    </button>
  );
};
