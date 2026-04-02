"use client";

import { DollarSign, TrendingDown } from "lucide-react";
import type { CostEstimate } from "@/lib/api";

export function CostPanel({ cost }: { cost: CostEstimate }) {
  const sorted = Object.entries(cost.cloud_costs).sort(([, a], [, b]) => a - b);
  const maxCost = Math.max(...sorted.map(([, v]) => v), cost.parsemux_cost_usd);

  return (
    <div className="border border-border rounded-xl bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Cost ({cost.page_count} {cost.page_count === 1 ? "page" : "pages"})
        </h3>
        {cost.savings_vs_cheapest_cloud > 0 && (
          <div className="flex items-center gap-1 text-[10px] font-medium text-green-500">
            <TrendingDown className="w-3 h-3" />
            Save ${cost.savings_vs_cheapest_cloud.toFixed(4)}
          </div>
        )}
      </div>

      <div className="space-y-1.5">
        {/* Parsemux row — highlighted */}
        <CostBar
          name="Parsemux"
          cost={cost.parsemux_cost_usd}
          maxCost={maxCost}
          highlight
        />
        {sorted.map(([name, value]) => (
          <CostBar key={name} name={name} cost={value} maxCost={maxCost} />
        ))}
      </div>
      <p className="text-[9px] text-muted-foreground/60 text-right">
        Cloud pricing as of Apr 2026
      </p>
    </div>
  );
}

function CostBar({
  name,
  cost,
  maxCost,
  highlight,
}: {
  name: string;
  cost: number;
  maxCost: number;
  highlight?: boolean;
}) {
  const pct = maxCost > 0 ? (cost / maxCost) * 100 : 0;

  return (
    <div className="flex items-center gap-2">
      <span
        className={`text-[10px] w-24 shrink-0 truncate ${highlight ? "font-semibold text-amber" : "text-muted-foreground"}`}
      >
        {name}
      </span>
      <div className="flex-1 h-3 bg-muted rounded-sm overflow-hidden">
        <div
          className={`h-full rounded-sm transition-all duration-500 ${highlight ? "bg-amber" : "bg-muted-foreground/30"}`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <span className="text-[10px] font-mono tabular-nums w-14 text-right text-muted-foreground">
        ${cost.toFixed(4)}
      </span>
    </div>
  );
}
