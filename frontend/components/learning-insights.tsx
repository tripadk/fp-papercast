"use client";

import { useEffect, useMemo, useState } from "react";
import { Brain, GitBranch, TrendingUp, TriangleAlert } from "lucide-react";
import {
  fetchConfusionStatus,
  fetchKnowledgeGraph,
  fetchLearningEfficiency,
  fetchLearningNextAction,
  fetchLearningState,
  fetchNextMode,
} from "@/lib/api";
import { toUserId } from "@/lib/user-id";
import type {
  ConfusionStatusResponse,
  KnowledgeGraphResponse,
  LearningEfficiencyResponse,
  LearningNextActionResponse,
  LearningStateResponse,
  NextModeResponse,
} from "@/lib/types";

type Props = {
  userEmail: string;
  paperId: string | null;
};

export function LearningInsights({ userEmail, paperId }: Props) {
  const userId = toUserId(userEmail);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [learningState, setLearningState] = useState<LearningStateResponse | null>(null);
  const [efficiency, setEfficiency] = useState<LearningEfficiencyResponse | null>(null);
  const [nextAction, setNextAction] = useState<LearningNextActionResponse | null>(null);
  const [nextMode, setNextMode] = useState<NextModeResponse | null>(null);
  const [confusion, setConfusion] = useState<ConfusionStatusResponse | null>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<KnowledgeGraphResponse | null>(null);

  useEffect(() => {
    if (!userId) return;
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [statePayload, efficiencyPayload] = await Promise.all([
          fetchLearningState(userId),
          fetchLearningEfficiency(userId),
        ]);
        if (cancelled) return;
        setLearningState(statePayload);
        setEfficiency(efficiencyPayload);

        const avgAccuracy =
          efficiencyPayload.prioritized_topics.length > 0
            ? efficiencyPayload.prioritized_topics.reduce((acc, item) => acc + item.quiz_accuracy, 0) /
              efficiencyPayload.prioritized_topics.length
            : 0;
        const avgTime =
          efficiencyPayload.prioritized_topics.length > 0
            ? efficiencyPayload.prioritized_topics.reduce((acc, item) => acc + item.time_spent, 0) /
              efficiencyPayload.prioritized_topics.length
            : 300;

        const nextActionPayload = await fetchLearningNextAction({
          user_id: userId,
          recent_activity: {
            recent_correct_rate: avgAccuracy,
            avg_response_time_seconds: 30,
            last_mode: statePayload.topics[0]?.next_mode_hint ?? "notes",
            sessions_last_7_days: 3,
          },
        });
        if (!cancelled) setNextAction(nextActionPayload);

        if (paperId) {
          const [modePayload, confusionPayload, graphPayload] = await Promise.all([
            fetchNextMode(paperId, {
              user_email: userEmail,
              accuracy: avgAccuracy,
              time_spent: Math.max(60, Math.round(avgTime)),
              engagement: 0.7,
            }),
            fetchConfusionStatus(paperId, userEmail),
            fetchKnowledgeGraph(paperId),
          ]);
          if (cancelled) return;
          setNextMode(modePayload);
          setConfusion(confusionPayload);
          setKnowledgeGraph(graphPayload);
        } else {
          setNextMode(null);
          setConfusion(null);
          setKnowledgeGraph(null);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load learning insights.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [paperId, userEmail, userId]);

  const weakTopics = useMemo(
    () => (learningState?.topics ?? []).filter((item) => item.priority === "high").slice(0, 6),
    [learningState]
  );
  const confusedTopics = useMemo(
    () => (confusion?.topics ?? []).filter((item) => item.topic_status === "confused").slice(0, 4),
    [confusion]
  );

  const avgMastery = useMemo(() => {
    const topics = learningState?.topics ?? [];
    if (topics.length === 0) return 0;
    const sum = topics.reduce((acc, item) => acc + item.mastery_level, 0);
    return Math.round(sum / topics.length);
  }, [learningState]);

  const avgRetention = useMemo(() => {
    const topics = learningState?.topics ?? [];
    if (topics.length === 0) return 0;
    const sum = topics.reduce((acc, item) => acc + item.retention_score, 0);
    return Math.round(sum / topics.length);
  }, [learningState]);

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

      {loading && <p className="text-sm text-slate-300">Loading learning insights...</p>}
      {error && <p className="text-sm text-rose-300">{error}</p>}

      {!loading && !error && (
        <div className="grid gap-4 lg:grid-cols-3">
          <article className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">Next Recommended Action</h3>
            <p className="mt-3 text-sm text-slate-100">
              <strong>Topic:</strong> {nextAction?.next_topic ?? "N/A"}
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Mode:</strong> {nextAction?.next_mode ?? nextMode?.current_mode ?? "notes"}
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Difficulty:</strong> {nextAction?.difficulty_level ?? "medium"}
            </p>
          </article>

          <article className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
            <h3 className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">
              <TrendingUp className="h-3.5 w-3.5" />
              Learning Progress
            </h3>
            <p className="mt-3 text-sm text-slate-100">
              <strong>Avg Mastery:</strong> {avgMastery}%
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Avg Retention:</strong> {avgRetention}%
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Efficiency Score:</strong> {Math.round(efficiency?.average_learning_efficiency_score ?? 0)}
            </p>
          </article>

          <article className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
            <h3 className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">
              <GitBranch className="h-3.5 w-3.5" />
              Knowledge Graph
            </h3>
            <p className="mt-3 text-sm text-slate-100">
              <strong>Topics:</strong> {knowledgeGraph?.knowledge_graph.topics.length ?? 0}
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Navigation Nodes:</strong> {knowledgeGraph?.knowledge_navigation.length ?? 0}
            </p>
            <p className="mt-1 text-sm text-slate-100">
              <strong>Learning Paths:</strong> {knowledgeGraph?.learning_path.length ?? 0}
            </p>
          </article>
        </div>
      )}

      {!loading && !error && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <article className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">Weak Topics</h3>
            {weakTopics.length === 0 ? (
              <p className="mt-2 text-sm text-slate-300">No weak topics detected.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {weakTopics.map((topic) => (
                  <li key={topic.topic} className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100">
                    {topic.topic}
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
            <h3 className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-sky-200">
              <TriangleAlert className="h-3.5 w-3.5" />
              Confusion Status
            </h3>
            {confusedTopics.length === 0 ? (
              <p className="mt-2 text-sm text-slate-300">No confused topics detected.</p>
            ) : (
              <ul className="mt-2 space-y-2">
                {confusedTopics.map((topic) => (
                  <li key={topic.topic} className="rounded-lg border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
                    {topic.topic}
                  </li>
                ))}
              </ul>
            )}
          </article>
        </div>
      )}
    </section>
  );
}
