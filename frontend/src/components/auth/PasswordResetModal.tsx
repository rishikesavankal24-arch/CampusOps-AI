"use client";

import React, { useEffect } from "react";
import { X, HelpCircle, ShieldAlert, ArrowLeft } from "lucide-react";

interface PasswordResetModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PasswordResetModal({ isOpen, onClose }: PasswordResetModalProps) {
  // Listen for Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reset-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-md bg-[#05181b] border border-teal-800/80 rounded-2xl p-6 shadow-2xl text-[#f5faf9] space-y-4">
        {/* Close Button */}
        <button
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-1.5 text-[#84999a] hover:text-white rounded-lg hover:bg-slate-800 transition focus:outline-none focus:ring-2 focus:ring-[#00e5bf]/60 cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-teal-950/90 border border-[#00e5bf]/40 rounded-xl text-[#00e5bf]">
            <HelpCircle className="w-6 h-6" />
          </div>
          <div>
            <h3 id="reset-modal-title" className="text-lg font-bold text-white">
              Password Recovery Procedure
            </h3>
            <p className="text-xs text-[#00e5bf]">Institutional IT Identity Verification</p>
          </div>
        </div>

        {/* Security Notice */}
        <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-xl flex items-start gap-2.5 text-xs text-amber-200/90">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            Automated self-service password reset is not enabled in this deployment. To maintain campus system security, password changes and account recovery must be performed by an Administrator.
          </p>
        </div>

        <div className="space-y-3 pt-1 text-xs text-slate-300">
          <p className="leading-relaxed">
            Please reach out directly to your designated campus system administrator or IT department with your verified student or staff identification to request a credential reset.
          </p>
          <div className="p-3 bg-slate-900/80 border border-teal-900/50 rounded-xl space-y-1">
            <span className="font-semibold text-white block">Administrator Action Required</span>
            <p className="text-[11px] text-[#84999a] leading-relaxed">
              Administrators can reset user credentials or promote roles securely using the backend offline administration utility (<code className="text-teal-400 font-mono">scripts/seed_admin.py</code>).
            </p>
          </div>
        </div>

        {/* Return to Sign In Action */}
        <div className="pt-3 border-t border-teal-900/50 flex justify-end">
          <button
            onClick={onClose}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-500 hover:to-emerald-500 text-[#030e10] font-bold text-xs rounded-xl shadow-md transition focus:outline-none focus:ring-2 focus:ring-[#00e5bf] cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Sign In</span>
          </button>
        </div>
      </div>
    </div>
  );
}
