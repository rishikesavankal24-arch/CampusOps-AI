"use client";

import React, { useState } from "react";
import { ServiceDependencyGraphResponse } from "@/types/incident";
import {
  Server,
  Database,
  Layers,
  Cpu,
  CheckCircle2,
  Flame,
  Activity,
  ArrowRight,
} from "lucide-react";

interface ServiceGraphProps {
  graph: ServiceDependencyGraphResponse;
  selectedService: string | null;
  onSelectService: (serviceName: string | null) => void;
}

// Fixed topology layout coordinates for deterministic presentation
const NODE_COORDINATES: Record<string, { x: number; y: number }> = {
  "student-portal-ui": { x: 120, y: 160 },
  "portal-gateway": { x: 320, y: 160 },
  "auth-service": { x: 540, y: 160 },
  "redis-session-cache": { x: 780, y: 70 },
  "campusops-db": { x: 780, y: 160 },
  "campus-ldap-idp": { x: 780, y: 250 },
};

export default function ServiceGraph({
  graph,
  selectedService,
  onSelectService,
}: ServiceGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const getStatusColor = (status: string, impact: string) => {
    if (impact === "root_suspect" || status === "critical") {
      return {
        stroke: "#f43f5e",
        fill: "rgba(244, 63, 94, 0.15)",
        halo: "rgba(244, 63, 94, 0.35)",
        text: "text-rose-400",
        badge: "bg-rose-950/80 text-rose-300 border-rose-700/60",
      };
    }
    if (status === "degraded" || impact === "high") {
      return {
        stroke: "#f59e0b",
        fill: "rgba(245, 158, 11, 0.12)",
        halo: "rgba(245, 158, 11, 0.25)",
        text: "text-amber-400",
        badge: "bg-amber-950/80 text-amber-300 border-amber-700/60",
      };
    }
    return {
      stroke: "#10b981",
      fill: "rgba(16, 185, 129, 0.1)",
      halo: "rgba(16, 185, 129, 0.2)",
      text: "text-emerald-400",
      badge: "bg-emerald-950/80 text-emerald-300 border-emerald-700/60",
    };
  };

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "frontend":
        return Layers;
      case "gateway":
        return Activity;
      case "database":
        return Database;
      case "cache":
        return Cpu;
      case "idp":
        return CheckCircle2;
      default:
        return Server;
    }
  };

  const activeNode = graph.nodes.find(
    (n) => n.id === (hoveredNode || selectedService)
  );

  return (
    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 flex flex-col gap-4 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1e2e54] pb-3">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-sky-400" />
          <h2 className="text-sm font-semibold text-slate-100 tracking-wide uppercase">
            Service Dependency Topology & Health
          </h2>
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-[#0b132b] text-sky-300 border border-[#1e2e54]">
            {graph.nodes.length} Nodes &bull; {graph.edges.length} Edges
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-slate-300">Root Suspect</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-slate-300">Degraded Cascade</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-300">Operational</span>
          </div>
          {selectedService && (
            <button
              onClick={() => onSelectService(null)}
              className="text-xs text-sky-400 hover:text-sky-200 underline font-mono ml-2 cursor-pointer"
            >
              Clear Filter
            </button>
          )}
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-x-auto bg-[#0b132b] rounded-lg border border-[#1e2e54] p-2">
        <svg
          viewBox="0 0 920 310"
          className="w-full h-auto min-w-[760px] select-none"
          style={{ maxHeight: "340px" }}
        >
          <defs>
            <marker
              id="arrow-degraded"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#f59e0b" />
            </marker>
            <marker
              id="arrow-healthy"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 9 5 L 0 9 z" fill="#10b981" />
            </marker>
          </defs>

          {/* Render Dependency Edges */}
          {graph.edges.map((edge) => {
            const src = NODE_COORDINATES[edge.source] || { x: 50, y: 50 };
            const tgt = NODE_COORDINATES[edge.target] || { x: 100, y: 100 };
            const isDegraded = edge.is_degraded;
            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2 - 10;

            return (
              <g key={`${edge.source}->${edge.target}`}>
                <path
                  d={`M ${src.x + 40} ${src.y} C ${midX} ${src.y}, ${midX} ${tgt.y}, ${tgt.x - 40} ${tgt.y}`}
                  fill="none"
                  stroke={isDegraded ? "#f59e0b" : "#10b981"}
                  strokeWidth={isDegraded ? "2" : "1.5"}
                  strokeDasharray={isDegraded ? "4 3" : "none"}
                  markerEnd={isDegraded ? "url(#arrow-degraded)" : "url(#arrow-healthy)"}
                  opacity={isDegraded ? "0.9" : "0.5"}
                  className={isDegraded ? "animate-pulse" : ""}
                />
                <text
                  x={midX}
                  y={midY}
                  fill={isDegraded ? "#fbbf24" : "#6ee7b7"}
                  fontSize="9"
                  fontFamily="monospace"
                  textAnchor="middle"
                  className="bg-black/50"
                >
                  {edge.protocol}
                </text>
              </g>
            );
          })}

          {/* Render Service Nodes */}
          {graph.nodes.map((node) => {
            const coord = NODE_COORDINATES[node.id] || { x: 100, y: 100 };
            const isSelected = selectedService === node.id;
            const isHovered = hoveredNode === node.id;
            const colors = getStatusColor(node.status, node.impact);
            const isRoot = graph.root_suspects.includes(node.id);

            return (
              <g
                key={node.id}
                transform={`translate(${coord.x}, ${coord.y})`}
                className="cursor-pointer transition-transform duration-150"
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() =>
                  onSelectService(isSelected ? null : node.id)
                }
              >
                {/* Outer halo glow for root suspects or selected node */}
                {(isRoot || isSelected || isHovered) && (
                  <circle
                    r="46"
                    fill="none"
                    stroke={colors.stroke}
                    strokeWidth="2"
                    strokeDasharray={isRoot ? "5 3" : "none"}
                    opacity="0.6"
                    className={isRoot ? "animate-spin" : ""}
                    style={{ transformOrigin: "0 0" }}
                  />
                )}

                {/* Node Center Card */}
                <rect
                  x="-48"
                  y="-26"
                  width="96"
                  height="52"
                  rx="8"
                  fill={colors.fill}
                  stroke={isSelected ? "#38bdf8" : colors.stroke}
                  strokeWidth={isSelected ? "2.5" : "1.5"}
                  className="transition-colors"
                />

                {/* Root Suspect Flame Badge */}
                {isRoot && (
                  <g transform="translate(32, -26)">
                    <circle r="9" fill="#e11d48" />
                    <text
                      textAnchor="middle"
                      dy="3"
                      fontSize="9"
                      fill="#fff"
                      fontWeight="bold"
                    >
                      !
                    </text>
                  </g>
                )}

                {/* Node Service Title */}
                <text
                  textAnchor="middle"
                  y="-4"
                  fill="#f1f5f9"
                  fontSize="11"
                  fontWeight="600"
                  fontFamily="sans-serif"
                >
                  {node.name.length > 13 ? `${node.name.slice(0, 11)}..` : node.name}
                </text>

                {/* Node Type & Status Pill */}
                <text
                  textAnchor="middle"
                  y="12"
                  fill={colors.stroke}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="500"
                >
                  {node.status.toUpperCase()}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Node Telemetry Inspector Card */}
      {activeNode && (
        <div className="bg-[#0b132b] border border-[#1e2e54] rounded-lg p-3 text-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg border ${
                activeNode.impact === "root_suspect"
                  ? "bg-rose-950/70 border-rose-700 text-rose-300"
                  : "bg-sky-950/70 border-sky-700 text-sky-300"
              }`}
            >
              {React.createElement(getNodeIcon(activeNode.service_type), {
                className: "w-4 h-4",
              })}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-100 text-sm">
                  {activeNode.name}
                </span>
                <span className="font-mono text-[10px] text-sky-400">
                  ({activeNode.id})
                </span>
                {graph.root_suspects.includes(activeNode.id) && (
                  <span className="bg-rose-950/90 text-rose-300 border border-rose-700/80 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                    <Flame className="w-2.5 h-2.5" /> ROOT SUSPECT
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 text-slate-400 mt-0.5">
                <span>Type: <strong className="text-slate-200">{activeNode.service_type}</strong></span>
                <span>Impact: <strong className="text-slate-200">{activeNode.impact}</strong></span>
                <span>Linked Evidence: <strong className="text-sky-300">{activeNode.supporting_evidence_ids.length} events</strong></span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 font-mono">
            {Object.entries(activeNode.metrics_summary).map(([key, val]) => (
              <div
                key={key}
                className="bg-[#182344] border border-[#1e2e54] px-2 py-1 rounded text-[11px] text-slate-300"
              >
                <span className="text-sky-400 mr-1">{key}:</span>
                <span className="font-semibold">{String(val)}</span>
              </div>
            ))}
            <button
              onClick={() => onSelectService(activeNode.id)}
              className="ml-2 px-2.5 py-1 rounded bg-sky-600 hover:bg-sky-500 text-slate-950 text-[11px] font-sans font-semibold transition-colors flex items-center gap-1 cursor-pointer"
            >
              Filter Timeline <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
