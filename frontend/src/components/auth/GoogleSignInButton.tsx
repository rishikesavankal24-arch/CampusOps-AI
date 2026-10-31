"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface GoogleSignInButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
  theme?: "outline" | "filled_blue" | "filled_black";
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "large" | "medium" | "small";
              width?: number;
              text?: string;
              shape?: "rectangular" | "pill" | "circle";
              logo_alignment?: "left" | "center";
            }
          ) => void;
          prompt: () => void;
        };
      };
    };
    __campusops_gsi_initialized?: boolean;
    __campusops_gsi_client_id?: string;
  }
}

export function GoogleSignInButton({
  onSuccess,
  onError,
  theme = "outline",
}: GoogleSignInButtonProps) {
  const { googleLogin } = useAuth();
  const [configMessage, setConfigMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const buttonContainerRef = useRef<HTMLDivElement | null>(null);

  // Keep callback references stable across renders to prevent effect re-runs
  const successCallbackRef = useRef(onSuccess);
  const errorCallbackRef = useRef(onError);
  const googleLoginRef = useRef(googleLogin);

  useEffect(() => {
    successCallbackRef.current = onSuccess;
    errorCallbackRef.current = onError;
    googleLoginRef.current = googleLogin;
  }, [onSuccess, onError, googleLogin]);

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  const handleCredentialResponse = useCallback(async (response: { credential: string }) => {
    try {
      setIsLoading(true);
      await googleLoginRef.current(response.credential);
      successCallbackRef.current?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google authentication failed";
      errorCallbackRef.current?.(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const renderGoogleButton = useCallback(() => {
    if (!window.google?.accounts?.id || !buttonContainerRef.current || !clientId) {
      return;
    }

    // Initialize ONLY ONCE per client ID across React Strict Mode and component remounts
    if (
      !window.__campusops_gsi_initialized ||
      window.__campusops_gsi_client_id !== clientId
    ) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        cancel_on_tap_outside: true,
      });
      window.__campusops_gsi_initialized = true;
      window.__campusops_gsi_client_id = clientId;
    }

    // Clear previous button render to prevent duplicate iframe stacks
    buttonContainerRef.current.innerHTML = "";

    // Render the Google-branded button
    window.google.accounts.id.renderButton(buttonContainerRef.current, {
      theme: theme,
      size: "large",
      width: 380,
      text: "continue_with",
      shape: "rectangular",
      logo_alignment: "center",
    });
  }, [clientId, handleCredentialResponse, theme]);

  useEffect(() => {
    if (!clientId) {
      return;
    }

    // Check if script is already present in document
    const existingScript = document.querySelector(
      'script[src="https://accounts.google.com/gsi/client"]'
    );

    if (window.google?.accounts?.id) {
      // Script already loaded and ready
      renderGoogleButton();
    } else if (existingScript) {
      // Script tag exists, wait for load event
      existingScript.addEventListener("load", renderGoogleButton);
      return () => {
        existingScript.removeEventListener("load", renderGoogleButton);
      };
    } else {
      // Inject script once
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = renderGoogleButton;
      document.head.appendChild(script);
    }
  }, [clientId, renderGoogleButton]);

  if (!clientId) {
    return (
      <div className="w-full">
        <button
          type="button"
          onClick={() =>
            setConfigMessage(
              "Institutional Google SSO requires NEXT_PUBLIC_GOOGLE_CLIENT_ID to be configured in .env.local. Please sign in with email and password."
            )
          }
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 bg-white hover:bg-slate-50 border border-slate-300 rounded-xl text-slate-700 font-medium text-sm shadow-sm transition focus:outline-none focus:ring-2 focus:ring-teal-500/40 cursor-pointer"
        >
          {/* Google G logo */}
          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>Continue with Google</span>
          <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-100 border border-slate-300 text-slate-600">
            Setup Required
          </span>
        </button>

        {configMessage && (
          <div
            role="alert"
            className="mt-2.5 p-3 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-2 text-xs text-amber-800"
          >
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p>{configMessage}</p>
            </div>
            <button
              onClick={() => setConfigMessage(null)}
              className="text-amber-800 hover:text-amber-950 text-xs font-semibold ml-2 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col items-center">
      <div
        ref={buttonContainerRef}
        className="w-full flex justify-center min-h-[44px] overflow-hidden rounded-xl"
      />
      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-teal-700 font-medium mt-2">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Verifying Google SSO credentials...</span>
        </div>
      )}
    </div>
  );
}
