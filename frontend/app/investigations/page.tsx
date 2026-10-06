"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  Trash2,
  ExternalLink,
  RefreshCw,
  Plus,
  PlayCircle,
  Filter,
} from "lucide-react";
import {
  listInvestigations,
  deleteInvestigation,
  createDemoInvestigation,
  InvestigationItem,
} from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

export default function InvestigationsHistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<InvestigationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const [deleteTarget, setDeleteTarget] = useState<InvestigationItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);

  const loadList = useCallback(async () => {
    try {
      setLoading(true);
      const res = await listInvestigations();
      setItems(res);
    } catch (err) {
      console.error("Failed to load investigations history:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setIsDeleting(true);
      await deleteInvestigation(deleteTarget.id);
      setItems((prev) => prev.filter((i) => i.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      console.error("Failed to delete investigation:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSeedDemo = async () => {
    try {
      setIsSeedingDemo(true);
      const demo = await createDemoInvestigation();
      router.push(`/investigations/${demo.id}`);
    } catch (err) {
      console.error("Failed to seed demo investigation:", err);
      setIsSeedingDemo(false);
    }
  };

  const filteredItems = useMemo(() => {
    let list = items;
    if (statusFilter !== "all") {
      list = list.filter((i) => i.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((i) => i.target.toLowerCase().includes(q));
    }
    return list;
  }, [items, statusFilter, search]);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-5xl mx-auto w-full space-y-6">
      {/* Header and Quick Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-base font-semibold text-text-primary tracking-tight">
            Investigation History
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            Audit history of passive investigation runs and stored evidence trails.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSeedDemo}
            disabled={isSeedingDemo}
            className="px-3 py-1.5 text-xs font-mono rounded-control border border-border-default hover:bg-subtle text-text-secondary flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Seed an offline pre-correlated demo investigation"
          >
            <PlayCircle className="w-3.5 h-3.5 text-accent" />
            <span>{isSeedingDemo ? "Seeding..." : "Load Demo Data"}</span>
          </button>

          <Link
            href="/"
            className="px-3 py-1.5 text-xs font-medium rounded-control bg-accent text-accent-fg hover:opacity-90 flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Investigation</span>
          </Link>
        </div>
      </div>

      {/* Toolbar: Search and Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-surface p-3 border border-border rounded-panel">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search targets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs rounded-control bg-canvas border border-border-default focus:border-accent font-mono text-text-primary"
          />
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-text-muted font-mono text-[11px] flex items-center gap-1">
            <Filter className="w-3 h-3" /> Status:
          </span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-control bg-canvas border border-border-default text-text-secondary focus:border-accent"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <button
            type="button"
            onClick={loadList}
            className="p-1.5 rounded-control border border-border-default hover:bg-subtle text-text-muted hover:text-text-primary"
            title="Refresh list"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Dense History Table */}
      {loading ? (
        <div className="p-12 text-center text-xs text-text-muted font-mono animate-pulse">
          Loading investigation records...
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 text-center text-xs text-text-muted border border-dashed border-border rounded-panel bg-surface space-y-3">
          <p>No investigations match the current filter criteria.</p>
          <div className="flex items-center justify-center gap-2 pt-2">
            <Link
              href="/"
              className="text-accent hover:underline font-mono text-xs"
            >
              Start a new investigation →
            </Link>
          </div>
        </div>
      ) : (
        <div className="border border-border rounded-panel bg-surface overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider font-mono">
                <th className="py-2.5 px-3">Target</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Started</th>
                <th className="py-2.5 px-3">Findings</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {filteredItems.map((inv) => (
                <tr
                  key={inv.id}
                  className="hover:bg-subtle/50 transition-colors"
                >
                  <td className="py-2.5 px-3 font-mono font-medium text-text-primary">
                    <Link
                      href={`/investigations/${inv.id}`}
                      className="hover:text-accent hover:underline"
                    >
                      {inv.target}
                    </Link>
                  </td>
                  <td className="py-2.5 px-3 capitalize text-text-secondary text-[11px]">
                    {inv.target_type}
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-control text-[10px] font-medium capitalize ${
                        inv.status === "completed"
                          ? "text-success-fg bg-success-bg"
                          : inv.status === "running"
                          ? "text-accent bg-info-bg"
                          : inv.status === "failed"
                          ? "text-danger-fg bg-danger-bg"
                          : "text-text-muted bg-canvas border border-border-subtle"
                      }`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-text-muted font-mono text-[11px]">
                    {new Date(inv.created_at).toUTCString()}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-text-secondary">
                    {inv.findings_count} entities
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link
                        href={`/investigations/${inv.id}`}
                        className="p-1 text-text-muted hover:text-accent rounded-control hover:bg-subtle"
                        title="Open workspace"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(inv)}
                        className="p-1 text-text-muted hover:text-danger-fg rounded-control hover:bg-danger-bg"
                        title="Delete investigation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Investigation?"
        description={`This removes all findings, relations, and raw evidence records collected for "${deleteTarget?.target}". This action is permanent and cannot be undone.`}
        confirmLabel="Delete Permanently"
        confirmVariant="danger"
        isProcessing={isDeleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
