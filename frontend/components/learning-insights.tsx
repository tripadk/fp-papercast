"use client";

import { Brain } from "lucide-react";

type Props = {
  userEmail: string;
  paperId: string | null;
};

export function LearningInsights({ paperId }: Props) {
  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Learning Insights</h2>
          <p className="mt-1 text-sm text-slate-300">Unified recommendations from goal, progress, confusion, and recall.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <Brain className="h-5 w-5" />
        </div>
      </div>

      <div className="rounded-xl border border-white/15 bg-slate-950/35 p-4 text-sm text-slate-300">
        {paperId
          ? "Learning insights are temporarily unavailable while user_id-dependent backend APIs remain disabled."
          : "Upload a paper to view core analysis. Learning APIs are temporarily disabled in the frontend."}
      </div>
    </section>
  );
}
