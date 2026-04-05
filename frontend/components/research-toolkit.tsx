"use client";

import { useEffect, useState } from "react";
import { Download, Library } from "lucide-react";
import { backendAssetUrl } from "@/lib/backend-url";
import { fetchActiveRecall, submitActiveRecallAttempt, updateConfusionStatus, updateLearningEfficiency } from "@/lib/api";
import { toUserId } from "@/lib/user-id";
import { NotesSectionSkeleton } from "@/components/loading-skeletons";
import type { ActiveRecallItem, ImportanceExtraction, StudyNotes } from "@/lib/types";

type Props = {
  topCitations: string[] | null;
  studyNotes: StudyNotes | null;
  importanceExtraction: ImportanceExtraction | null;
  notesDownloadUrl: string | null;
  paperId: string | null;
  userEmail: string;
};

export function ResearchToolkit({
  topCitations,
  studyNotes,
  importanceExtraction,
  notesDownloadUrl,
  paperId,
  userEmail,
}: Props) {
  const userId = toUserId(userEmail);
  const pdfUrl = notesDownloadUrl ? backendAssetUrl(notesDownloadUrl) : null;
  const [recallItems, setRecallItems] = useState<ActiveRecallItem[]>([]);
  const [revealedIds, setRevealedIds] = useState<Record<string, boolean>>({});
  const [revealTimes, setRevealTimes] = useState<Record<string, number>>({});
  const [recallError, setRecallError] = useState<string | null>(null);
  const noteEntries = studyNotes
      ? [
        { title: "Core Idea", value: studyNotes.core_idea },
        { title: "Key Concepts", value: studyNotes.key_concepts },
        { title: "Key Points", value: studyNotes.key_points },
        { title: "Important Results", value: studyNotes.important_results },
        { title: "Limitations", value: studyNotes.limitations },
        { title: "Applications", value: studyNotes.applications },
        { title: "Quick Revision", value: studyNotes.quick_revision },
      ]
    : [];

  useEffect(() => {
    if (!paperId || !studyNotes) {
      setRecallItems([]);
      setRevealedIds({});
      setRevealTimes({});
      setRecallError(null);
      return;
    }

    let cancelled = false;
    fetchActiveRecall(paperId, userEmail)
      .then((items) => {
        if (!cancelled) {
          setRecallItems(items);
          setRecallError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setRecallItems([]);
          setRecallError(error instanceof Error ? error.message : "Could not load active recall prompts.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [paperId, studyNotes, userEmail]);

  return (
    <section className="space-y-6">
      <section className="glass-card p-6 sm:p-8">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold text-white">Top Citations</h2>
            <p className="mt-1 text-sm text-slate-300">Most referenced works extracted from the uploaded paper.</p>
          </div>
          <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
            <Library className="h-5 w-5" />
          </div>
        </div>
        {!topCitations || topCitations.length === 0 ? (
          <p className="text-sm text-slate-300">No references detected.</p>
        ) : (
          <ul className="custom-scrollbar max-h-[260px] space-y-2 overflow-y-auto pr-2 text-sm text-slate-100">
            {topCitations.map((citation, idx) => (
              <li key={`${citation}-${idx}`} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2">
                {citation}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="glass-card p-6 sm:p-8">
        <div className="mb-4">
          <h2 className="text-2xl font-semibold text-white">Importance Extraction</h2>
          <p className="mt-1 text-sm text-slate-300">Exam-priority classification generated from paper content.</p>
        </div>
        {!importanceExtraction ? (
          <p className="text-sm text-slate-300">No prioritized points available yet.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              { key: "must_know", title: "Must Know", items: importanceExtraction.must_know },
              { key: "important", title: "Important", items: importanceExtraction.important },
              { key: "optional", title: "Optional", items: importanceExtraction.optional },
            ].map((section) => (
              <article key={section.key} className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">{section.title}</h3>
                {section.items.length === 0 ? (
                  <p className="mt-2 text-sm text-slate-300">No items.</p>
                ) : (
                  <ul className="mt-2 space-y-2 text-sm text-slate-100">
                    {section.items.map((item, idx) => (
                      <li key={`${section.key}-${idx}`} className="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5">
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="glass-card p-6 sm:p-8">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold text-white">Study Notes</h2>
            <p className="mt-1 text-sm text-slate-300">Structured revision notes for assignments and exam prep.</p>
          </div>
          {pdfUrl && (
            <a className="btn-secondary" href={pdfUrl} download>
              <Download className="h-4 w-4" />
              Download Notes (PDF)
            </a>
          )}
        </div>
        {!studyNotes ? (
          <NotesSectionSkeleton />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {noteEntries.map((entry) => (
              <article
                key={entry.title}
                className="rounded-xl border border-white/15 bg-slate-950/35 p-4 transition-all duration-300 hover:scale-105 hover:border-sky-300/60"
              >
                <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">{entry.title}</h3>
                <p className="mt-2 text-sm leading-7 text-slate-100">{entry.value}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="glass-card p-6 sm:p-8">
        <div className="mb-4">
          <h2 className="text-2xl font-semibold text-white">Active Recall Mode</h2>
          <p className="mt-1 text-sm text-slate-300">Try to recall key concepts before revealing the answer.</p>
        </div>

        {recallError && <p className="text-sm text-rose-300">{recallError}</p>}
        {!studyNotes ? (
          <NotesSectionSkeleton />
        ) : recallItems.length === 0 ? (
          <p className="text-sm text-slate-300">No recall prompts available yet.</p>
        ) : (
          <div className="space-y-3">
            {recallItems.map((item) => {
              const isRevealed = !!revealedIds[item.id];
              return (
                <article key={item.id} className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">{item.topic}</p>
                  <p className="mt-2 text-sm text-slate-100">{item.prompt}</p>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => {
                        setRevealedIds((prev) => ({ ...prev, [item.id]: true }));
                        setRevealTimes((prev) => ({ ...prev, [item.id]: Date.now() }));
                      }}
                    >
                      Reveal Answer
                    </button>
                    {isRevealed && (
                      <>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white transition-all duration-300 hover:scale-105 hover:bg-emerald-700"
                          onClick={async () => {
                            const responseTimeSeconds = Math.max(
                              1,
                              Math.round((Date.now() - (revealTimes[item.id] ?? Date.now())) / 1000)
                            );
                            await submitActiveRecallAttempt({
                              userEmail,
                              paperId: paperId ?? "",
                              topic: item.topic,
                              isCorrect: true,
                            });
                            if (paperId) {
                              await Promise.all([
                                updateConfusionStatus(paperId, {
                                  user_email: userEmail,
                                  topic: item.topic,
                                  question: item.prompt,
                                  is_correct: true,
                                  response_time_seconds: responseTimeSeconds,
                                }),
                                updateLearningEfficiency(userId, {
                                  topic: item.topic,
                                  accuracy: 1,
                                  attempts: 1,
                                  time_spent: responseTimeSeconds,
                                }),
                              ]);
                            }
                          }}
                        >
                          I got it right
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white transition-all duration-300 hover:scale-105 hover:bg-rose-700"
                          onClick={async () => {
                            const responseTimeSeconds = Math.max(
                              1,
                              Math.round((Date.now() - (revealTimes[item.id] ?? Date.now())) / 1000)
                            );
                            await submitActiveRecallAttempt({
                              userEmail,
                              paperId: paperId ?? "",
                              topic: item.topic,
                              isCorrect: false,
                            });
                            if (paperId) {
                              await Promise.all([
                                updateConfusionStatus(paperId, {
                                  user_email: userEmail,
                                  topic: item.topic,
                                  question: item.prompt,
                                  is_correct: false,
                                  response_time_seconds: responseTimeSeconds,
                                }),
                                updateLearningEfficiency(userId, {
                                  topic: item.topic,
                                  accuracy: 0,
                                  attempts: 1,
                                  time_spent: responseTimeSeconds,
                                }),
                              ]);
                            }
                          }}
                        >
                          I got it wrong
                        </button>
                      </>
                    )}
                  </div>
                  {isRevealed && (
                    <div className="mt-3 rounded-lg border border-sky-400/30 bg-sky-500/10 p-3">
                      <p className="text-sm text-slate-100">{item.answer}</p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </section>
  );
}
