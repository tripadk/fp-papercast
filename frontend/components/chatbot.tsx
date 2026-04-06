"use client";

import { useState } from "react";
import { Bot, Loader2, SendHorizontal } from "lucide-react";
import { askPaperQuestion } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

type Props = {
  paperId: string | null;
};

export function ChatbotPanel({ paperId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSend = async () => {
    const trimmedQuestion = question.trim();
    if (!paperId || !trimmedQuestion || loading) return;

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: trimmedQuestion }];
    setMessages(nextMessages);
    setQuestion("");
    setLoading(true);
    setError(null);

    try {
      const response = await askPaperQuestion(paperId, trimmedQuestion, nextMessages);
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
    } catch (requestError: unknown) {
      setError(requestError instanceof Error ? requestError.message : "Chat request failed.");
    } finally {
      setLoading(false);
    }
  };

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

      <div className="custom-scrollbar mb-4 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-4">
        {messages.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
            Ask about the paper&apos;s method, findings, or limitations.
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-2xl px-4 py-3 text-sm ${
                message.role === "user"
                  ? "ml-auto max-w-[85%] bg-sky-500/15 text-sky-100"
                  : "mr-auto max-w-[90%] border border-white/10 bg-white/5 text-slate-200"
              }`}
            >
              {message.content}
            </div>
          ))
        )}
        {loading && (
          <div className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating answer...
          </div>
        )}
      </div>

      <div className="mt-auto rounded-2xl border border-white/15 bg-slate-950/40 p-3">
        <textarea
          rows={2}
          placeholder="Ask about methods, results, limitations..."
          value={question}
          disabled={!paperId || loading}
          onChange={(event) => setQuestion(event.target.value)}
          className="w-full resize-none rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none ring-0 transition placeholder:text-slate-400 focus:border-sky-300/70 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">{error ?? "Answers are generated from the uploaded paper content."}</p>
          <button type="button" className="btn-primary" disabled={!paperId || loading || !question.trim()} onClick={onSend}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizontal className="h-4 w-4" />}
            Send
          </button>
        </div>
      </div>
    </section>
  );
}
