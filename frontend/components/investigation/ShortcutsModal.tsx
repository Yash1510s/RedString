"use client";

import React from "react";
import { X, Command, Keyboard } from "lucide-react";

interface ShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ShortcutsModal({ isOpen, onClose }: ShortcutsModalProps) {
  if (!isOpen) return null;

  const shortcuts = [
    { key: "1", description: "Switch to Overview tab" },
    { key: "2", description: "Switch to Relationship Graph tab" },
    { key: "3", description: "Switch to All Findings table" },
    { key: "4", description: "Switch to Certificates table" },
    { key: "5", description: "Switch to Technologies table" },
    { key: "6", description: "Switch to Repositories table" },
    { key: "7", description: "Switch to AI Grounded Summary" },
    { key: "T", description: "Toggle between Canvas and Accessible Table view" },
    { key: "R", description: "Regenerate AI grounded summary" },
    { key: "E", description: "Export printable report in new tab" },
    { key: "?", description: "Open/close this keyboard shortcuts dialog" },
    { key: "Esc", description: "Clear node selection or close dialog" },
  ];

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-panel max-w-md w-full p-5 space-y-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-accent" />
            <h2 id="shortcuts-title" className="text-sm font-semibold font-mono uppercase tracking-wider text-text-primary">
              Analyst Keyboard Shortcuts
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-text-primary p-1 rounded-control hover:bg-subtle transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="divide-y divide-border-subtle max-h-80 overflow-y-auto">
          {shortcuts.map((sc) => (
            <div key={sc.key} className="py-2 flex items-center justify-between text-xs">
              <span className="text-text-secondary">{sc.description}</span>
              <kbd className="px-2 py-0.5 font-mono text-[11px] font-semibold bg-canvas border border-border-default rounded text-accent shadow-xs">
                {sc.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="pt-2 border-t border-border flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs font-mono rounded-control bg-subtle hover:bg-hover border border-border-default text-text-primary transition-colors"
          >
            Got it (Esc)
          </button>
        </div>
      </div>
    </div>
  );
}
