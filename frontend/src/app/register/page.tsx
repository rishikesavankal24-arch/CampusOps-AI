"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  User as UserIcon,
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Shield,
  XCircle,
} from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { useAuth } from "@/context/AuthContext";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Password validation checks
  const isLengthValid = password.length >= 8;
  const hasMixedCase = /[a-z]/.test(password) && /[A-Z]/.test(password);
  const hasNumberOrSpecial = /[\d!@#$%^&*(),.?":{}|<>]/.test(password);
  const doPasswordsMatch = password === confirmPassword && confirmPassword.length > 0;

  // Strength calculation (0 - 4)
  const calculateStrength = (): number => {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (hasMixedCase) score++;
    if (hasNumberOrSpecial) score++;
    return score;
  };

  const strength = calculateStrength();

  const getStrengthLabel = (): { text: string; color: string } => {
    if (!password) return { text: "None", color: "text-slate-400" };
    switch (strength) {
      case 1:
        return { text: "Weak", color: "text-rose-600" };
      case 2:
        return { text: "Fair", color: "text-amber-600" };
      case 3:
        return { text: "Good", color: "text-teal-600" };
      case 4:
      default:
        return { text: "Strong", color: "text-emerald-600" };
    }
  };

  const strengthMeta = getStrengthLabel();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedName = name.trim();
    if (!trimmedName || trimmedName.length < 2) {
      setErrorMessage("Please enter your full name (at least 2 characters).");
      return;
    }

    const trimmedEmail = email.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!trimmedEmail || !emailRegex.test(trimmedEmail)) {
      setErrorMessage("Please enter a valid institutional email address format.");
      return;
    }

    if (!isLengthValid) {
      setErrorMessage("Password must be at least 8 characters long.");
      return;
    }

    if (!hasMixedCase) {
      setErrorMessage("Password must contain both uppercase and lowercase letters.");
      return;
    }

    if (!hasNumberOrSpecial) {
      setErrorMessage("Password must contain at least one number or special character.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match. Please verify both fields.");
      return;
    }

    if (!agreeTerms) {
      setErrorMessage("You must acknowledge the campus IT acceptable use policy.");
      return;
    }

    try {
      setIsSubmitting(true);
      await register(trimmedName, trimmedEmail, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create Student Account"
      subtitle="Register with your institutional credentials to submit and monitor campus IT incidents."
    >
      <div className="space-y-4">
        {/* Error Alert Banner */}
        {errorMessage && (
          <div
            role="alert"
            aria-live="polite"
            className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-2.5 text-rose-800 text-xs shadow-sm animate-in fade-in duration-150"
          >
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-rose-900">Registration Error</p>
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

        {/* Security Role Transparency Notice */}
        <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-2.5 text-xs text-teal-900">
          <Shield className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <span className="font-bold text-teal-950">Role Policy:</span> All public self-registrations automatically receive the <span className="font-semibold text-teal-800">Student</span> role. IT Support and Administrator privileges are provisioned through secure institutional workflows.
          </p>
        </div>

        {/* Google SSO Quick Registration */}
        <div className="space-y-2">
          <GoogleSignInButton
            onSuccess={() => router.push("/dashboard")}
            onError={(err) => setErrorMessage(err)}
            theme="outline"
          />
        </div>

        {/* Divider */}
        <div className="relative flex items-center justify-center my-2">
          <div className="w-full border-t border-slate-200" />
          <span className="relative px-3 bg-white text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
            or register with email
          </span>
        </div>

        {/* Registration Form */}
        <form onSubmit={handleSubmit} className="space-y-3" noValidate>
          {/* Full Name */}
          <div className="space-y-1">
            <label htmlFor="name-input" className="block text-xs font-semibold text-slate-700">
              Full Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <UserIcon className="w-4 h-4" />
              </div>
              <input
                id="name-input"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Student"
                disabled={isSubmitting}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 transition disabled:opacity-60"
              />
            </div>
          </div>

          {/* Institutional Email */}
          <div className="space-y-1">
            <label htmlFor="email-input" className="block text-xs font-semibold text-slate-700">
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
                placeholder="netid@campus.edu"
                disabled={isSubmitting}
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 transition disabled:opacity-60"
              />
            </div>
          </div>

          {/* Password */}
          <div className="space-y-1">
            <label htmlFor="password-input" className="block text-xs font-semibold text-slate-700">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                id="password-input"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
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

          {/* Password Strength Indicator Meter */}
          {password.length > 0 && (
            <div className="space-y-1 pt-0.5">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-500">Password Strength:</span>
                <span className={`font-semibold ${strengthMeta.color}`}>{strengthMeta.text}</span>
              </div>
              <div className="grid grid-cols-4 gap-1.5 h-1.5 w-full">
                <div
                  className={`rounded-full transition-colors ${
                    strength >= 1
                      ? strength === 1
                        ? "bg-rose-500"
                        : strength === 2
                        ? "bg-amber-500"
                        : "bg-teal-600"
                      : "bg-slate-200"
                  }`}
                />
                <div
                  className={`rounded-full transition-colors ${
                    strength >= 2
                      ? strength === 2
                        ? "bg-amber-500"
                        : "bg-teal-600"
                      : "bg-slate-200"
                  }`}
                />
                <div
                  className={`rounded-full transition-colors ${
                    strength >= 3 ? "bg-teal-600" : "bg-slate-200"
                  }`}
                />
                <div
                  className={`rounded-full transition-colors ${
                    strength >= 4 ? "bg-emerald-600" : "bg-slate-200"
                  }`}
                />
              </div>
            </div>
          )}

          {/* Confirm Password */}
          <div className="space-y-1">
            <label htmlFor="confirm-password-input" className="block text-xs font-semibold text-slate-700">
              Confirm Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                id="confirm-password-input"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••••••"
                disabled={isSubmitting}
                className="w-full pl-10 pr-11 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600 transition disabled:opacity-60"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition cursor-pointer"
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Live Validation Checklist Box */}
          {password.length > 0 && (
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                {isLengthValid ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span className={isLengthValid ? "text-slate-900 font-medium" : "text-slate-500"}>
                  Minimum 8 characters
                </span>
              </div>
              <div className="flex items-center gap-2">
                {hasMixedCase ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span className={hasMixedCase ? "text-slate-900 font-medium" : "text-slate-500"}>
                  Contains uppercase and lowercase letters
                </span>
              </div>
              <div className="flex items-center gap-2">
                {hasNumberOrSpecial ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span className={hasNumberOrSpecial ? "text-slate-900 font-medium" : "text-slate-500"}>
                  Contains a number or special character
                </span>
              </div>
              {confirmPassword.length > 0 && (
                <div className="flex items-center gap-2">
                  {doPasswordsMatch ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-rose-500" />
                  )}
                  <span className={doPasswordsMatch ? "text-slate-900 font-medium" : "text-rose-600 font-medium"}>
                    {doPasswordsMatch ? "Passwords match" : "Passwords do not match"}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Terms Agreement Checkbox */}
          <div className="pt-1">
            <label className="flex items-start gap-2.5 cursor-pointer text-xs text-slate-600 hover:text-slate-900 select-none">
              <input
                type="checkbox"
                required
                checked={agreeTerms}
                onChange={(e) => setAgreeTerms(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded bg-slate-50 border-slate-300 text-teal-600 focus:ring-teal-500/40 accent-teal-600"
              />
              <span className="leading-snug">
                I agree to the CampusOps AI Acceptable Use Policy and understand my student account activity is subject to security audit logging.
              </span>
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-teal-700 via-teal-600 to-emerald-600 hover:from-teal-800 hover:to-emerald-700 text-white font-bold text-sm rounded-xl shadow-md shadow-teal-700/20 transition duration-150 focus:outline-none focus:ring-2 focus:ring-teal-500/50 disabled:opacity-60 cursor-pointer disabled:cursor-not-allowed active:scale-[0.99]"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-white" />
                <span>Creating Student Account...</span>
              </>
            ) : (
              <>
                <span>Complete Student Registration</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Switch to Login */}
        <div className="pt-1 text-center text-xs text-slate-500">
          <span>Already have an account? </span>
          <Link
            href="/login"
            className="font-bold text-teal-700 hover:text-teal-900 transition underline underline-offset-2"
          >
            Sign in to platform
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}
