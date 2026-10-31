"use client";

import React, { useState } from "react";
import { NormalizedEvidenceItem } from "@/types/incident";
import {
  X,
  Copy,
  Check,
  Tag,
} from "lucide-react";

interface EvidenceDetailModalProps {
  evidence: NormalizedEvidenceItem | null;
  onClose: () => void;
}

export default function EvidenceDetailModal({
  evidence,
  onClose,
}: EvidenceDetailModalProps) {
  const [copied, setCopied] = useState(false);

  if (!evidence) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(evidence, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case "critical":
        return "bg-rose-950/80 border-rose-700/60 text-rose-300";
      case "error":
        return "bg-red-950/80 border-red-700/60 text-red-300";
      case "warning":
        return "bg-amber-950/80 border-amber-700/60 text-amber-300";
      default:
        return "bg-sky-950/80 border-sky-700/60 text-sky-300";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-[#1e2e54] bg-[#0b132b]">
          <div className="flex flex-col gap-1 pr-4">
            <div className="flex items-center gap-2">
              <span
                className={`text-[11px] font-mono uppercase px-2 py-0.5 rounded border ${getSeverityStyle(
                  evidence.severity
                )}`}
              >
                {evidence.severity}
              </span>
              <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-[#182344] text-sky-300 border border-[#1e2e54]">
                {evidence.source_type.replace("_", " ")}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-800/50">
                SIMULATED TELEMETRY
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-100 mt-1 leading-snug">
              {evidence.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-[#1e2e54] rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs font-sans text-slate-300">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-[#0b132b] p-3 rounded-lg border border-[#1e2e54]">
            <div>
              <span className="text-[11px] text-sky-400 block font-mono">Service Name</span>
              <span className="font-semibold text-slate-100 font-mono">
                {evidence.service_name}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-sky-400 block font-mono">Related Service</span>
              <span className="font-semibold text-slate-100 font-mono">
                {evidence.related_service || "N/A"}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-sky-400 block font-mono">Event Time (UTC)</span>
              <span className="font-semibold text-slate-100 font-mono">
                {new Date(evidence.event_time).toLocaleTimeString()}
              </span>
            </div>
            <div>
              <span className="text-[11px] text-sky-400 block font-mono">Ingest Time (UTC)</span>
              <span className="font-semibold text-slate-100 font-mono">
                {new Date(evidence.ingest_time).toLocaleTimeString()}
              </span>
            </div>
          </div>

          {/* Correlation ID */}
          {evidence.correlation_id && (
            <div className="flex items-center gap-2 bg-[#182344] border border-[#1e2e54] px-3 py-2 rounded-lg font-mono">
              <Tag className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-sky-400 text-[11px]">Correlation ID:</span>
              <span className="text-slate-100 text-[11px] font-semibold">
                {evidence.correlation_id}
              </span>
            </div>
          )}

          {/* Content Payload */}
          <div>
            <label className="text-xs font-semibold text-sky-300 uppercase tracking-wider block mb-1">
              Raw Statement / Log Payload
            </label>
            <pre className="bg-[#0b132b] p-3 rounded-lg border border-[#1e2e54] text-slate-200 font-mono text-[11px] whitespace-pre-wrap break-all leading-relaxed">
              {evidence.content}
            </pre>
          </div>

          {/* Structured Details JSON */}
          {evidence.details && Object.keys(evidence.details).length > 0 && (
            <div>
              <label className="text-xs font-semibold text-sky-300 uppercase tracking-wider block mb-1">
                Structured Telemetry Attributes
              </label>
              <pre className="bg-[#0b132b] p-3 rounded-lg border border-[#1e2e54] text-sky-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
                {JSON.stringify(evidence.details, null, 2)}
              </pre>
            </div>
          )}

          {/* Provenance Metadata */}
          {evidence.source_metadata && Object.keys(evidence.source_metadata).length > 0 && (
            <div>
              <label className="text-xs font-semibold text-sky-300 uppercase tracking-wider block mb-1">
                Collector Provenance Metadata
              </label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(evidence.source_metadata).map(([k, v]) => (
                  <span
                    key={k}
                    className="bg-[#0b132b] border border-[#1e2e54] px-2 py-1 rounded font-mono text-[11px] text-slate-300"
                  >
                    <strong className="text-sky-400">{k}:</strong> {String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#1e2e54] bg-[#0b132b] flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-400">
            UUID: {evidence.evidence_id}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-lg border border-[#1e2e54] hover:bg-[#182344] text-sky-300 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied JSON
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" /> Copy Normalized Item
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-slate-950 font-bold text-xs transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
