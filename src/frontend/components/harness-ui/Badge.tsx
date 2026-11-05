import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "purple" | "outline";
  className?: string;
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "default",
  className = "",
  size = "sm",
}) => {
  const base = "inline-flex items-center font-mono font-medium rounded-full border";
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";

  const variants = {
    default: "bg-zinc-800 text-zinc-300 border-zinc-700",
    success: "bg-emerald-950/60 text-emerald-300 border-emerald-800/80",
    warning: "bg-amber-950/60 text-amber-300 border-amber-800/80",
    error: "bg-rose-950/60 text-rose-300 border-rose-800/80",
    purple: "bg-indigo-950/60 text-indigo-300 border-indigo-800/80",
    outline: "bg-transparent text-zinc-400 border-zinc-700",
  };

  return (
    <span className={`${base} ${sizeClasses} ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
};
