"use client";

import { Bot } from "lucide-react";

type Props = {
  paperId: string | null;
};

export function ChatbotPanel({ paperId }: Props) {
  return (
    <section className="flex h-[620px] flex-col rounded-3xl p-5 sm:p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Paper Chat</h2>
          <p className="mt-1 text-sm text-slate-300">Ask grounded questions about the uploaded research paper.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <Bot className="h-5 w-5" />
        </div>
      </div>

      {!paperId && <p className="mb-3 text-sm text-slate-300">Upload a paper first to enable Q&A.</p>}
      {paperId && (
        <p className="mb-3 mt-0 text-sm text-slate-300">
          Paper chat is temporarily unavailable while only the stable backend API surface is enabled.
        </p>
      )}

      <div className="custom-scrollbar mb-4 flex-1 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
          Chat requests are disabled in the frontend until the backend-supported route set is expanded again.
        </div>
      </div>

      <div className="mt-auto rounded-2xl border border-white/15 bg-slate-950/40 p-3">
        <textarea
          rows={2}
          placeholder="Ask about methods, results, limitations..."
          disabled
          className="w-full resize-none rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none ring-0 transition placeholder:text-slate-400 focus:border-sky-300/70"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">Only upload, history, and profile requests are active.</p>
          <button type="button" className="btn-primary" disabled>
            Send
          </button>
        </div>
      </div>
    </section>
  );
}
