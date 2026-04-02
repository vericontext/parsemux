"use client";

import { Clock, Shield } from "lucide-react";
import type { ParseResult } from "@/lib/api";
import { ResultView } from "@/components/result-view";

export function CompareView({ results }: { results: ParseResult[] }) {
  if (results.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex gap-3 overflow-x-auto pb-2">
        {results.map((r) => (
          <div
            key={r.parser_used}
            className="flex items-center gap-3 px-4 py-2.5 bg-card border border-border rounded-lg shrink-0"
          >
            <span className="font-mono text-sm font-medium">{r.parser_used}</span>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="w-3 h-3" />
              {r.elapsed_ms}ms
            </div>
            <div className="flex items-center gap-1 text-xs">
              <Shield className="w-3 h-3 text-muted-foreground" />
              <span
                className={`font-mono ${
                  (r.confidence ?? 0) >= 0.7
                    ? "text-amber"
                    : (r.confidence ?? 0) >= 0.4
                      ? "text-yellow-500"
                      : "text-destructive"
                }`}
              >
                {((r.confidence ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Side-by-side results */}
      <div className={`grid gap-4 ${results.length === 2 ? "md:grid-cols-2" : results.length >= 3 ? "md:grid-cols-2 xl:grid-cols-3" : ""}`}>
        {results.map((r) => (
          <div key={r.parser_used} className="border border-border rounded-xl bg-card overflow-hidden">
            <div className="px-4 py-2.5 bg-muted/50 border-b border-border flex items-center justify-between">
              <span className="font-mono text-sm font-semibold">{r.parser_used}</span>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{r.elapsed_ms}ms</span>
                <span>·</span>
                <span>{((r.confidence ?? 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="p-4 max-h-[500px] overflow-y-auto">
              <ResultView content={r.content} format="markdown" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
