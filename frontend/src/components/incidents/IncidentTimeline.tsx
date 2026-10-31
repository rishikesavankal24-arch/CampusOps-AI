"use client";

import React from "react";
import { NormalizedEvidenceItem, SourceType, EventSeverity } from "@/types/incident";
import {
  FileText,
  Activity,
  GitCommit,
  AlertTriangle,
  Radio,
  FileCode,
  LifeBuoy,
  History,
  Layers,
  Clock,
  Eye,
  Filter,
} from "lucide-react";

interface IncidentTimelineProps {
  events: NormalizedEvidenceItem[];
  selectedSourceType: string | null;
  selectedSeverity: string | null;
  onSelectSourceType: (type: string | null) => void;
  onSelectSeverity: (sev: string | null) => void;
  onInspectEvidence: (ev: NormalizedEvidenceItem) => void;
}

export default function IncidentTimeline({
  events,
  selectedSourceType,
  selectedSeverity,
  onSelectSourceType,
  onSelectSeverity,
  onInspectEvidence,
}: IncidentTimelineProps) {
  const sourceTypes: { label: string; value: SourceType | "all" }[] = [
    { label: "All Sources", value: "all" },
    { label: "Logs", value: "application_log" },
    { label: "Infra Logs", value: "infrastructure_log" },
    { label: "Metrics", value: "metric" },
    { label: "Traces", value: "trace" },
    { label: "Alerts", value: "alert" },
    { label: "Deployments", value: "deployment" },
    { label: "Config", value: "configuration" },
    { label: "Tickets", value: "support_ticket" },
    { label: "Past Incidents", value: "previous_incident" },
  ];

  const severities: { label: string; value: EventSeverity | "all" }[] = [
    { label: "All Severities", value: "all" },
    { label: "Critical", value: "critical" },
    { label: "Error", value: "error" },
    { label: "Warning", value: "warning" },
    { label: "Info", value: "info" },
  ];

  const getSourceIcon = (source: string) => {
    switch (source) {
      case "application_log":
      case "infrastructure_log":
        return FileText;
      case "metric":
        return Activity;
      case "trace":
        return Radio;
      case "alert":
        return AlertTriangle;
      case "deployment":
        return GitCommit;
      case "configuration":
        return FileCode;
      case "support_ticket":
        return LifeBuoy;
      case "previous_incident":
        return History;
      default:
        return Layers;
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "critical":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "error":
        return "bg-red-950/80 border-red-700/60 text-red-300";
      case "warning":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      default:
        return "bg-cyan-950/80 border-cyan-700/60 text-cyan-300";
    }
  };

  const firstEventTime = events.length > 0 ? new Date(events[0].event_time).getTime() : 0;

  return (
    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 flex flex-col gap-4 shadow-xl">
      {/* Header and Filter Controls */}
      <div className="flex flex-col gap-3 border-b border-[#1e2e54] pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-sky-400" />
            <h2 className="text-sm font-semibold text-slate-100 tracking-wide uppercase">
              Chronological Incident Evidence Timeline
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b132b] text-sky-300 border border-[#1e2e54]">
              {events.length} Events Sequenced
            </span>
          </div>

          <span className="text-[10px] font-mono text-slate-400">
            Sorted strictly by <strong className="text-sky-300">event_time ASC</strong>
          </span>
        </div>

        {/* Source Type Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-xs text-sky-400/80 flex items-center gap-1 mr-1 font-mono">
            <Filter className="w-3 h-3" /> Source:
          </span>
          {sourceTypes.map((st) => {
            const isSelected =
              st.value === "all"
                ? !selectedSourceType
                : selectedSourceType === st.value;
            return (
              <button
                key={st.value}
                onClick={() =>
                  onSelectSourceType(st.value === "all" ? null : st.value)
                }
                className={`text-xs px-2.5 py-1 rounded-md transition-all font-mono cursor-pointer ${
                  isSelected
                    ? "bg-sky-600 text-slate-950 font-bold shadow-md"
                    : "bg-[#0b132b] text-slate-300 border border-[#1e2e54] hover:bg-[#182344]"
                }`}
              >
                {st.label}
              </button>
            );
          })}
        </div>

        {/* Severity Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-sky-400/80 flex items-center gap-1 mr-1 font-mono">
            Severity:
          </span>
          {severities.map((sev) => {
            const isSelected =
              sev.value === "all"
                ? !selectedSeverity
                : selectedSeverity === sev.value;
            return (
              <button
                key={sev.value}
                onClick={() =>
                  onSelectSeverity(sev.value === "all" ? null : sev.value)
                }
                className={`text-[11px] px-2 py-0.5 rounded transition-all font-mono cursor-pointer ${
                  isSelected
                    ? "bg-slate-200 text-slate-950 font-bold"
                    : "bg-[#0b132b] text-slate-400 border border-[#1e2e54] hover:bg-[#182344]"
                }`}
              >
                {sev.label}
              </button>
            );
          })}

          {(selectedSourceType || selectedSeverity) && (
            <button
              onClick={() => {
                onSelectSourceType(null);
                onSelectSeverity(null);
              }}
              className="text-xs text-sky-400 hover:text-sky-200 underline font-mono ml-auto cursor-pointer"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Timeline Stream */}
      {events.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-xs">
          No evidence records matched your current filters.
        </div>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-[#1e2e54]">
          {events.map((ev) => {
            const SourceIcon = getSourceIcon(ev.source_type);
            const evTime = new Date(ev.event_time);
            const offsetMinutes = Math.round(
              (evTime.getTime() - firstEventTime) / 60000
            );

            return (
              <div
                key={ev.evidence_id}
                className="relative group cursor-pointer"
                onClick={() => onInspectEvidence(ev)}
              >
                {/* Timeline node dot */}
                <div
                  className={`absolute -left-[29px] top-3 w-4 h-4 rounded-full border-2 border-[#131d38] flex items-center justify-center transition-transform group-hover:scale-125 ${
                    ev.severity === "critical"
                      ? "bg-rose-500 ring-2 ring-rose-500/40"
                      : ev.severity === "error"
                      ? "bg-red-500"
                      : ev.severity === "warning"
                      ? "bg-amber-500"
                      : "bg-sky-500"
                  }`}
                />

                {/* Evidence Card */}
                <div className="bg-[#0b132b] border border-[#1e2e54] hover:border-sky-500/80 rounded-lg p-3.5 transition-all shadow-md group-hover:bg-[#182344]/60">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${getSeverityBadge(
                          ev.severity
                        )}`}
                      >
                        {ev.severity}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#131d38] text-sky-300 border border-[#1e2e54] flex items-center gap-1">
                        <SourceIcon className="w-3 h-3" />
                        {ev.source_type.replace("_", " ")}
                      </span>
                      <span className="text-[11px] font-mono font-semibold text-slate-200">
                        {ev.service_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                      <span className="text-sky-400 font-semibold">
                        +{offsetMinutes}m
                      </span>
                      <span>{evTime.toLocaleTimeString()} UTC</span>
                    </div>
                  </div>

                  <h3 className="text-xs font-semibold text-slate-100 group-hover:text-sky-200 transition-colors leading-snug">
                    {ev.title}
                  </h3>

                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {ev.content}
                  </p>

                  <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-[#1e2e54] text-[10px] font-mono text-slate-400">
                    <div className="flex items-center gap-2">
                      {ev.correlation_id && (
                        <span className="text-sky-400/90 truncate max-w-[200px]">
                          cid: {ev.correlation_id}
                        </span>
                      )}
                      {ev.related_service && (
                        <span className="text-slate-400">
                          &rarr; {ev.related_service}
                        </span>
                      )}
                    </div>
                    <span className="text-sky-400 flex items-center gap-1 opacity-80 group-hover:opacity-100 group-hover:underline">
                      <Eye className="w-3 h-3" /> Inspect Details
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
