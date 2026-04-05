"use client";

import { ExternalLink, LibraryBig } from "lucide-react";
import type { RelatedPaper } from "@/lib/types";

type Props = {
  papers: RelatedPaper[] | null;
};

export function RelatedPapers({ papers }: Props) {
  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Related Papers</h2>
          <p className="mt-1 text-sm text-slate-300">Discover similar literature from arXiv to continue your review.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <LibraryBig className="h-5 w-5" />
        </div>
      </div>

      {!papers || papers.length === 0 ? (
        <p className="text-sm text-slate-300">Upload a paper to get related research recommendations.</p>
      ) : (
        <div className="custom-scrollbar grid max-h-[300px] gap-3 overflow-y-auto pr-2">
          {papers.map((paper, idx) => (
            <article
              key={`${paper.link}-${idx}`}
              className="rounded-xl border border-white/15 bg-slate-950/35 p-4 transition-all duration-300 hover:scale-105 hover:border-sky-300/60"
            >
              <h3 className="text-sm font-semibold leading-6 text-white">{paper.title}</h3>
              <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-sky-200">{paper.authors}</p>
              <p className="mt-2 max-h-20 overflow-hidden text-sm leading-6 text-slate-200">{paper.summary}</p>
              <a
                href={paper.link}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary mt-3 w-fit"
              >
                View Paper
                <ExternalLink className="h-4 w-4" />
              </a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
