"use client";

import React, { useState } from "react";
import {
  InvestigationStateResponse,
  InvestigationTrackerResponse,
} from "@/types/investigation";
import {
  AlertTriangle,
  CheckCircle2,
  GitBranch,
  RotateCcw,
  Play,
  HelpCircle,
  ChevronRight,
  X,
  ArrowRight,
} from "lucide-react";

interface LifecycleWorkflowDiagramProps {
  investigation: InvestigationStateResponse | null;
  tracker: InvestigationTrackerResponse | null;
  onInspectEvidenceId?: (id: string) => void;
  onEscalate?: () => Promise<void>;
  onTriggerReinvestigate?: () => Promise<void>;
  onRunDiagnostic?: () => Promise<void>;
  onApproveReject?: (decision: "approve" | "reject") => Promise<void>;
}

interface WorkflowNode {
  id: string;
  label: string;
  sublabel: string;
  category: "detection" | "orchestrator" | "decision" | "remediation" | "verification";
  stageNum?: number;
  status: "COMPLETED" | "IN_PROGRESS" | "BLOCKED" | "REPLANNING" | "PENDING";
  description: string;
  outcome?: string;
  timestamp?: string | null;
  evidenceIds?: string[];
}

export default function LifecycleWorkflowDiagram({
  investigation,
  tracker,
  onInspectEvidenceId,
  onEscalate,
  onTriggerReinvestigate,
  onRunDiagnostic,
  onApproveReject,
}: LifecycleWorkflowDiagramProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [escalating, setEscalating] = useState<boolean>(false);

  if (!investigation) return null;

  const currentStage = investigation.current_stage;
  const isResolved = currentStage === "RESOLVED";
  const isReplanning = currentStage === "REPLANNING";
  const isAwaitingApproval = currentStage === "AWAITING_APPROVAL";
  const isReadyToExecute = currentStage === "RECOVERY_EXECUTION";
  const isPostRecovery = investigation.recovery_plan?.executed === true;
  const verifiedPass = investigation.verification_result?.verified === true;
  const verifiedFail = investigation.verification_result?.verified === false;
  const hasDiag1 = investigation.tool_history.some((t) => t.category === "network");
  const hasDiag2 = investigation.tool_history.some((t) =>
    ["database", "deployment_config"].includes(t.category)
  );
  const leadingConf =
    investigation.hypotheses.find((h) => h.id === investigation.leading_hypothesis_id)
      ?.confidence_score || 0.78;

  // 15 primary lifecycle sequence nodes
  const nodes: WorkflowNode[] = [
    {
      id: "live_telemetry",
      label: "1. Live Telemetry",
      sublabel: "Ingress Telemetry",
      category: "detection",
      stageNum: 1,
      status: "COMPLETED",
      description: "Continuous ingestion of ingress P99 latency and HTTP 504 error rates from gateway.",
      outcome: "Anomaly detected: Ingress P99 spiked to 10.82s (+801% over SLA limit).",
    },
    {
      id: "auto_error_detection",
      label: "2. Auto Detection",
      sublabel: "Threshold Monitor",
      category: "detection",
      stageNum: 2,
      status: "COMPLETED",
      description: "Gateway 504 timeout rate crossed 5% SLA threshold, reaching 14.8%.",
      outcome: "Threshold breach: HighLatency504GatewayTimeouts firing.",
      evidenceIds: ["a1111111-0000-0000-0000-000000000004"],
    },
    {
      id: "error_bucket",
      label: "3. Error Bucket",
      sublabel: "Classification",
      category: "detection",
      stageNum: 3,
      status: "COMPLETED",
      description: "Categorized into infrastructure/software degradation with P1 priority.",
      outcome: "Classified: Category SOFTWARE, Subsystem AUTH_CASCADE.",
    },
    {
      id: "incident_correlation",
      label: "4. Correlation",
      sublabel: "Trace Linkage",
      category: "detection",
      stageNum: 4,
      status: "COMPLETED",
      description: "Correlated 11 multi-source artifacts via distributed trace req-c83109a1.",
      outcome: "Correlated across gateway, identity service, and database.",
    },
    {
      id: "affected_users_services",
      label: "5. Blast Radius",
      sublabel: "Impact Analysis",
      category: "detection",
      stageNum: 5,
      status: "COMPLETED",
      description: "Identified 420 student sessions impacted; gateway and database degraded.",
      outcome: "Impacted: student-portal-ui, gateway, identity-service, campusops-db.",
    },
    {
      id: "ai_investigation_orchestrator",
      label: "6. AI Orchestrator",
      sublabel: "State Machine",
      category: "orchestrator",
      stageNum: 6,
      status: isResolved ? "COMPLETED" : isReplanning ? "REPLANNING" : "IN_PROGRESS",
      description: "State machine coordinating evidence evaluation and network-first diagnostics.",
      outcome: `Active state: ${currentStage} (Round ${investigation.current_round}/3).`,
    },
    {
      id: "hypothesis_generation",
      label: "7. Hypotheses",
      sublabel: "3 Competing Models",
      category: "orchestrator",
      stageNum: 7,
      status: "COMPLETED",
      description: "Generated 3 failure hypotheses: Network Backbone, DB Connection Pool, and Canary Argon2id.",
      outcome: `Leading candidate: ${investigation.leading_hypothesis_id} (${Math.round(leadingConf * 100)}% conf).`,
    },
    {
      id: "diagnostic_tool_selection",
      label: "8. Tool Selection",
      sublabel: "Network-First",
      category: "orchestrator",
      stageNum: 8,
      status: hasDiag1 ? "COMPLETED" : "IN_PROGRESS",
      description: "Selected network_connectivity_diagnostic to inspect physical switches and gateway.",
      outcome: hasDiag1
        ? "Network L3/L4 switches, DNS, and gateway ICMP verified 100% operational."
        : "Awaiting diagnostic execution.",
    },
    {
      id: "evidence_evaluation",
      label: "9. Diagnostics Run",
      sublabel: "DB Diagnostics",
      category: "orchestrator",
      stageNum: 9,
      status: hasDiag2 ? "COMPLETED" : hasDiag1 ? "IN_PROGRESS" : "PENDING",
      description: "Executed database diagnostics inspecting connection pool starvation.",
      outcome: hasDiag2
        ? "Confirmed: DB pool utilization 15/15 (100% saturation, QueuePool timeout)."
        : "Pending secondary diagnostic.",
    },
    {
      id: "root_cause_decision",
      label: "10. Root Cause",
      sublabel: "Hypothesis Confirmed",
      category: "decision",
      stageNum: 10,
      status:
        investigation.current_stage !== "INITIALIZING" &&
        investigation.current_stage !== "DIAGNOSTIC_EXECUTION" &&
        investigation.current_stage !== "HYPOTHESIS_GENERATION"
          ? "COMPLETED"
          : "PENDING",
      description: "Formulated root cause decision with 94% Bayesian confidence.",
      outcome: `Confirmed: ${investigation.leading_hypothesis_id} (ConfigMap reduced pool to 15).`,
    },
    {
      id: "recovery_recommendation",
      label: "11. Recovery Plan",
      sublabel: "Scale Pool to 50",
      category: "decision",
      stageNum: 11,
      status: investigation.recovery_plan ? "COMPLETED" : "PENDING",
      description: "Formulated remediation plan ACTION-DB-POOL-SCALE-50 with rollback procedure.",
      outcome: investigation.recovery_plan
        ? `${investigation.recovery_plan.action_id}: ${investigation.recovery_plan.action_name}`
        : "Awaiting plan formulation.",
    },
    {
      id: "human_approval",
      label: "12. Human Gate",
      sublabel: "Operator Approval",
      category: "decision",
      stageNum: 12,
      status:
        investigation.recovery_plan?.is_approved === true
          ? "COMPLETED"
          : isAwaitingApproval
          ? "BLOCKED"
          : investigation.recovery_plan?.is_approved === false
          ? "REPLANNING"
          : "PENDING",
      description: "Mandatory human safety gate awaiting explicit operator authorization.",
      outcome:
        investigation.recovery_plan?.is_approved === true
          ? `Approved by ${investigation.recovery_plan.approved_by || "SRE Operator"}`
          : isAwaitingApproval
          ? "Awaiting human operator approval."
          : investigation.recovery_plan?.is_approved === false
          ? "Rejected by operator — replanning."
          : "Pending approval submission.",
    },
    {
      id: "execute_recovery",
      label: "13. Recovery Action",
      sublabel: "Simulated Execution",
      category: "remediation",
      stageNum: 13,
      status:
        isPostRecovery || isResolved
          ? "COMPLETED"
          : isReadyToExecute
          ? "IN_PROGRESS"
          : "PENDING",
      description: "Execute simulated GitOps commit revert, connection drain, and rolling pod restart.",
      outcome: isPostRecovery
        ? "Recovery executed: pool size restored to 50, idle handles released."
        : "Ready for execution.",
    },
    {
      id: "verify_telemetry",
      label: "14. Telemetry Verify",
      sublabel: "4 SLA Checks",
      category: "verification",
      stageNum: 14,
      status: verifiedPass
        ? "COMPLETED"
        : verifiedFail
        ? "REPLANNING"
        : isPostRecovery
        ? "IN_PROGRESS"
        : "PENDING",
      description: "Post-recovery telemetry comparison against 4 SLA threshold criteria.",
      outcome: verifiedPass
        ? "PASSED: All 4 SLA criteria met (P99 latency 240ms, HTTP 504 0.02%)."
        : verifiedFail
        ? "FAILED: Error rate remains above SLA limit (11.5% > 0.5%)."
        : "Awaiting telemetry verification.",
    },
    {
      id: "resolve_incident",
      label: "15. Resolve Incident",
      sublabel: "Audit Sealed",
      category: "verification",
      stageNum: 15,
      status: isResolved ? "COMPLETED" : isReplanning ? "REPLANNING" : "PENDING",
      description: "Incident resolved, database record sealed, and audit log preserved.",
      outcome: isResolved
        ? "Incident resolved and closed in database."
        : isReplanning
        ? "Replanning cycle active."
        : "Awaiting resolution closure.",
    },
  ];

  const getNodeColors = (status: WorkflowNode["status"]) => {
    switch (status) {
      case "COMPLETED":
        return {
          bg: "bg-emerald-950/30",
          border: "border-emerald-600/60",
          text: "text-emerald-300",
          badge: "bg-emerald-950/60 text-emerald-400 border-emerald-800",
          icon: CheckCircle2,
        };
      case "IN_PROGRESS":
        return {
          bg: "bg-sky-950/30",
          border: "border-sky-500",
          text: "text-sky-200",
          badge: "bg-sky-950/60 text-sky-300 border-sky-800",
          icon: Play,
        };
      case "BLOCKED":
        return {
          bg: "bg-amber-950/30",
          border: "border-amber-500",
          text: "text-amber-200",
          badge: "bg-amber-950/60 text-amber-300 border-amber-800",
          icon: AlertTriangle,
        };
      case "REPLANNING":
        return {
          bg: "bg-rose-950/30",
          border: "border-rose-600",
          text: "text-rose-200",
          badge: "bg-rose-950/60 text-rose-300 border-rose-800",
          icon: RotateCcw,
        };
      default:
        return {
          bg: "bg-[#0b1329]",
          border: "border-[#1e2e54]",
          text: "text-slate-500",
          badge: "bg-[#0b1329] text-slate-500 border-[#1e2e54]",
          icon: HelpCircle,
        };
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  const handleEscalateClick = async () => {
    if (!onEscalate) return;
    try {
      setEscalating(true);
      await onEscalate();
    } finally {
      setEscalating(false);
    }
  };

  return (
    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#1e2e54] pb-3">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Incident Investigation Lifecycle
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b1329] text-sky-300 border border-[#1e2e54]">
            {tracker
              ? `Stage ${tracker.current_stage_id} / 13 (${tracker.overall_status})`
              : "15 Stages &bull; 5 Branches"}
          </span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[11px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span className="text-slate-300">Completed</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
            <span className="text-sky-300 font-semibold">Active</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span className="text-slate-300">Blocked Gate</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span className="text-slate-300">Replanning</span>
          </div>
        </div>
      </div>

      {/* Main Horizontal Lifecycle Flow Stepper (Scrollable) */}
      <div className="overflow-x-auto pb-3 pt-2">
        <div className="flex items-center gap-2 min-w-[1280px]">
          {nodes.map((node, idx) => {
            const colors = getNodeColors(node.status);
            const Icon = colors.icon;
            const isSelected = selectedNodeId === node.id;
            const isActive =
              node.status === "IN_PROGRESS" ||
              node.status === "BLOCKED" ||
              node.status === "REPLANNING";

            return (
              <React.Fragment key={node.id}>
                {/* Stage Step Node */}
                <div
                  onClick={() => setSelectedNodeId(isSelected ? null : node.id)}
                  className={`flex flex-col justify-between p-3 rounded-xl border transition-all cursor-pointer select-none shrink-0 w-[156px] h-[106px] relative ${
                    colors.bg
                  } ${colors.border} ${
                    node.status === "IN_PROGRESS"
                      ? "ring-2 ring-sky-500/80 shadow"
                      : node.status === "BLOCKED"
                      ? "ring-2 ring-amber-500/80 shadow"
                      : node.status === "REPLANNING"
                      ? "ring-2 ring-rose-500/80 shadow"
                      : "hover:border-slate-500"
                  } ${isSelected ? "border-sky-400 ring-2 ring-sky-400" : ""}`}
                >
                  {isActive && (
                    <span
                      className={`absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.2 rounded text-[8px] font-mono uppercase font-bold tracking-wider shadow ${
                        node.status === "IN_PROGRESS"
                          ? "bg-sky-500 text-slate-950"
                          : node.status === "BLOCKED"
                          ? "bg-amber-400 text-slate-950"
                          : "bg-rose-500 text-white"
                      }`}
                    >
                      {node.status === "IN_PROGRESS"
                        ? "CURRENT"
                        : node.status === "BLOCKED"
                        ? "GATE"
                        : "REPLAN"}
                    </span>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold text-slate-300">
                      #{node.stageNum}
                    </span>
                    <span
                      className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border ${colors.badge}`}
                    >
                      {node.status}
                    </span>
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-slate-100 leading-snug line-clamp-1">
                      {node.label.replace(/^\d+\.\s*/, "")}
                    </h4>
                    <span className="text-[10px] text-sky-400 font-mono block truncate">
                      {node.sublabel}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-[#1e2e54]/60">
                    <div className="flex items-center gap-1">
                      <Icon className="w-3 h-3 text-current" />
                      <span className="capitalize">{node.category}</span>
                    </div>
                    <ChevronRight className="w-3 h-3 text-slate-500" />
                  </div>
                </div>

                {/* Arrow connector */}
                {idx < nodes.length - 1 && (
                  <div className="shrink-0 text-slate-600 font-mono">
                    <ArrowRight className="w-4 h-4 text-[#1e2e54]" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Decision Branches Sub-Bar with Real Actions */}
      <div className="bg-[#0b1329] border border-[#1e2e54] rounded-xl p-3 text-xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-sky-400" />
            <span className="font-bold uppercase tracking-wider text-slate-200 font-mono text-[11px]">
              Decision Branches & Actions
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Click branch or stage node to inspect details
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 font-mono text-[11px]">
          {/* Branch 1 */}
          <button
            onClick={() => onRunDiagnostic && onRunDiagnostic()}
            className="p-2 rounded-lg bg-[#131d38] border border-[#1e2e54] hover:border-sky-500 text-left transition cursor-pointer"
          >
            <span className="text-amber-400 font-bold block mb-0.5">
              1. Insufficient Evidence:
            </span>
            <span className="text-slate-300 block">
              Run Next Diagnostic (R{investigation.current_round}/3)
            </span>
          </button>

          {/* Branch 2 */}
          <button
            onClick={handleEscalateClick}
            disabled={escalating}
            className="p-2 rounded-lg bg-[#131d38] border border-[#1e2e54] hover:border-rose-500 text-left transition cursor-pointer"
          >
            <span className="text-rose-400 font-bold block mb-0.5 flex items-center justify-between">
              <span>2. Still Unresolved:</span>
              <span className="text-[9px] bg-rose-950/70 text-rose-300 px-1 py-0.2 rounded border border-rose-800">
                {escalating ? "Escalating..." : "Escalate"}
              </span>
            </span>
            <span className="text-slate-300 block">
              Escalate to Tier 3 Platform SRE
            </span>
          </button>

          {/* Branch 3 */}
          <button
            onClick={() => onApproveReject && onApproveReject("reject")}
            className="p-2 rounded-lg bg-[#131d38] border border-[#1e2e54] hover:border-amber-500 text-left transition cursor-pointer"
          >
            <span className="text-amber-400 font-bold block mb-0.5">
              3. Recovery Rejected:
            </span>
            <span className="text-slate-300 block">
              Reject recovery & replan
            </span>
          </button>

          {/* Branch 4 */}
          <button
            onClick={() => onTriggerReinvestigate && onTriggerReinvestigate()}
            className="p-2 rounded-lg bg-[#131d38] border border-[#1e2e54] hover:border-rose-500 text-left transition cursor-pointer"
          >
            <span className="text-rose-400 font-bold block mb-0.5">
              4. Verification Failed:
            </span>
            <span className="text-slate-300 block">
              Trigger replanning loop
            </span>
          </button>

          {/* Branch 5 */}
          <div className="p-2 rounded-lg bg-[#131d38] border border-[#1e2e54] text-left">
            <span className="text-emerald-400 font-bold block mb-0.5">
              5. Verification Passed:
            </span>
            <span className="text-slate-300 block">
              4/4 SLA checks &bull; Resolved
            </span>
          </div>
        </div>
      </div>

      {/* Selected Node Inspector Drawer (Progressive Disclosure) */}
      {selectedNode && (
        <div className="bg-[#0b1329] border border-sky-500/60 rounded-xl p-4 text-xs space-y-2 relative">
          <button
            onClick={() => setSelectedNodeId(null)}
            className="absolute top-3 right-3 text-slate-400 hover:text-slate-100 p-1 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2">
            <span className="font-mono text-sky-400 font-bold text-sm">
              {selectedNode.label}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#131d38] text-slate-300 border border-[#1e2e54]">
              {selectedNode.sublabel}
            </span>
            <span
              className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border ${
                getNodeColors(selectedNode.status).badge
              }`}
            >
              {selectedNode.status}
            </span>
          </div>

          <p className="text-slate-300 font-sans leading-relaxed">
            {selectedNode.description}
          </p>

          {selectedNode.outcome && (
            <div className="p-2.5 rounded bg-[#131d38] border border-[#1e2e54] font-mono text-[11px] text-slate-200">
              <strong className="text-sky-400">Stage Outcome:</strong> {selectedNode.outcome}
            </div>
          )}

          {selectedNode.evidenceIds && selectedNode.evidenceIds.length > 0 && (
            <div className="flex items-center gap-2 pt-1 font-mono text-[11px]">
              <span className="text-slate-400">Associated Evidence:</span>
              {selectedNode.evidenceIds.map((id) => (
                <button
                  key={id}
                  onClick={() => onInspectEvidenceId && onInspectEvidenceId(id)}
                  className="px-2 py-0.5 rounded bg-[#182344] text-sky-300 border border-sky-800 hover:border-sky-500 cursor-pointer"
                >
                  {id.slice(0, 8)}...
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
