"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Mail, Lock, Eye, EyeOff, ArrowRight, Loader2, AlertCircle } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { PasswordResetModal } from "@/components/auth/PasswordResetModal";
import { useAuth, getRoleDashboardPath } from "@/context/AuthContext";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromParam = searchParams.get("from");

  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setErrorMessage("Please enter your institutional email address.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setErrorMessage("Please enter a valid institutional email address format.");
      return;
    }

    if (!password) {
      setErrorMessage("Please enter your account password.");
      return;
    }

    try {
      setIsSubmitting(true);
      const user = await login(trimmedEmail, password);

      if (fromParam && fromParam.startsWith("/") && !fromParam.startsWith("//")) {
        router.push(fromParam);
      } else {
        router.push(getRoleDashboardPath(user.role));
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSuccess = () => {
    if (fromParam && fromParam.startsWith("/") && !fromParam.startsWith("//")) {
      router.push(fromParam);
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="space-y-5">
      {/* Accessible Error Alert Banner */}
      {errorMessage && (
        <div
          role="alert"
          aria-live="polite"
          className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-rose-800 text-xs shadow-sm animate-in fade-in duration-150"
        >
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-rose-900">Access Denied</p>
            <p className="mt-0.5 text-rose-700 leading-relaxed">{errorMessage}</p>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage(null)}
            className="text-rose-500 hover:text-rose-800 text-xs font-bold px-1.5 py-0.5 rounded cursor-pointer"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Google Single Sign-On Button */}
      <div className="space-y-2">
        <GoogleSignInButton
          onSuccess={handleGoogleSuccess}
          onError={(err) => setErrorMessage(err)}
          theme="outline"
        />
      </div>

      {/* Divider */}
      <div className="relative flex items-center justify-center my-3">
        <div className="w-full border-t border-slate-200" />
        <span className="relative px-3 bg-white text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
          or sign in with email
        </span>
      </div>

      {/* Email / Password Form */}
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Email Field */}
        <div className="space-y-1.5">
          <label
            htmlFor="email-input"
            className="block text-xs font-semibold text-slate-700"
          >
            Institutional Email Address
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Mail className="w-4 h-4" />
            </div>
            <input
              id="email-input"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="netid@campus.edu or staff@campusops.edu"
              disabled={isSubmitting}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 transition disabled:opacity-60"
            />
          </div>
        </div>

        {/* Password Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="password-input"
              className="block text-xs font-semibold text-slate-700"
            >
              Account Password
            </label>
            <button
              type="button"
              onClick={() => setIsResetModalOpen(true)}
              className="text-xs text-teal-700 hover:text-teal-900 font-medium transition cursor-pointer"
            >
              Forgot password?
            </button>
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="password-input"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              disabled={isSubmitting}
              className="w-full pl-10 pr-11 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 transition disabled:opacity-60"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition cursor-pointer"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Remember Me Option */}
        <div className="flex items-center justify-between text-xs pt-0.5">
          <label className="flex items-center gap-2 cursor-pointer text-slate-600 hover:text-slate-900 select-none">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded bg-slate-50 border-slate-300 text-teal-600 focus:ring-teal-500/40 accent-teal-600"
            />
            <span>Remember session on this device</span>
          </label>
        </div>

        {/* Primary Sign In Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-teal-700 via-teal-600 to-emerald-600 hover:from-teal-800 hover:to-emerald-700 text-white font-bold text-sm rounded-xl shadow-md shadow-teal-700/20 transition duration-150 focus:outline-none focus:ring-2 focus:ring-teal-500/50 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed active:scale-[0.99]"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Verifying Credentials...</span>
            </>
          ) : (
            <>
              <span>Sign In to Platform</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      {/* Switch to Registration */}
      <div className="pt-2 text-center text-xs text-slate-500">
        <span>Need a student account? </span>
        <Link
          href="/register"
          className="font-bold text-teal-700 hover:text-teal-900 transition underline underline-offset-2"
        >
          Create student account
        </Link>
      </div>

      {/* Password Recovery Helpdesk Modal */}
      <PasswordResetModal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
      />
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in with your verified institutional credentials to access operations dashboard."
    >
      <Suspense fallback={<div className="text-center py-8 text-xs text-slate-400">Loading secure authentication form...</div>}>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
