"use client";

import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmVariant?: "danger" | "primary";
  onConfirm: () => void;
  isProcessing?: boolean;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  confirmVariant = "danger",
  onConfirm,
  isProcessing = false,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50 animate-fadeIn" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface border border-border rounded-panel p-5 shadow-dialog max-w-md w-full z-50 space-y-4 animate-scaleIn">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2.5">
              {confirmVariant === "danger" && (
                <div className="p-1.5 rounded-control bg-danger-bg text-danger-fg">
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                </div>
              )}
              <Dialog.Title className="text-sm font-semibold text-text-primary">
                {title}
              </Dialog.Title>
            </div>
            <Dialog.Close
              disabled={isProcessing}
              className="p-1 text-text-muted hover:text-text-primary rounded-control transition-colors"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </Dialog.Close>
          </div>

          <Dialog.Description className="text-xs text-text-secondary leading-relaxed">
            {description}
          </Dialog.Description>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
            <Dialog.Close asChild>
              <button
                type="button"
                disabled={isProcessing}
                className="px-3 py-1.5 text-xs font-medium rounded-control border border-border-default hover:bg-subtle text-text-secondary transition-colors"
              >
                Cancel
              </button>
            </Dialog.Close>
            <button
              type="button"
              disabled={isProcessing}
              onClick={onConfirm}
              className={`px-3 py-1.5 text-xs font-medium rounded-control transition-colors ${
                confirmVariant === "danger"
                  ? "bg-danger-fg text-white hover:bg-danger-fg/90"
                  : "bg-accent text-accent-fg hover:opacity-90"
              } disabled:opacity-50`}
            >
              {isProcessing ? "Processing..." : confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
