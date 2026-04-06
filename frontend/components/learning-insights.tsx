"use client";

import { useEffect, useState } from "react";
import { Brain, Loader2 } from "lucide-react";
import { fetchLearningInsights } from "@/lib/api";
import type { LearningInsightsResponse } from "@/lib/types";

type Props = {
  userEmail: string;
  paperId: string | null;
};

export function LearningInsights({ userEmail, paperId }: Props) {
  const [insights, setInsights] = useState<LearningInsightsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userEmail) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchLearningInsights(userEmail)
      .then((payload) => {
        if (!cancelled) {
          setInsights(payload);
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Could not load learning insights.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [userEmail, paperId]);

  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Learning Insights</h2>
          <p className="mt-1 text-sm text-slate-300">Strengths, weak areas, and recommended next steps.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <Brain className="h-5 w-5" />
        </div>
      </div>

      {loading ? (
        <div className="inline-flex items-center gap-2 text-sm text-slate-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading insights...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-200">{error}</div>
      ) : insights ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4 text-sm text-slate-200">
            {insights.progress_summary}
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">Strengths</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {insights.strengths.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">Weaknesses</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {insights.weaknesses.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">Recommendations</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                {insights.recommendations.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4 text-sm text-slate-300">
          {paperId ? "Insights will appear after the paper and learner data are loaded." : "Upload a paper to begin."}
        </div>
      )}
    </section>
  );
}
