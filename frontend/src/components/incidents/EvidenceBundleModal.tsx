"use client";

import React, { useState } from "react";
import { EvidenceBundleResponse } from "@/types/incident";
import {
  X,
  PackageCheck,
  Check,
  Copy,
  ShieldCheck,
} from "lucide-react";

interface EvidenceBundleModalProps {
  bundle: EvidenceBundleResponse | null;
  onClose: () => void;
}

export default function EvidenceBundleModal({
  bundle,
  onClose,
}: EvidenceBundleModalProps) {
  const [copied, setCopied] = useState(false);

  if (!bundle) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(bundle, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-[#1e2e54] bg-[#0b132b]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#182344] border border-[#1e2e54] text-sky-300">
              <PackageCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#182344] text-sky-300 border border-[#1e2e54]">
                  MANIFEST v{bundle.bundle_version}
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-800/60">
                  SIMULATED BUNDLE
                </span>
              </div>
              <h3 className="text-sm font-semibold text-slate-100 mt-1">
                Verifiable Incident Evidence Bundle (Cryptographic Export)
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-[#1e2e54] rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs font-sans text-slate-300">
          <div className="flex items-center gap-2 p-3 bg-emerald-950/20 border border-emerald-800/40 rounded-lg text-emerald-300 text-xs">
            <ShieldCheck className="w-4 h-4 flex-shrink-0" />
            <span>
              All <strong>{bundle.total_evidence_count}</strong> telemetry records
              bound with SHA-256 integrity hash for immutable audit compliance.
            </span>
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
              <span>Bundle ID:</span>
              <span className="text-sky-300 select-all font-mono">
                {bundle.bundle_id}
              </span>
            </div>
            <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
              <span>Generated At (UTC):</span>
              <span className="text-slate-200">
                {new Date(bundle.created_at).toISOString()}
              </span>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-sky-300 uppercase tracking-wider block mb-1">
              Bundle Manifest JSON
            </label>
            <pre className="bg-[#0b132b] p-3 rounded-lg border border-[#1e2e54] text-sky-300 font-mono text-[11px] overflow-x-auto max-h-96 leading-relaxed">
              {JSON.stringify(bundle, null, 2)}
            </pre>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#1e2e54] bg-[#0b132b] flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-400">
            Total Items: {bundle.total_evidence_count}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-lg border border-[#1e2e54] hover:bg-[#182344] text-sky-300 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Copied Full Bundle
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" /> Copy Raw Manifest JSON
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
