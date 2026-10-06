"use client";

import React, { useState } from "react";
import { Filter, ChevronDown, ChevronUp } from "lucide-react";
import { ENTITY_STYLES } from "@/lib/entityStyle";

interface GraphFilterPanelProps {
  availableTypes: string[];
  selectedTypes: Set<string>;
  onToggleType: (type: string) => void;
  onSelectAllTypes: () => void;
  onClearTypes: () => void;
  selectedConfidence: Set<string>;
  onToggleConfidence: (conf: string) => void;
}

export function GraphFilterPanel({
  availableTypes,
  selectedTypes,
  onToggleType,
  onSelectAllTypes,
  onClearTypes,
  selectedConfidence,
  onToggleConfidence,
}: GraphFilterPanelProps) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div
      className="absolute top-3 left-3 z-20 bg-surface/95 backdrop-blur-sm border border-border rounded-panel text-xs shadow-sm max-w-[220px] w-full overflow-hidden transition-all"
      role="region"
      aria-label="Graph Filter Controls"
    >
      {/* Header / Toggle Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2.5 bg-canvas/60 hover:bg-canvas text-left font-medium text-text-primary transition-colors border-b border-border-subtle"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          <Filter className="w-3.5 h-3.5 text-accent" />
          <span>Filters</span>
          <span className="text-text-muted text-[10px]">
            ({selectedTypes.size}/{availableTypes.length})
          </span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-3.5 h-3.5 text-text-muted" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
        )}
      </button>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="p-2.5 space-y-3 max-h-72 overflow-y-auto">
          {/* Entity Types Section */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[10px] uppercase font-mono text-text-muted tracking-wider">
              <span>Entity Types</span>
              <div className="flex items-center gap-1.5 font-sans lowercase text-[10px]">
                <button
                  type="button"
                  onClick={onSelectAllTypes}
                  className="text-accent hover:underline"
                >
                  all
                </button>
                <span>·</span>
                <button
                  type="button"
                  onClick={onClearTypes}
                  className="text-text-muted hover:underline"
                >
                  none
                </button>
              </div>
            </div>

            <div className="space-y-1">
              {availableTypes.map((type) => {
                const checked = selectedTypes.has(type);
                const style = ENTITY_STYLES[type.toLowerCase()] || {
                  label: type,
                  color: "#999999",
                };

                return (
                  <label
                    key={type}
                    className="flex items-center gap-2 px-1 py-0.5 rounded-control hover:bg-subtle cursor-pointer select-none text-[11px]"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleType(type)}
                      className="rounded-control border-border-default text-accent focus:ring-accent w-3 h-3"
                    />
                    <span
                      className="w-2 h-2 rounded-xs shrink-0"
                      style={{ backgroundColor: style.color }}
                      aria-hidden="true"
                    />
                    <span className="truncate text-text-secondary">
                      {style.label}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Confidence Section */}
          <div className="space-y-1.5 pt-2 border-t border-border-subtle">
            <div className="text-[10px] uppercase font-mono text-text-muted tracking-wider">
              Confidence
            </div>
            <div className="space-y-1">
              {["high", "medium", "low"].map((conf) => {
                const checked = selectedConfidence.has(conf);
                return (
                  <label
                    key={conf}
                    className="flex items-center gap-2 px-1 py-0.5 rounded-control hover:bg-subtle cursor-pointer select-none text-[11px]"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleConfidence(conf)}
                      className="rounded-control border-border-default text-accent focus:ring-accent w-3 h-3"
                    />
                    <span className="capitalize text-text-secondary">
                      {conf} Confidence
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
