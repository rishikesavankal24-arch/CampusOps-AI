"use client";

import React from "react";
import {
  Server,
  Wifi,
  ShieldAlert,
  Database,
  Cpu,
  Sparkles,
} from "lucide-react";

export function CampusNetworkTopology() {
  return (
    <div className="relative w-full rounded-2xl bg-[#05181b]/95 border border-teal-800/40 p-4 xl:p-5 shadow-2xl backdrop-blur-md overflow-hidden">
      {/* Subtle ambient glow */}
      <div className="absolute -top-10 -right-10 w-36 h-36 bg-[#00e5bf]/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Topology Status Bar */}
      <div className="flex items-center justify-between border-b border-teal-900/50 pb-2.5 mb-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00e5bf] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00e5bf]"></span>
          </span>
          <span className="text-xs font-semibold text-[#f5faf9] tracking-wide">
            Campus Network Topology
          </span>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-teal-950/80 border border-teal-700/60 text-[10px] font-mono text-[#00e5bf]">
          <Sparkles className="w-2.5 h-2.5" />
          <span>AI Engine Synchronized</span>
        </div>
      </div>

      {/* SVG Network Canvas */}
      <div className="relative w-full h-36 sm:h-40">
        <svg
          className="w-full h-full"
          viewBox="0 0 420 150"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Animated Connecting Lines */}
          {/* Center to Top-Left (Gateway) */}
          <line
            x1="210"
            y1="75"
            x2="60"
            y2="35"
            stroke="#00e5bf"
            strokeWidth="1.5"
            strokeOpacity="0.45"
            className="animate-signal-flow"
          />
          {/* Center to Top-Right (Core Spine) */}
          <line
            x1="210"
            y1="75"
            x2="360"
            y2="35"
            stroke="#00e5bf"
            strokeWidth="1.5"
            strokeOpacity="0.45"
            className="animate-signal-flow"
          />
          {/* Center to Bottom-Left (Access Point) */}
          <line
            x1="210"
            y1="75"
            x2="60"
            y2="115"
            stroke="#00e5bf"
            strokeWidth="1.5"
            strokeOpacity="0.45"
            className="animate-signal-flow"
          />
          {/* Center to Bottom-Right (pgvector DB) */}
          <line
            x1="210"
            y1="75"
            x2="360"
            y2="115"
            stroke="#00e5bf"
            strokeWidth="1.5"
            strokeOpacity="0.45"
            className="animate-signal-flow"
          />

          {/* Interconnect Cross Lines */}
          <line
            x1="60"
            y1="35"
            x2="60"
            y2="115"
            stroke="#84999a"
            strokeWidth="1"
            strokeOpacity="0.2"
            strokeDasharray="4 4"
          />
          <line
            x1="360"
            y1="35"
            x2="360"
            y2="115"
            stroke="#84999a"
            strokeWidth="1"
            strokeOpacity="0.2"
            strokeDasharray="4 4"
          />

          {/* Central AI Engine Halo */}
          <circle
            cx="210"
            cy="75"
            r="32"
            fill="#00e5bf"
            fillOpacity="0.08"
            className="animate-network-pulse"
          />
          <circle
            cx="210"
            cy="75"
            r="22"
            fill="#05181b"
            stroke="#00e5bf"
            strokeWidth="2"
          />
          <circle cx="210" cy="75" r="14" fill="#030e10" />

          {/* Peripheral Nodes */}
          <circle cx="60" cy="35" r="16" fill="#05181b" stroke="#00e5bf" strokeWidth="1.5" strokeOpacity="0.6" />
          <circle cx="360" cy="35" r="16" fill="#05181b" stroke="#00e5bf" strokeWidth="1.5" strokeOpacity="0.6" />
          <circle cx="60" cy="115" r="16" fill="#05181b" stroke="#00e5bf" strokeWidth="1.5" strokeOpacity="0.6" />
          <circle cx="360" cy="115" r="16" fill="#05181b" stroke="#00e5bf" strokeWidth="1.5" strokeOpacity="0.6" />
        </svg>

        {/* DOM Icons & Labels */}
        {/* Center Node: AI Operations Core */}
        <div className="absolute top-[75px] left-[210px] -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <Cpu className="w-4 h-4 text-[#00e5bf] animate-pulse" />
          <span className="text-[9px] font-bold text-white mt-0.5 whitespace-nowrap bg-[#030e10]/90 px-1 rounded border border-teal-800/40">
            AI Core
          </span>
        </div>

        {/* Top-Left: Perimeter Gateway */}
        <div className="absolute top-[35px] left-[60px] -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-[8px] font-mono text-[#84999a] mt-0.5 whitespace-nowrap">
            Gateway
          </span>
        </div>

        {/* Top-Right: Core Spine */}
        <div className="absolute top-[35px] left-[360px] -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <Server className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[8px] font-mono text-[#84999a] mt-0.5 whitespace-nowrap">
            Core Spine
          </span>
        </div>

        {/* Bottom-Left: Wi-Fi 6 AP */}
        <div className="absolute top-[115px] left-[60px] -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <Wifi className="w-3.5 h-3.5 text-teal-300" />
          <span className="text-[8px] font-mono text-[#84999a] mt-0.5 whitespace-nowrap">
            Wi-Fi 6 AP
          </span>
        </div>

        {/* Bottom-Right: Vector Store */}
        <div className="absolute top-[115px] left-[360px] -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
          <Database className="w-3.5 h-3.5 text-purple-300" />
          <span className="text-[8px] font-mono text-[#84999a] mt-0.5 whitespace-nowrap">
            pgvector
          </span>
        </div>
      </div>

      {/* Illustrative Architecture Metrics Bar */}
      <div className="grid grid-cols-3 gap-2 pt-2.5 border-t border-teal-900/50 text-center">
        <div className="p-1.5 rounded-lg bg-slate-900/60 border border-teal-900/30">
          <span className="text-[9px] text-[#84999a] block font-medium">Inference</span>
          <span className="text-[11px] font-mono font-bold text-white">&lt; 140ms</span>
        </div>
        <div className="p-1.5 rounded-lg bg-slate-900/60 border border-teal-900/30">
          <span className="text-[9px] text-[#84999a] block font-medium">Topology Mesh</span>
          <span className="text-[11px] font-mono font-bold text-[#00e5bf]">Active Sync</span>
        </div>
        <div className="p-1.5 rounded-lg bg-slate-900/60 border border-teal-900/30">
          <span className="text-[9px] text-[#84999a] block font-medium">Policy</span>
          <span className="text-[11px] font-mono font-bold text-emerald-400">Zero-Trust</span>
        </div>
      </div>

      {/* Mandatory Notice */}
      <p className="text-[9px] text-center text-[#84999a]/80 pt-1.5 font-sans italic">
        Illustrative architectural preview of CampusOps AI digital twin.
      </p>
    </div>
  );
}
