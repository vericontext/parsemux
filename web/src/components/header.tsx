"use client";

import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchHealth } from "@/lib/api";
import { Moon, Sun, Zap, GitBranch, Star } from "lucide-react";
import { useEffect, useState } from "react";

interface HealthState {
  version: string;
  parsers: number;
  mode: string;
  limits: { max_file_size_mb: number; rate_limit_per_min: number; max_pages: number } | null;
}

export function Header() {
  const { theme, toggle } = useTheme();
  const [health, setHealth] = useState<HealthState | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) =>
        setHealth({
          version: h.version,
          parsers: h.parsers_available,
          mode: h.mode,
          limits: h.limits,
        })
      )
      .catch(() => setHealth(null));
  }, []);

  return (
    <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-amber flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="font-semibold text-lg tracking-tight">parsemux</span>
          </div>
          {health && (
            <Badge variant="secondary" className="font-mono text-xs hidden sm:inline-flex">
              v{health.version} · {health.parsers} parsers
            </Badge>
          )}
          {health?.mode === "demo" && (
            <Badge
              variant="secondary"
              className="bg-amber/15 text-amber border-amber/30 text-xs hidden sm:inline-flex cursor-default"
              title={
                health.limits
                  ? `${health.limits.max_file_size_mb}MB max · ${health.limits.rate_limit_per_min} req/min · ${health.limits.max_pages} pages max`
                  : "Demo mode"
              }
            >
              Demo
            </Badge>
          )}
          {!health && (
            <Badge variant="destructive" className="font-mono text-xs hidden sm:inline-flex">
              API offline
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          <a
            href="https://github.com/vericontext/parsemux"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center gap-1.5 h-8 px-3 rounded-md text-xs font-medium border border-border hover:bg-accent transition-colors"
          >
            <Star className="w-3.5 h-3.5" />
            Star on GitHub
          </a>
          <a
            href="https://x.com/vericontext"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Follow on X"
            className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
          </a>
          <a
            href="https://github.com/vericontext/parsemux"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            className="inline-flex items-center justify-center h-8 w-8 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground sm:hidden"
          >
            <GitBranch className="w-4 h-4" />
          </a>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={toggle}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </Button>
        </div>
      </div>
    </header>
  );
}
