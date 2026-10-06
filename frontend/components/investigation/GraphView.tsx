"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import cytoscape, { Core, EventObject } from "cytoscape";
import {
  Search,
  Maximize2,
  Image as ImageIcon,
  Table2,
  Layers,
  ZoomIn,
  ZoomOut,
  RefreshCw,
} from "lucide-react";
import { InvestigationGraphData, GraphNodeData, GraphEdgeData } from "@/lib/api";
import { ENTITY_STYLES } from "@/lib/entityStyle";
import { GraphFilterPanel } from "./GraphFilterPanel";
import { GraphLegend } from "./GraphLegend";

interface GraphViewProps {
  graphData: InvestigationGraphData;
  onSelectEntity: (entityId: number, findingId: string) => void;
  selectedEntityId?: number | null;
  className?: string;
}

export function GraphView({
  graphData,
  onSelectEntity,
  selectedEntityId,
  className = "",
}: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [layoutName, setLayoutName] = useState<"cose" | "concentric">("cose");
  const [searchTerm, setSearchTerm] = useState("");
  const [showTableAlternative, setShowTableAlternative] = useState(false);

  // Filter states
  const allAvailableTypes = useMemo(() => {
    const types = new Set<string>();
    graphData.nodes.forEach((n) => types.add(n.data.type));
    return Array.from(types).sort();
  }, [graphData.nodes]);

  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedConfidence, setSelectedConfidence] = useState<Set<string>>(
    new Set(["high", "medium", "low"])
  );

  // Initialize selected types when graphData changes
  useEffect(() => {
    setSelectedTypes(new Set(allAvailableTypes));
  }, [allAvailableTypes]);

  const toggleType = (t: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) {
        next.delete(t);
      } else {
        next.add(t);
      }
      return next;
    });
  };

  const selectAllTypes = () => setSelectedTypes(new Set(allAvailableTypes));
  const clearTypes = () => setSelectedTypes(new Set());

  const toggleConfidence = (c: string) => {
    setSelectedConfidence((prev) => {
      const next = new Set(prev);
      if (next.has(c)) {
        next.delete(c);
      } else {
        next.add(c);
      }
      return next;
    });
  };

  // Filter nodes & edges
  const filteredNodes = useMemo(() => {
    return graphData.nodes.filter((node) => {
      const matchType = selectedTypes.has(node.data.type);
      const matchSearch =
        !searchTerm.trim() ||
        node.data.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        node.data.findingId.toLowerCase().includes(searchTerm.toLowerCase());
      return matchType && matchSearch;
    });
  }, [graphData.nodes, selectedTypes, searchTerm]);

  const visibleNodeIds = useMemo(() => {
    return new Set(filteredNodes.map((n) => n.data.id));
  }, [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return graphData.edges.filter((edge) => {
      const sourceVisible = visibleNodeIds.has(edge.data.source);
      const targetVisible = visibleNodeIds.has(edge.data.target);
      const confVisible = selectedConfidence.has(edge.data.confidence);
      return sourceVisible && targetVisible && confVisible;
    });
  }, [graphData.edges, visibleNodeIds, selectedConfidence]);

  // Types currently visible on canvas
  const visibleTypes = useMemo(() => {
    const types = new Set<string>();
    filteredNodes.forEach((n) => types.add(n.data.type));
    return Array.from(types);
  }, [filteredNodes]);

  // Initialize / update Cytoscape instance
  useEffect(() => {
    if (showTableAlternative || !containerRef.current) return;

    // Clean up previous cy instance if exists
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements: cytoscape.ElementDefinition[] = [
      ...filteredNodes.map((n) => ({
        group: "nodes" as const,
        data: n.data,
      })),
      ...filteredEdges.map((e) => ({
        group: "edges" as const,
        data: e.data,
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "ui-monospace, monospace",
            "font-size": "9px",
            "text-valign": "bottom",
            "text-margin-y": 4,
            color: "#6B7280",
            "background-color": (ele: any) => {
              const type = ele.data("type") || "";
              return ENTITY_STYLES[type]?.color || "#999999";
            },
            shape: (ele: any) => {
              const type = ele.data("type") || "";
              return (ENTITY_STYLES[type]?.shape || "ellipse") as any;
            },
            width: (ele: any) => {
              const type = ele.data("type") || "";
              return (ENTITY_STYLES[type]?.width || 22) as any;
            },
            height: (ele: any) => {
              const type = ele.data("type") || "";
              return (ENTITY_STYLES[type]?.height || 22) as any;
            },
            "border-width": 1.5,
            "border-color": (ele: any) => {
              const type = ele.data("type") || "";
              return ENTITY_STYLES[type]?.borderColor || "#FFFFFF";
            },
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 3,
            "border-color": "#1B5FC4",
            "font-weight": "bold",
            color: "#14181F",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#C3C9D2",
            "target-arrow-color": "#C3C9D2",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "line-style": (ele: any) => {
              const conf = ele.data("confidence");
              if (conf === "medium") return "dashed";
              if (conf === "low") return "dotted";
              return "solid";
            },
          },
        },
        {
          selector: "edge:selected",
          style: {
            width: 2.5,
            "line-color": "#1B5FC4",
            "target-arrow-color": "#1B5FC4",
          },
        },
      ],
      layout: {
        name: layoutName,
        animate: false,
        padding: 40,
      } as any,
      wheelSensitivity: 0.25,
      minZoom: 0.2,
      maxZoom: 3.0,
    });

    // Handle node click
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      const entityId = node.data("entityId");
      const findingId = node.data("findingId");
      if (entityId) {
        onSelectEntity(entityId, findingId);
      }
    });

    // Handle background click (clear selection)
    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        // Clicked background
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [filteredNodes, filteredEdges, layoutName, showTableAlternative, onSelectEntity]);

  // Sync selectedEntityId with Cytoscape node selection
  useEffect(() => {
    if (!cyRef.current || !selectedEntityId) return;
    const cy = cyRef.current;
    cy.nodes().unselect();
    const targetNode = cy.nodes().filter((n) => n.data("entityId") === selectedEntityId);
    if (targetNode.length > 0) {
      targetNode.select();
      cy.animate(
        {
          center: { eles: targetNode },
          zoom: Math.max(cy.zoom(), 1.0),
        },
        { duration: 180 }
      );
    }
  }, [selectedEntityId]);

  // Actions
  const handleFit = useCallback(() => {
    cyRef.current?.fit(undefined, 40);
  }, []);

  const handleZoomIn = useCallback(() => {
    if (!cyRef.current) return;
    cyRef.current.zoom({
      level: cyRef.current.zoom() * 1.3,
      renderedPosition: {
        x: cyRef.current.width() / 2,
        y: cyRef.current.height() / 2,
      },
    });
  }, []);

  const handleZoomOut = useCallback(() => {
    if (!cyRef.current) return;
    cyRef.current.zoom({
      level: cyRef.current.zoom() / 1.3,
      renderedPosition: {
        x: cyRef.current.width() / 2,
        y: cyRef.current.height() / 2,
      },
    });
  }, []);

  const handleExportPng = useCallback(() => {
    if (!cyRef.current) return;
    const png64 = cyRef.current.png({
      output: "blob",
      bg: "#F7F8FA",
      full: true,
      scale: 2,
    });
    const url = URL.createObjectURL(png64);
    const link = document.createElement("a");
    link.href = url;
    link.download = `redstring-graph-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div className={`relative flex-1 flex flex-col bg-canvas overflow-hidden ${className}`}>
      {/* Top Floating Controls Bar */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5 bg-surface/95 backdrop-blur-sm border border-border rounded-panel p-1.5 shadow-sm text-xs">
        {/* Node Search Bar */}
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-7 pr-2 py-1 text-xs rounded-control bg-canvas border border-border-default focus:border-accent text-text-primary placeholder:text-text-muted w-36 sm:w-44 font-mono transition-all"
          />
        </div>

        <div className="h-4 w-px bg-border-subtle" />

        {/* Layout Switcher */}
        <button
          type="button"
          onClick={() => setLayoutName(layoutName === "cose" ? "concentric" : "cose")}
          className="p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors flex items-center gap-1 font-mono text-[11px]"
          title={`Switch layout (Current: ${layoutName})`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="capitalize hidden sm:inline">{layoutName}</span>
        </button>

        <div className="h-4 w-px bg-border-subtle" />

        {/* Zoom Controls */}
        <button
          type="button"
          onClick={handleZoomIn}
          className="p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={handleZoomOut}
          className="p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={handleFit}
          className="p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors"
          title="Fit view to graph"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>

        <div className="h-4 w-px bg-border-subtle" />

        {/* Export PNG */}
        <button
          type="button"
          onClick={handleExportPng}
          className="p-1.5 rounded-control text-text-secondary hover:text-text-primary hover:bg-subtle transition-colors"
          title="Export graph as PNG"
        >
          <ImageIcon className="w-3.5 h-3.5" />
        </button>

        <div className="h-4 w-px bg-border-subtle" />

        {/* Accessible Table Alternative Toggle */}
        <button
          type="button"
          onClick={() => setShowTableAlternative(!showTableAlternative)}
          className={`p-1.5 rounded-control text-xs flex items-center gap-1 transition-colors ${
            showTableAlternative
              ? "bg-selected text-accent font-medium border border-accent/30"
              : "text-text-secondary hover:text-text-primary hover:bg-subtle"
          }`}
          title="Toggle Accessible Table View"
          aria-pressed={showTableAlternative}
        >
          <Table2 className="w-3.5 h-3.5" />
          <span className="hidden sm:inline text-[11px]">Table view</span>
        </button>
      </div>

      {/* Floating Filter Panel (Top-Left) */}
      {!showTableAlternative && (
        <GraphFilterPanel
          availableTypes={allAvailableTypes}
          selectedTypes={selectedTypes}
          onToggleType={toggleType}
          onSelectAllTypes={selectAllTypes}
          onClearTypes={clearTypes}
          selectedConfidence={selectedConfidence}
          onToggleConfidence={toggleConfidence}
        />
      )}

      {/* Graph Visual Canvas or Accessible Table Alternative */}
      {showTableAlternative ? (
        <div className="flex-1 overflow-y-auto p-4 bg-surface" role="region" aria-label="Graph Nodes Table Alternative">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
              Accessible Graph Elements ({filteredNodes.length} nodes, {filteredEdges.length} edges)
            </h2>
            <button
              onClick={() => setShowTableAlternative(false)}
              className="text-xs text-accent hover:underline font-mono"
            >
              ← Return to visual canvas
            </button>
          </div>

          <div className="border border-border rounded-panel overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider">
                  <th className="py-2.5 px-3 font-medium">Finding ID</th>
                  <th className="py-2.5 px-3 font-medium">Type</th>
                  <th className="py-2.5 px-3 font-medium">Value</th>
                  <th className="py-2.5 px-3 font-medium">Relationships</th>
                  <th className="py-2.5 px-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {filteredNodes.map((n) => {
                  const nodeEdges = filteredEdges.filter(
                    (e) => e.data.source === n.data.id || e.data.target === n.data.id
                  );
                  const isSelected = selectedEntityId === n.data.entityId;

                  return (
                    <tr
                      key={n.data.id}
                      onClick={() => onSelectEntity(n.data.entityId, n.data.findingId)}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onSelectEntity(n.data.entityId, n.data.findingId);
                        }
                      }}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-selected border-l-2 border-l-accent"
                          : "hover:bg-subtle/60"
                      }`}
                    >
                      <td className="py-2 px-3 font-mono text-accent font-medium">
                        {n.data.findingId}
                      </td>
                      <td className="py-2 px-3">
                        <span className="inline-block px-1.5 py-0.5 rounded text-[10px] uppercase font-mono bg-canvas border border-border-subtle text-text-secondary">
                          {n.data.type}
                        </span>
                      </td>
                      <td className="py-2 px-3 font-mono font-medium text-text-primary break-all">
                        {n.data.label}
                      </td>
                      <td className="py-2 px-3 text-text-secondary font-mono text-[11px]">
                        {nodeEdges.length} connected
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          type="button"
                          className="px-2 py-0.5 text-[11px] rounded-control border border-border-default hover:bg-subtle text-accent"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEntity(n.data.entityId, n.data.findingId);
                          }}
                        >
                          View evidence
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="flex-1 w-full h-full min-h-[460px] cursor-grab active:cursor-grabbing"
          aria-label="Interactive cytoscape graph visualization canvas"
        />
      )}

      {/* Bottom Legend */}
      {!showTableAlternative && <GraphLegend visibleTypes={visibleTypes} />}

      {/* Mini status (bottom-right) */}
      <div className="absolute bottom-3 right-3 z-20 bg-surface/90 backdrop-blur-xs border border-border rounded-control px-2 py-1 text-[10px] font-mono text-text-muted shadow-xs select-none">
        {filteredNodes.length} nodes · {filteredEdges.length} edges
      </div>
    </div>
  );
}
