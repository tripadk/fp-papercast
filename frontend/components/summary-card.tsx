import React from "react";
import { SummarySectionSkeleton } from "@/components/loading-skeletons";

interface SummaryCardProps {
  title: string;
  content: string;
}

export default function SummaryCard({ title, content }: SummaryCardProps) {
  const summary = content?.trim();

  if (!summary) {
    return <SummarySectionSkeleton />;
  }

  return (
    <div className="rounded-xl bg-slate-900 p-5 shadow-md">
      <h2 className="mb-3 text-xl font-semibold text-white">{title}</h2>
      <div className="max-h-[220px] overflow-y-auto pr-2">
        <p className="whitespace-pre-line text-base leading-relaxed tracking-wide text-gray-100">{summary}</p>
      </div>
    </div>
  );
}

