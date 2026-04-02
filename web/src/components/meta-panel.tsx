"use client";

import { Clock, Cpu, FileText, Image, Shield } from "lucide-react";
import type { ParseResult } from "@/lib/api";

export function MetaPanel({ result }: { result: ParseResult }) {
  const confidence = result.confidence ?? 0;
  const pageCount = (result.metadata?.page_count as number) ?? 1;
  const imageCount = result.images?.length ?? 0;

  return (
    <div className="border border-border rounded-xl bg-card p-4 space-y-3">
      <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Parse Info
      </h3>

      <div className="grid grid-cols-2 gap-3">
        <MetaStat
          icon={<Cpu className="w-3.5 h-3.5" />}
          label="Parser"
          value={result.parser_used}
          mono
        />
        <MetaStat
          icon={<Clock className="w-3.5 h-3.5" />}
          label="Time"
          value={`${result.elapsed_ms.toLocaleString()}ms`}
        />
        <MetaStat
          icon={<FileText className="w-3.5 h-3.5" />}
          label="Pages"
          value={pageCount.toString()}
        />
        {imageCount > 0 && (
          <MetaStat
            icon={<Image className="w-3.5 h-3.5" />}
            label="Images"
            value={imageCount.toString()}
          />
        )}
        <div>
          <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
            <Shield className="w-3.5 h-3.5" />
            <span className="text-[10px] uppercase tracking-wider font-medium">Confidence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full rounded-full animate-fill-bar"
                style={{
                  width: `${confidence * 100}%`,
                  backgroundColor:
                    confidence >= 0.7
                      ? "var(--chart-1)"
                      : confidence >= 0.4
                        ? "#eab308"
                        : "var(--destructive)",
                }}
              />
            </div>
            <span className="text-xs font-mono font-medium tabular-nums">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {result.metadata?.fallback_from ? (
        <div className="text-xs text-muted-foreground pt-1 border-t border-border">
          Fallback:{" "}
          {(result.metadata.fallback_from as Array<{ parser: string; reason: string }>)
            .map((f) => f.parser)
            .join(" → ")}{" "}
          → {result.parser_used}
        </div>
      ) : null}
    </div>
  );
}

function MetaStat({
  icon,
  label,
  value,
  mono,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
        {icon}
        <span className="text-[10px] uppercase tracking-wider font-medium">{label}</span>
      </div>
      <p className={`text-sm font-medium ${mono ? "font-mono" : ""}`}>{value}</p>
    </div>
  );
}
