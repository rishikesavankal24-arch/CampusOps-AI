"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { ChatMessage, SourceReference } from "@/types/chat";
import {
  Cpu,
  Bot,
  User as UserIcon,
  Send,
  Loader2,
  Trash2,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ArrowLeft,
  Info,
} from "lucide-react";

const SUGGESTED_PROMPTS = [
  "How do I configure eduroam Wi-Fi on my laptop?",
  "What are the student lab printing quotas and costs?",
  "What is the campus password complexity and reset policy?",
  "How do I set up the campus VPN for remote access?",
];

export default function ChatPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const [isSeedingSample, setIsSeedingSample] = useState(false);
  const [seedNotification, setSeedNotification] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const idCounterRef = useRef(1);

  // Redirect if unauthenticated
  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login?from=/chat");
    }
  }, [user, isLoading, router]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  // Load chat history safely inside effect
  useEffect(() => {
    let isMounted = true;
    if (!user) return;

    async function fetchHistory() {
      try {
        const res = await fetch("/api/chat/history?limit=50", { credentials: "same-origin" });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setMessages(data.messages || []);
        } else if (res.status === 401) {
          router.push("/login?from=/chat");
        }
      } catch {
        if (isMounted) setErrorMsg("Failed to load conversation history from server.");
      } finally {
        if (isMounted) setIsLoadingHistory(false);
      }
    }

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [user, router]);

  // Toggle expandable source accordion
  const toggleSourceExpand = (messageId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  // Submit question
  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputText).trim();
    if (!textToSend || isGenerating) return;

    setErrorMsg(null);
    setInputText("");

    const currentCounter = idCounterRef.current++;
    const tempUserId = `user-${currentCounter}`;
    const userMessage: ChatMessage = {
      id: tempUserId,
      role: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: textToSend }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to receive answer from assistant.");
      }

      const assistantMessage: ChatMessage = {
        id: data.message_id || `assistant-${currentCounter}`,
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        is_grounded: data.is_grounded,
        insufficient_context: data.insufficient_context,
        created_at: data.created_at || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Service error occurred.";
      setErrorMsg(msg);
      const errorChatMsg: ChatMessage = {
        id: `err-${currentCounter}`,
        role: "assistant",
        content: `Error: ${msg}. Please try asking your question again.`,
        isError: true,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorChatMsg]);
    } finally {
      setIsGenerating(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  // Handle key press (Enter to submit, Shift+Enter for newline)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Clear chat history
  const handleClearHistory = async () => {
    if (!confirm("Are you sure you want to permanently clear your conversation history?")) {
      return;
    }
    try {
      const res = await fetch("/api/chat/history", { method: "DELETE" });
      if (res.ok) {
        setMessages([]);
      }
    } catch {
      setErrorMsg("Failed to clear chat history.");
    }
  };

  // Seed sample knowledge for test demonstration
  const handleSeedSampleKnowledge = async () => {
    try {
      setIsSeedingSample(true);
      setSeedNotification(null);
      const res = await fetch("/api/knowledge/seed-sample", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        const count = Array.isArray(data) ? data.length : 1;
        setSeedNotification(`Successfully ingested ${count} sample campus IT runbooks into the vector database!`);
      } else {
        setSeedNotification(data.detail || "Failed to seed sample knowledge.");
      }
    } catch {
      setSeedNotification("Network error seeding sample runbooks.");
    } finally {
      setIsSeedingSample(false);
      setTimeout(() => setSeedNotification(null), 6000);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030e10] text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-teal-500/20 border-t-teal-500 rounded-full animate-spin" />
          <p className="text-xs text-teal-400 font-medium">Verifying campus session credentials...</p>
        </div>
      </div>
    );
  }

  const isStaff = user.role === "support" || user.role === "admin";

  return (
    <div className="min-h-screen bg-[#030e10] text-slate-100 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-teal-900/40 bg-[#05181b]/80 backdrop-blur-md sticky top-0 z-30 shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="p-1.5 rounded-lg bg-teal-950/60 border border-teal-800/40 hover:border-teal-500 text-teal-300 hover:text-white transition"
              title="Return to Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>

            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-teal-500/20 border border-teal-500/40 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-teal-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white tracking-tight">CampusOps AI</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-900/60 text-teal-300 border border-teal-700/40">
                    IT Assistant
                  </span>
                </div>
                <p className="text-[10px] text-teal-400/80 uppercase font-semibold">
                  RAG-Grounded Campus Troubleshooting
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isStaff && (
              <button
                onClick={handleSeedSampleKnowledge}
                disabled={isSeedingSample}
                className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-950/70 hover:bg-teal-900/80 border border-teal-700/60 text-teal-300 text-xs font-medium transition cursor-pointer disabled:opacity-50"
                title="Index sample IT runbooks for Wi-Fi, printing, password policy and VPN"
              >
                {isSeedingSample ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                )}
                <span>Seed Sample Runbooks</span>
              </button>
            )}

            <button
              onClick={handleClearHistory}
              disabled={messages.length === 0}
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/60 hover:bg-rose-950/60 border border-slate-700 hover:border-rose-700 text-slate-300 hover:text-rose-300 text-xs font-medium transition cursor-pointer disabled:opacity-30 disabled:pointer-events-none"
              title="Clear conversation history"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Clear Chat</span>
            </button>
          </div>
        </div>
      </header>

      {/* Seed Notification Alert */}
      {seedNotification && (
        <div className="max-w-4xl mx-auto w-full px-4 pt-3">
          <div className="p-3 bg-teal-950/80 border border-teal-600/60 rounded-xl flex items-center justify-between text-xs text-teal-200">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{seedNotification}</span>
            </div>
            <button
              onClick={() => setSeedNotification(null)}
              className="text-teal-400 hover:text-white text-xs px-2"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Main Chat Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-6 flex flex-col justify-between">
        {/* Messages Thread */}
        <div className="flex-1 overflow-y-auto space-y-6 pb-6">
          {isLoadingHistory ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
              <p className="text-xs">Loading conversation history...</p>
            </div>
          ) : messages.length === 0 ? (
            /* Empty State */
            <div className="py-8 sm:py-12 text-center space-y-6">
              <div className="inline-flex p-4 rounded-2xl bg-teal-950/50 border border-teal-700/40 text-teal-400 mb-2">
                <Bot className="w-10 h-10" />
              </div>
              <div className="space-y-2 max-w-md mx-auto">
                <h2 className="text-xl sm:text-2xl font-extrabold text-white">
                  Campus IT Operations Assistant
                </h2>
                <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                  Ask questions about campus Wi-Fi, lab printing quotas, single sign-on passwords, or VPN access. Answers are retrieved directly from verified university runbooks.
                </p>
              </div>

              {/* Prompt Suggestions */}
              <div className="max-w-lg mx-auto pt-2">
                <div className="text-[11px] font-semibold text-teal-400 uppercase tracking-wider mb-3">
                  Sample Campus IT Inquiries
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {SUGGESTED_PROMPTS.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(prompt)}
                      className="p-3 rounded-xl bg-slate-900/80 hover:bg-[#062428] border border-teal-900/50 hover:border-teal-500/60 text-xs text-slate-200 hover:text-teal-200 transition text-left cursor-pointer flex items-start gap-2 shadow-sm"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-teal-400 shrink-0 mt-0.5" />
                      <span>{prompt}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-teal-800/40 text-[11px] text-slate-400">
                <Info className="w-3.5 h-3.5 text-teal-400" />
                <span>pgvector Cosine Semantic Retrieval Active • Untrusted Context Guard Enforced</span>
              </div>
            </div>
          ) : (
            /* Messages List */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {/* Assistant Avatar */}
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-xl bg-teal-950 border border-teal-700/60 flex items-center justify-center text-teal-400 shrink-0 mt-1">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-lg ${
                    msg.role === "user"
                      ? "bg-gradient-to-r from-teal-700 to-teal-800 text-white rounded-tr-none"
                      : msg.isError
                      ? "bg-rose-950/70 border border-rose-800 text-rose-200 rounded-tl-none"
                      : "bg-[#05181b] border border-teal-900/70 text-slate-200 rounded-tl-none"
                  }`}
                >
                  {/* Assistant Status Tag */}
                  {msg.role === "assistant" && !msg.isError && (
                    <div className="mb-2 flex items-center gap-2">
                      {msg.is_grounded ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-teal-950 border border-teal-700/60 text-[10px] font-semibold text-emerald-400">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          <span>Verified from Campus Knowledge Base</span>
                        </span>
                      ) : msg.insufficient_context ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-950/60 border border-amber-800/60 text-[10px] font-semibold text-amber-300">
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          <span>No Direct Match in Knowledge Base</span>
                        </span>
                      ) : null}
                    </div>
                  )}

                  {/* Message Content */}
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

                  {/* Sources Accordion (when available) */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-teal-900/60">
                      <button
                        onClick={() => toggleSourceExpand(msg.id)}
                        className="flex items-center justify-between w-full text-[11px] font-semibold text-teal-300 hover:text-teal-200 transition py-1 cursor-pointer"
                      >
                        <span className="flex items-center gap-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-teal-400" />
                          <span>Retrieved Sources ({msg.sources.length})</span>
                        </span>
                        {expandedSources[msg.id] ? (
                          <ChevronUp className="w-3.5 h-3.5" />
                        ) : (
                          <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {expandedSources[msg.id] && (
                        <div className="mt-2 space-y-2">
                          {msg.sources.map((src: SourceReference, sIdx: number) => (
                            <div
                              key={sIdx}
                              className="p-2.5 rounded-xl bg-slate-900/90 border border-teal-900/50 text-[11px] space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-semibold text-white truncate max-w-[240px]">
                                  {src.title}
                                </span>
                                <span className="px-1.5 py-0.5 rounded bg-teal-950 text-teal-300 border border-teal-800/60 text-[10px] font-mono shrink-0">
                                  {Math.round(src.similarity * 100)}% match
                                </span>
                              </div>
                              <p className="text-slate-400 leading-snug line-clamp-3">
                                {src.snippet}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Timestamp */}
                  <div className="mt-2 text-right">
                    <span className="text-[10px] text-slate-400">
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                {/* User Avatar */}
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-xl bg-teal-800 border border-teal-600 flex items-center justify-center text-white shrink-0 mt-1">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* Thinking / Ingesting Indicator */}
          {isGenerating && (
            <div className="flex gap-3 justify-start items-center">
              <div className="w-8 h-8 rounded-xl bg-teal-950 border border-teal-700/60 flex items-center justify-center text-teal-400 shrink-0">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
              <div className="p-3 rounded-2xl rounded-tl-none bg-[#05181b] border border-teal-900/70 text-teal-300 text-xs flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-400" />
                <span>Searching knowledge base and generating grounded answer...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Alert Banner */}
        {errorMsg && (
          <div className="mb-3 p-3 bg-rose-950/80 border border-rose-800 rounded-xl text-rose-200 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-rose-400 hover:text-white px-1.5"
            >
              ✕
            </button>
          </div>
        )}

        {/* Input Bar */}
        <div className="relative bg-[#05181b] border border-teal-900/80 rounded-2xl p-2.5 shadow-2xl focus-within:border-teal-500/80 transition">
          <textarea
            ref={textareaRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a campus IT question (e.g. Wi-Fi setup, PaperCut quotas, password reset)..."
            rows={2}
            className="w-full bg-transparent text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none resize-none px-2 py-1 leading-relaxed"
          />

          <div className="flex items-center justify-between pt-2 px-1 border-t border-teal-900/40">
            <div className="text-[10px] text-slate-400 hidden sm:block">
              Press <kbd className="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">Shift+Enter</kbd> for newline
            </div>

            <button
              onClick={() => handleSendMessage()}
              disabled={!inputText.trim() || isGenerating}
              className="ml-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-[#030e10] font-bold text-xs shadow-md transition disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <span>Send</span>
                  <Send className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
