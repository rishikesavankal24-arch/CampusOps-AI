"use client";

import React, { useState } from "react";
import {
  InvestigationStateResponse,
  Hypothesis,
  DiagnosticToolCall,
} from "@/types/investigation";
import {
  Bot,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  Activity,
  UserCheck,
  ListTree,
  ChevronDown,
  ChevronUp,
  Shield,
  Gauge,
  X,
} from "lucide-react";

interface InvestigationPanelProps {
  state: InvestigationStateResponse | null;
  onRunDiagnostic: (toolName?: string) => Promise<void>;
  onApprove: (decision: "approve" | "reject", notes?: string) => Promise<void>;
  onExecuteRecovery: (forceFailure: boolean) => Promise<void>;
  onReset: () => Promise<void>;
  onInspectEvidenceId?: (id: string) => void;
}

export default function InvestigationPanel({
  state,
  onRunDiagnostic,
  onApprove,
  onExecuteRecovery,
  onReset,
  onInspectEvidenceId,
}: InvestigationPanelProps) {
  const [runningAction, setRunningAction] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [forceFailToggle, setForceFailToggle] = useState(false);
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null);
  const [expandedHypothesisId, setExpandedHypothesisId] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  if (!state) return null;

  const handleDiagnosticClick = async (toolName?: string) => {
    try {
      setRunningAction(true);
      await onRunDiagnostic(toolName);
    } finally {
      setRunningAction(false);
    }
  };

  const handleApprovalClick = async (decision: "approve" | "reject") => {
    try {
      setRunningAction(true);
      await onApprove(decision, approvalNotes || undefined);
      setApprovalNotes("");
    } finally {
      setRunningAction(false);
    }
  };

  const handleExecuteConfirmed = async () => {
    try {
      setRunningAction(true);
      setShowConfirmModal(false);
      await onExecuteRecovery(forceFailToggle);
    } finally {
      setRunningAction(false);
    }
  };

  const handleResetClick = async () => {
    try {
      setRunningAction(true);
      await onReset();
    } finally {
      setRunningAction(false);
    }
  };

  const getStageBadge = (stage: string) => {
    switch (stage) {
      case "RESOLVED":
        return {
          label: "RESOLVED",
          classes: "bg-emerald-950/60 border-emerald-600/70 text-emerald-300",
          icon: CheckCircle2,
        };
      case "REPLANNING":
        return {
          label: "REPLANNING ACTIVE",
          classes: "bg-rose-950/60 border-rose-600/70 text-rose-300",
          icon: AlertTriangle,
        };
      case "AWAITING_APPROVAL":
        return {
          label: "AWAITING HUMAN APPROVAL",
          classes: "bg-amber-950/60 border-amber-600/70 text-amber-200",
          icon: UserCheck,
        };
      case "RECOVERY_EXECUTION":
        return {
          label: "APPROVED — READY TO EXECUTE",
          classes: "bg-sky-950/60 border-sky-600/70 text-sky-200",
          icon: Play,
        };
      default:
        return {
          label: stage.replace("_", " "),
          classes: "bg-blue-950/60 border-blue-600/70 text-blue-300",
          icon: Bot,
        };
    }
  };

  const stageInfo = getStageBadge(state.current_stage);
  const StageIcon = stageInfo.icon;

  return (
    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-6 shadow-sm">
      {/* Top Header & Stage Status */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#1e2e54] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-300">
            <Bot className="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Investigation Orchestrator
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b1329] text-sky-300 border border-[#1e2e54]">
                ROUND {state.current_round} / {state.max_rounds}
              </span>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#0b1329] text-slate-300 border border-[#1e2e54]">
                CLASS: {state.classification}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Network-First Diagnostic Engine &bull; Bayesian Hypothesis Evaluation
            </p>
          </div>
        </div>

        {/* Current State Indicator & Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono text-xs font-semibold ${stageInfo.classes}`}
          >
            <StageIcon className="w-3.5 h-3.5" />
            <span>{stageInfo.label}</span>
          </div>

          {state.current_stage !== "RESOLVED" &&
            state.current_stage !== "AWAITING_APPROVAL" &&
            state.current_stage !== "RECOVERY_EXECUTION" && (
              <button
                onClick={() => handleDiagnosticClick()}
                disabled={runningAction}
                className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-sm disabled:opacity-50 cursor-pointer"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                {runningAction
                  ? "Running Diagnostic..."
                  : state.current_round === 1
                  ? "Run Round 1 (Network-First)"
                  : `Run Round ${state.current_round} Diagnostic`}
              </button>
            )}

          <button
            onClick={handleResetClick}
            disabled={runningAction}
            className="p-1.5 rounded-lg border border-[#1e2e54] hover:bg-[#182344] text-slate-300 hover:text-white transition text-xs flex items-center gap-1 disabled:opacity-50 cursor-pointer"
            title="Reset investigation state back to round 1"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="text-[11px] font-mono">Reset</span>
          </button>
        </div>
      </div>

      {/* Competing Failure Hypotheses */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListTree className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Competing Failure Hypotheses ({state.hypotheses.length})
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Leading: <strong className="text-sky-300">{state.leading_hypothesis_id || "Evaluating"}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {state.hypotheses.map((h: Hypothesis) => {
            const isLeading = state.leading_hypothesis_id === h.id;
            const isRejected = h.status === "rejected";
            const isSupported = h.status === "supported";
            const isExpanded = expandedHypothesisId === h.id;

            return (
              <div
                key={h.id}
                className={`p-4 rounded-xl border flex flex-col justify-between gap-3 transition-all ${
                  isSupported
                    ? "bg-[#16274a] border-sky-500/80 shadow-sm"
                    : isRejected
                    ? "bg-[#0b1329]/60 border-slate-800 opacity-60"
                    : isLeading
                    ? "bg-[#182344] border-sky-600/70"
                    : "bg-[#0b1329] border-[#1e2e54]"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[#0b1329] text-sky-400 border border-[#1e2e54] font-bold">
                      {h.id}
                    </span>
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold border ${
                        isSupported
                          ? "bg-emerald-950/70 border-emerald-700/60 text-emerald-300"
                          : isRejected
                          ? "bg-rose-950/70 border-rose-800/60 text-rose-300 line-through"
                          : "bg-[#0b1329] border-slate-700 text-slate-300"
                      }`}
                    >
                      {h.status}
                    </span>
                  </div>

                  <h4 className="text-xs font-semibold text-slate-100 leading-snug">
                    {h.title}
                  </h4>

                  <p className="text-[11px] text-slate-400 leading-relaxed font-sans line-clamp-3">
                    {h.explanation}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-[#1e2e54] text-[11px]">
                  {/* Confidence Bar */}
                  <div>
                    <div className="flex justify-between items-center text-[10px] font-mono mb-1">
                      <span className="text-slate-400">Confidence</span>
                      <span
                        className={`font-bold ${
                          h.confidence_score >= 0.8
                            ? "text-emerald-400"
                            : h.confidence_score <= 0.2
                            ? "text-rose-400"
                            : "text-amber-400"
                        }`}
                      >
                        {Math.round(h.confidence_score * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0b1329] rounded-full overflow-hidden border border-[#1e2e54]">
                      <div
                        className={`h-full transition-all duration-300 ${
                          h.confidence_score >= 0.8
                            ? "bg-emerald-400"
                            : h.confidence_score <= 0.2
                            ? "bg-rose-500"
                            : "bg-amber-400"
                        }`}
                        style={{ width: `${Math.round(h.confidence_score * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Evidence Count and Expansion Toggle */}
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1">
                    <span>
                      Evidence: {h.supporting_evidence_ids.length} sup / {h.contradicting_evidence_ids.length} con
                    </span>
                    <button
                      onClick={() => setExpandedHypothesisId(isExpanded ? null : h.id)}
                      className="text-sky-400 hover:text-sky-200 underline cursor-pointer flex items-center gap-0.5"
                    >
                      {isExpanded ? "Hide" : "Details"}
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>
                  </div>

                  {/* Expanded Evidence References */}
                  {isExpanded && (
                    <div className="mt-2 pt-2 border-t border-[#1e2e54] space-y-1.5 text-[10px] font-mono animate-fadeIn">
                      <p className="text-slate-300">
                        <strong>Rationale:</strong> {h.confidence_rationale}
                      </p>
                      {h.supporting_evidence_ids.length > 0 && (
                        <div>
                          <span className="text-emerald-400 block font-semibold">Supporting Evidence:</span>
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {h.supporting_evidence_ids.map((id) => (
                              <button
                                key={String(id)}
                                onClick={() => onInspectEvidenceId && onInspectEvidenceId(String(id))}
                                className="px-1.5 py-0.2 rounded bg-[#0b1329] text-sky-300 border border-sky-800 hover:border-sky-500 cursor-pointer"
                              >
                                {String(id).slice(0, 8)}...
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      {h.contradicting_evidence_ids.length > 0 && (
                        <div>
                          <span className="text-rose-400 block font-semibold">Contradicting Evidence:</span>
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {h.contradicting_evidence_ids.map((id) => (
                              <button
                                key={String(id)}
                                onClick={() => onInspectEvidenceId && onInspectEvidenceId(String(id))}
                                className="px-1.5 py-0.2 rounded bg-[#0b1329] text-rose-300 border border-rose-800 hover:border-rose-500 cursor-pointer"
                              >
                                {String(id).slice(0, 8)}...
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Executed Diagnostic Tool History */}
      {state.tool_history.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Executed Diagnostics ({state.tool_history.length})
            </h3>
            <span className="text-[10px] font-mono text-amber-300 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/60">
              SIMULATED SRE
            </span>
          </div>

          <div className="space-y-2">
            {state.tool_history.map((tool: DiagnosticToolCall) => {
              const isExpanded = expandedToolId === tool.call_id;

              return (
                <div
                  key={tool.call_id}
                  className="bg-[#0b1329] border border-[#1e2e54] rounded-lg p-3 text-xs space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#131d38] text-sky-300 border border-[#1e2e54]">
                        R{tool.round} &bull; {tool.category.toUpperCase()}
                      </span>
                      <span className="font-mono font-bold text-slate-100">
                        {tool.tool_name}
                      </span>
                      <span className="text-slate-400 font-mono text-[11px]">
                        (&rarr; {tool.target_service})
                      </span>
                    </div>

                    <button
                      onClick={() => setExpandedToolId(isExpanded ? null : tool.call_id)}
                      className="text-[11px] font-mono text-sky-400 hover:text-sky-200 underline cursor-pointer"
                    >
                      {isExpanded ? "Hide Raw Output" : "View Raw Output"}
                    </button>
                  </div>

                  <p className="text-[11px] text-slate-300 leading-relaxed bg-[#131d38] p-2 rounded border border-[#1e2e54] font-sans">
                    <strong>Insight:</strong> {tool.interpreted_insight}
                  </p>

                  {isExpanded && (
                    <pre className="bg-[#070d1e] p-3 rounded text-[10px] font-mono text-emerald-300 overflow-x-auto border border-[#1e2e54] leading-relaxed">
                      {JSON.stringify(tool.simulated_output, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Human Approval Gate Card */}
      {state.recovery_plan && state.current_stage === "AWAITING_APPROVAL" && (
        <div className="bg-[#182344] border-2 border-amber-500/80 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between gap-2 border-b border-amber-900/40 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-950 border border-amber-600 text-amber-300">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-amber-100 uppercase tracking-wide">
                  Human Approval Gate
                </h3>
                <p className="text-xs text-amber-300/80 font-mono">
                  Policy Gate: Human authorization required before execution.
                </p>
              </div>
            </div>

            <span className="text-xs font-mono px-2.5 py-1 rounded bg-amber-900/80 text-amber-200 border border-amber-700 font-bold">
              RISK: {state.recovery_plan.risk_level.toUpperCase()}
            </span>
          </div>

          {/* Action Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <span className="text-slate-400 block font-mono text-[11px]">Proposed Recovery Action:</span>
              <p className="font-semibold text-slate-100 text-sm">
                {state.recovery_plan.action_name}
              </p>
              <p className="text-slate-300 text-[11px] font-mono">
                {state.recovery_plan.rationale}
              </p>
            </div>

            <div className="space-y-1.5">
              <span className="text-slate-400 block font-mono text-[11px]">Expected Telemetry Signal:</span>
              <p className="text-emerald-300 font-mono text-[11px] bg-[#0b1329] p-2 rounded border border-[#1e2e54]">
                {state.recovery_plan.expected_signal}
              </p>
              <div className="flex items-center gap-2 pt-1 text-[11px] font-mono text-slate-400">
                <span>Affected Services:</span>
                <span className="text-sky-300">
                  {state.recovery_plan.affected_services.join(", ")}
                </span>
              </div>
            </div>
          </div>

          {/* Approval Controls */}
          <div className="pt-2 border-t border-[#1e2e54] flex flex-col sm:flex-row items-center justify-between gap-3">
            <input
              type="text"
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
              placeholder="Operator notes (e.g. 'Approved for test execution')..."
              className="w-full sm:max-w-md px-3 py-1.5 rounded-lg bg-[#0b1329] border border-[#1e2e54] text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => handleApprovalClick("reject")}
                disabled={runningAction}
                className="px-3.5 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
              >
                Reject Recovery
              </button>
              <button
                onClick={() => handleApprovalClick("approve")}
                disabled={runningAction}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-sm disabled:opacity-50 cursor-pointer"
              >
                Approve Recovery Plan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Recovery Ready Execution Trigger */}
      {state.recovery_plan && state.current_stage === "RECOVERY_EXECUTION" && (
        <div className="bg-[#182344] border-2 border-sky-500/80 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1e2e54] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-sky-400" />
                <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wide">
                  Plan Approved — Ready for Simulated Execution
                </h3>
              </div>
              <p className="text-xs text-slate-300 mt-1 font-mono">
                Operator authorized: {state.recovery_plan.action_name}
              </p>
            </div>

            {/* Verification failure demo toggle */}
            <label className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={forceFailToggle}
                onChange={(e) => setForceFailToggle(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-blue-500 focus:ring-0"
              />
              <span className={forceFailToggle ? "text-amber-300 font-bold" : ""}>
                Demo Verification Failure & Replanning Loop
              </span>
            </label>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setShowConfirmModal(true)}
              disabled={runningAction}
              className="px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold shadow transition flex items-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              <Gauge className="w-4 h-4" />
              <span>Execute Simulated Recovery & Verify Telemetry</span>
            </button>
          </div>
        </div>
      )}

      {/* Post-Recovery Verification Results */}
      {state.verification_result && (
        <div
          className={`border rounded-xl p-5 space-y-4 shadow-sm ${
            state.verification_result.verified
              ? "bg-[#10243b] border-emerald-500/70"
              : "bg-[#25131f] border-rose-600/70"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div
                className={`p-2 rounded-lg border ${
                  state.verification_result.verified
                    ? "bg-emerald-950/80 border-emerald-600 text-emerald-300"
                    : "bg-rose-950/80 border-rose-600 text-rose-300"
                }`}
              >
                {state.verification_result.verified ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  <XCircle className="w-5 h-5" />
                )}
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100">
                  {state.verification_result.outcome_summary}
                </h3>
                <p className="text-xs text-slate-300 font-mono mt-0.5">
                  Post-recovery telemetry compared against 4 SLA criteria.
                </p>
              </div>
            </div>

            <span
              className={`text-xs font-mono font-bold px-3 py-1 rounded border ${
                state.verification_result.verified
                  ? "bg-emerald-950 text-emerald-300 border-emerald-600"
                  : "bg-rose-950 text-rose-300 border-rose-600"
              }`}
            >
              {state.verification_result.verified ? "INCIDENT RESOLVED" : "REPLANNING ENGAGED"}
            </span>
          </div>

          {/* Verification Criteria Checks Table */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            {state.verification_result.checks.map((check, idx) => (
              <div
                key={idx}
                className="bg-[#0b1329] p-3 rounded-lg border border-[#1e2e54] space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400">{check.metric}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                      check.passed
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                        : "bg-rose-950 text-rose-400 border border-rose-800"
                    }`}
                  >
                    {check.passed ? "PASS" : "FAIL"}
                  </span>
                </div>
                <div className="text-sm font-bold text-slate-100">{check.value}</div>
                <div className="text-[10px] text-slate-500">Threshold: {check.threshold}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confirmation Dialog before Simulated Recovery Execution (Requirement #12) */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#1e2e54] pb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Confirm Simulated Recovery Execution
                </h3>
              </div>
              <button
                onClick={() => setShowConfirmModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              You are about to execute simulated action{" "}
              <strong className="text-sky-300">{state.recovery_plan?.action_name}</strong>.
              This will apply the recovery changes in the simulated environment and run post-recovery
              telemetry verification across all SLA thresholds.
            </p>

            <div className="bg-[#0b1329] p-3 rounded-lg border border-[#1e2e54] text-xs font-mono space-y-1">
              <div>Action ID: <span className="text-sky-400">{state.recovery_plan?.action_id}</span></div>
              <div>Target: <span className="text-slate-300">{state.recovery_plan?.affected_services.join(", ")}</span></div>
              <div>Mode: <span className={forceFailToggle ? "text-amber-400" : "text-emerald-400"}>
                {forceFailToggle ? "Failure Injection (Replan Demo)" : "Standard (Passing Verification)"}
              </span></div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-3.5 py-1.5 rounded-lg border border-[#1e2e54] text-xs text-slate-300 hover:text-white transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteConfirmed}
                disabled={runningAction}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition shadow cursor-pointer disabled:opacity-50"
              >
                {runningAction ? "Executing..." : "Confirm & Execute"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
