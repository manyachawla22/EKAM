"use client";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useAppStore();
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleTheme}
      className={`h-8 w-8 ${className}`}
      aria-label="Toggle theme"
    >
      {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
