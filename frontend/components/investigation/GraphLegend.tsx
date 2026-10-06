"use client";

import React from "react";
import { ENTITY_STYLES } from "@/lib/entityStyle";

interface GraphLegendProps {
  visibleTypes: string[];
}

export function GraphLegend({ visibleTypes }: GraphLegendProps) {
  if (visibleTypes.length === 0) return null;

  return (
    <div
      className="absolute bottom-3 left-3 z-20 bg-surface/95 backdrop-blur-sm border border-border rounded-panel p-2.5 text-[11px] max-w-xs shadow-sm space-y-1.5"
      role="region"
      aria-label="Graph Entity Legend"
    >
      <div className="text-[10px] uppercase font-mono font-semibold text-text-muted tracking-wider">
        Legend
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {visibleTypes.map((type) => {
          const style = ENTITY_STYLES[type.toLowerCase()] || {
            label: type,
            color: "#999999",
            shape: "ellipse",
          };

          return (
            <div key={type} className="flex items-center gap-1.5 min-w-0">
              <span
                className="w-2.5 h-2.5 shrink-0 rounded-xs border"
                style={{
                  backgroundColor: style.color,
                  borderColor: style.borderColor || "transparent",
                  borderRadius:
                    style.shape === "ellipse"
                      ? "9999px"
                      : style.shape === "round-rectangle"
                      ? "2px"
                      : "0px",
                }}
                aria-hidden="true"
              />
              <span className="truncate text-text-secondary text-[11px]">
                {style.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
