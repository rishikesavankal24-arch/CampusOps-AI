"use client";

import React from "react";
import Link from "next/link";
import { Cpu, ShieldCheck, Zap, CheckCircle2 } from "lucide-react";
import { CampusNetworkTopology } from "./CampusNetworkTopology";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-[#030e10] font-sans selection:bg-[#00e5bf] selection:text-[#030e10]">
      {/* ========================================================================= */}
      {/* LEFT PANEL — BRAND EXPERIENCE & SEC-OPS DIGITAL TWIN (Dark Midnight-Teal) */}
      {/* ========================================================================= */}
      <aside
        aria-label="CampusOps AI Platform Overview"
        className="hidden lg:flex lg:w-1/2 xl:w-5/12 relative flex-col justify-between p-8 xl:p-12 overflow-hidden bg-gradient-to-br from-[#041518] via-[#05181b] to-[#020b0d] border-r border-teal-900/40"
      >
        {/* Ambient atmospheric glow */}
        <div className="absolute top-[-10%] left-[-10%] w-[450px] h-[450px] bg-[#00e5bf]/10 rounded-full blur-[120px] pointer-events-none animate-ambient-glow" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[400px] h-[400px] bg-teal-500/10 rounded-full blur-[130px] pointer-events-none animate-ambient-glow" />

        {/* Top Header & Brand Mark */}
        <header className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00e5bf] to-teal-700 p-0.5 shadow-lg shadow-[#00e5bf]/20 flex items-center justify-center">
              <div className="w-full h-full bg-[#05181b] rounded-[10px] flex items-center justify-center">
                <Cpu className="w-5 h-5 text-[#00e5bf]" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-white">CampusOps</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-teal-950/90 text-[#00e5bf] border border-[#00e5bf]/40 font-semibold tracking-wide">
                  AI
                </span>
              </div>
              <p className="text-[10px] text-[#84999a] tracking-wider uppercase font-medium">
                Campus IT Operations Platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#05181b]/90 border border-teal-800/40 text-[11px] text-[#84999a]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00e5bf] animate-ping" />
            <span className="font-mono text-white text-[10px]">SecOps v0.1</span>
          </div>
        </header>

        {/* Center Content: Headline + Network Topology + Feature Highlights */}
        <div className="relative z-10 my-auto py-4 space-y-4 max-w-lg">
          {/* Main Product Headline & Supporting Description */}
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-0.5 rounded-full bg-teal-950/80 border border-[#00e5bf]/30 text-[#00e5bf] text-xs font-medium shadow-sm">
              <Zap className="w-3.5 h-3.5" />
              <span>Intelligent Campus Operations</span>
            </div>
            <h1 className="text-2xl xl:text-3xl font-extrabold tracking-tight text-white leading-tight">
              Intelligent Campus Operations. One Unified Platform.
            </h1>
            <p className="text-xs xl:text-sm text-[#84999a] leading-relaxed">
              Bring campus IT incidents, network intelligence and AI-assisted troubleshooting into one secure operational workspace.
            </p>
          </div>

          {/* Interactive Network Topology Visual */}
          <CampusNetworkTopology />

          {/* Feature Highlights Grid */}
          <div className="grid grid-cols-2 gap-2.5 pt-1">
            <div className="flex items-start gap-2 p-2.5 rounded-xl bg-[#05181b]/80 border border-teal-900/30">
              <CheckCircle2 className="w-4 h-4 text-[#00e5bf] shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-semibold text-white block">Predictive Diagnostics</span>
                <span className="text-[10px] text-[#84999a] leading-tight block">
                  AI root cause identification across network assets.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2 p-2.5 rounded-xl bg-[#05181b]/80 border border-teal-900/30">
              <CheckCircle2 className="w-4 h-4 text-[#00e5bf] shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-semibold text-white block">Zero-Trust RBAC</span>
                <span className="text-[10px] text-[#84999a] leading-tight block">
                  HttpOnly session cookies with Argon2id protection.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Security Standards */}
        <footer className="relative z-10 flex items-center justify-between text-xs text-[#84999a] pt-4 border-t border-teal-900/40">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#00e5bf]" />
            <span>Role-Based Access Control</span>
          </div>
          <span className="font-mono text-[11px]">BFF Architecture</span>
        </footer>
      </aside>

      {/* ========================================================================= */}
      {/* RIGHT PANEL — AUTHENTICATION FORM (Clean White / Light Surface)           */}
      {/* ========================================================================= */}
      <main className="w-full lg:w-1/2 xl:w-7/12 flex flex-col justify-between p-6 sm:p-10 lg:p-12 xl:p-16 min-h-screen overflow-y-auto bg-slate-50 text-slate-900">
        {/* Mobile Header (Visible only on smaller viewports) */}
        <header className="lg:hidden flex items-center justify-between mb-6 pb-4 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#05181b] border border-teal-700/60 flex items-center justify-center shadow-sm">
              <Cpu className="w-4 h-4 text-[#00e5bf]" />
            </div>
            <div>
              <span className="text-base font-bold text-slate-900 tracking-tight">CampusOps AI</span>
              <p className="text-[9px] text-teal-700 uppercase tracking-wider font-semibold">
                Campus IT Operations Platform
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200 font-semibold">
            SecOps
          </span>
        </header>

        {/* Form Container (White Card on Light Surface) */}
        <div className="w-full max-w-md mx-auto my-auto space-y-6">
          <div className="space-y-1.5">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {title}
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">{subtitle}</p>
          </div>

          {/* Form Card Content */}
          <div className="bg-white border border-slate-200/80 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 space-y-5">
            {children}
          </div>
        </div>

        {/* Bottom Legal Notice */}
        <footer className="w-full max-w-md mx-auto pt-8 text-center text-[11px] text-slate-500 space-y-1">
          <p>Institutional computing credentials are strictly confidential.</p>
          <p>
            Authorized access only •{" "}
            <Link
              href="/login"
              className="text-slate-600 hover:text-teal-700 transition underline underline-offset-2"
            >
              Security Policy & Audit Logs
            </Link>
          </p>
        </footer>
      </main>
    </div>
  );
}
