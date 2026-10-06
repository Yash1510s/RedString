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
  Eye,
} from "lucide-react";
import { InvestigationGraphData } from "@/lib/api";
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
  const mountRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const [layoutName, setLayoutName] = useState<"cose" | "concentric">("cose");
  const [searchTerm, setSearchTerm] = useState("");
  const [showTableAlternative, setShowTableAlternative] = useState(false);

  // Available types
  const allAvailableTypes = useMemo(() => {
    const types = new Set<string>();
    graphData.nodes.forEach((n) => types.add(n.data.type));
    return Array.from(types).sort();
  }, [graphData.nodes]);

  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedConfidence, setSelectedConfidence] = useState<Set<string>>(
    new Set(["high", "medium", "low"])
  );

  // Sync types on data change
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

  // Filtered nodes & edges
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

  const visibleTypes = useMemo(() => {
    const types = new Set<string>();
    filteredNodes.forEach((n) => types.add(n.data.type));
    return Array.from(types);
  }, [filteredNodes]);

  // 1. Initialize Cytoscape ONCE on an isolated programmatic mount node
  useEffect(() => {
    const host = containerRef.current;
    if (!host) return;

    // Create an isolated sub-div that React does not track in fiber tree
    const cyMount = document.createElement("div");
    cyMount.style.width = "100%";
    cyMount.style.height = "100%";
    cyMount.style.position = "absolute";
    cyMount.style.top = "0";
    cyMount.style.left = "0";
    host.appendChild(cyMount);
    mountRef.current = cyMount;

    const cy = cytoscape({
      container: cyMount,
      elements: [],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "ui-monospace, monospace",
            "font-size": "9px",
            "text-valign": "bottom",
            "text-margin-y": 4,
            color: "#A7B0BD",
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
            color: "#FFFFFF",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#3A4552",
            "target-arrow-color": "#3A4552",
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
      layout: { name: "cose", animate: false } as any,
      wheelSensitivity: 0.25,
      minZoom: 0.1,
      maxZoom: 3.5,
    });

    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      const entityId = node.data("entityId");
      const findingId = node.data("findingId");
      if (entityId) {
        onSelectEntity(entityId, findingId);
      }
    });

    cyRef.current = cy;

    // Observe size changes
    const ro = new ResizeObserver(() => {
      if (cyRef.current) {
        cyRef.current.resize();
      }
    });
    ro.observe(host);

    return () => {
      ro.disconnect();
      try {
        cy.destroy();
      } catch {
        // ignore cleanup error
      }
      cyRef.current = null;
      if (cyMount.parentNode) {
        cyMount.parentNode.removeChild(cyMount);
      }
      mountRef.current = null;
    };
  }, [onSelectEntity]);

  // 2. Update Cytoscape elements and layout smoothly without tearing down the instance
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      cy.elements().remove();
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
      cy.add(elements);
    });

    if (filteredNodes.length > 0) {
      const layout = cy.layout({
        name: layoutName,
        animate: false,
        padding: 40,
      } as any);
      layout.run();
      cy.resize();
      cy.fit(undefined, 40);
    }
  }, [filteredNodes, filteredEdges, layoutName]);

  // 3. Highlight selected node
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

  // 4. Resize and fit when returning from table alternative
  useEffect(() => {
    if (!showTableAlternative && cyRef.current) {
      requestAnimationFrame(() => {
        cyRef.current?.resize();
        cyRef.current?.fit(undefined, 40);
      });
    }
  }, [showTableAlternative]);

  // Action helpers
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
      bg: "#0E1116",
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
      <div className="absolute top-3 right-3 z-30 flex items-center gap-1.5 bg-surface/95 backdrop-blur-sm border border-border rounded-panel p-1.5 shadow-sm text-xs">
        {/* Node Search Bar */}
        <div className="relative flex items-center">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-7 pr-2 py-1 text-xs rounded-control bg-canvas border border-border-default focus:border-accent text-text-primary placeholder:text-text-muted w-32 sm:w-44 font-mono transition-all"
          />
        </div>

        <div className="h-4 w-px bg-border-subtle" />

        {/* Layout Switcher */}
        {!showTableAlternative && (
          <>
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
          </>
        )}

        {/* Accessible Table Alternative Toggle */}
        <button
          type="button"
          onClick={() => setShowTableAlternative(!showTableAlternative)}
          className={`p-1.5 rounded-control text-xs flex items-center gap-1.5 transition-colors ${
            showTableAlternative
              ? "bg-accent text-accent-fg font-medium"
              : "text-text-secondary hover:text-text-primary hover:bg-subtle"
          }`}
          title={showTableAlternative ? "Switch to Interactive Graph Canvas" : "Switch to Accessible Table View"}
          aria-pressed={showTableAlternative}
        >
          {showTableAlternative ? (
            <>
              <Eye className="w-3.5 h-3.5" />
              <span className="text-[11px] font-mono">Graph canvas</span>
            </>
          ) : (
            <>
              <Table2 className="w-3.5 h-3.5" />
              <span className="text-[11px] font-mono">Table view</span>
            </>
          )}
        </button>
      </div>

      {/* Floating Filter Panel (Top-Left, visible when on canvas) */}
      <div className={showTableAlternative ? "hidden" : "block"}>
        <GraphFilterPanel
          availableTypes={allAvailableTypes}
          selectedTypes={selectedTypes}
          onToggleType={toggleType}
          onSelectAllTypes={selectAllTypes}
          onClearTypes={clearTypes}
          selectedConfidence={selectedConfidence}
          onToggleConfidence={toggleConfidence}
        />
      </div>

      {/* 1. Cytoscape Container: ALWAYS mounted, hidden via CSS if Table view active */}
      <div
        className={`flex-1 w-full h-full relative ${
          showTableAlternative ? "hidden" : "flex flex-col"
        }`}
      >
        <div
          ref={containerRef}
          className="flex-1 w-full h-full min-h-[460px] cursor-grab active:cursor-grabbing relative"
          aria-label="Interactive cytoscape graph visualization canvas"
        />

        {/* Legend */}
        <GraphLegend visibleTypes={visibleTypes} />

        {/* Mini status indicator (bottom-right) */}
        <div className="absolute bottom-3 right-3 z-20 bg-surface/90 backdrop-blur-xs border border-border rounded-control px-2.5 py-1 text-[10px] font-mono text-text-muted shadow-xs select-none">
          {filteredNodes.length} nodes · {filteredEdges.length} edges
        </div>
      </div>

      {/* 2. Accessible Table Alternative: ALWAYS mounted, hidden via CSS if Canvas active */}
      <div
        className={`flex-1 overflow-y-auto p-4 bg-surface ${
          showTableAlternative ? "block" : "hidden"
        }`}
        role="region"
        aria-label="Accessible Graph Elements Table Alternative"
      >
        <div className="mb-3 flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="text-xs font-semibold text-text-primary uppercase tracking-wider font-mono">
              Accessible Graph Elements ({filteredNodes.length} nodes, {filteredEdges.length} edges)
            </h2>
            <p className="text-[11px] text-text-muted mt-0.5">
              Screen-reader and keyboard accessible representation of graph relationships.
            </p>
          </div>
          <button
            onClick={() => setShowTableAlternative(false)}
            className="text-xs text-accent hover:underline font-mono"
          >
            ← Return to visual canvas
          </button>
        </div>

        {filteredNodes.length === 0 ? (
          <div className="p-8 text-center text-xs text-text-muted border border-dashed border-border rounded-panel">
            No nodes match the current filter criteria.
          </div>
        ) : (
          <div className="border border-border rounded-panel overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-canvas border-b border-border text-text-muted text-[11px] uppercase tracking-wider font-mono">
                  <th className="py-2.5 px-3">Finding ID</th>
                  <th className="py-2.5 px-3">Entity Type</th>
                  <th className="py-2.5 px-3">Observed Value</th>
                  <th className="py-2.5 px-3">Connected Relations</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
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
                        {nodeEdges.length} connected edges
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          type="button"
                          className="px-2 py-0.5 text-[11px] rounded-control border border-border-default hover:bg-subtle text-accent font-mono"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectEntity(n.data.entityId, n.data.findingId);
                          }}
                        >
                          Inspect evidence
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
