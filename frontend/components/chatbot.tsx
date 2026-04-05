"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Loader2, Send, UserRound } from "lucide-react";
import { askPaperQuestion, fetchChatHistory } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

type Props = {
  paperId: string | null;
};

export function ChatbotPanel({ paperId }: Props) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const isDisabled = useMemo(() => !paperId || loading, [paperId, loading]);

  useEffect(() => {
    setQuestion("");
    setMessages([]);
    setLoading(false);
    if (!paperId) return;

    let cancelled = false;
    fetchChatHistory(paperId)
      .then((history) => {
        if (cancelled || history.length === 0) return;
        const restored: ChatMessage[] = [];
        history.forEach((item) => {
          restored.push({ role: "user", content: item.user_message });
          restored.push({ role: "assistant", content: item.assistant_response });
        });
        setMessages(restored);
      })
      .catch(() => undefined);

    return () => {
      cancelled = true;
    };
  }, [paperId]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const onAsk = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!paperId || !question.trim()) return;

    const userQuestion = question.trim();
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: userQuestion }]);
    setLoading(true);

    try {
      const nextHistory = [...messages, { role: "user" as const, content: userQuestion }];
      const result = await askPaperQuestion(paperId, userQuestion, nextHistory);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
    } catch (err) {
      const details = err instanceof Error ? err.message : "Chat failed";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${details}` }]);
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
      {paperId && messages.length === 0 && (
        <p className="mb-3 mt-0 text-sm text-slate-300">
          Ask about the paper. Follow-up questions are supported, and answers stay grounded in the uploaded paper.
        </p>
      )}

      <div
        ref={listRef}
        className="custom-scrollbar mb-4 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-4"
      >
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`flex ${message.role === "assistant" ? "justify-start" : "justify-end"}`}
          >
            <div
              className={`max-w-[86%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm transition ${
                message.role === "assistant"
                  ? "border border-sky-300/25 bg-sky-400/10 text-slate-100"
                  : "border border-indigo-300/30 bg-indigo-400/20 text-indigo-50"
              }`}
            >
              <div className="mb-1 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.15em]">
                {message.role === "assistant" ? (
                  <>
                    <Bot className="h-3.5 w-3.5" />
                    PaperCast
                  </>
                ) : (
                  <>
                    <UserRound className="h-3.5 w-3.5" />
                    You
                  </>
                )}
              </div>
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/10 px-3 py-2 text-sm text-slate-200">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      <form onSubmit={onAsk} className="mt-auto rounded-2xl border border-white/15 bg-slate-950/40 p-3">
        <textarea
          rows={2}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about methods, results, limitations..."
          disabled={isDisabled}
          className="w-full resize-none rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none ring-0 transition placeholder:text-slate-400 focus:border-sky-300/70"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-400">Answers stay grounded in uploaded paper context.</p>
          <button type="submit" className="btn-primary" disabled={isDisabled}>
            <Send className="h-4 w-4" />
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
