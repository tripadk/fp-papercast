"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import { Bot, FileUp, LayoutDashboard, LogOut, Sparkles } from "lucide-react";
import Link from "next/link";
import { explainPaperLikeIm12, fetchContentStatus, fetchPaperDetail, fetchPaperHistory } from "@/lib/api";
import { ResearchToolkit } from "@/components/research-toolkit";
import { UploadForm } from "@/components/upload-form";
import { MethodologyDiagram } from "@/components/methodology-diagram";
import { RelatedPapers } from "@/components/related-papers";
import { LearningInsights } from "@/components/learning-insights";
import SummaryCard from "@/components/summary-card";
import { PodcastAudioPlayer } from "@/components/audio-player";
import { ChatbotPanel } from "@/components/chatbot";
import { PaperRow } from "@/components/paper-row";
import type { PaperShelfItem } from "@/components/paper-card";
import type {
  LearningMode,
  OutputLanguage,
  PaperHistoryItem,
  PodcastLength,
  PodcastStyle,
  StudyGoal,
  UploadResult,
} from "@/lib/types";

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [result, setResult] = useState<UploadResult | null>(null);
  const [podcastLength, setPodcastLength] = useState<PodcastLength>("standard");
  const [podcastStyle, setPodcastStyle] = useState<PodcastStyle>("casual");
  const [studyGoal, setStudyGoal] = useState<StudyGoal>("general");
  const [learningMode, setLearningMode] = useState<LearningMode>("beginner");
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>("english");
  const [activeTab, setActiveTab] = useState<"overview" | "toolkit">("overview");
  const [history, setHistory] = useState<PaperHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [simpleExplanation, setSimpleExplanation] = useState<string>("");
  const [simpleExplanationLoading, setSimpleExplanationLoading] = useState(false);
  const [simpleExplanationError, setSimpleExplanationError] = useState<string>("");

  const ready = useMemo(() => status === "authenticated" && !!session, [session, status]);
  const userEmail = session?.user?.email ?? "anonymous@local";
  const recentPapers = useMemo<PaperShelfItem[]>(
    () =>
      history.map((paper) => ({
        id: paper.paper_id,
        title: paper.paper_title,
        description: paper.summary || "Recently uploaded research paper.",
        paperId: paper.paper_id,
      })),
    [history]
  );

  const recommendedPapers = useMemo<PaperShelfItem[]>(
    () =>
      (result?.related_papers ?? []).map((paper, index) => ({
        id: `${paper.link}-${index}`,
        title: paper.title,
        description: paper.summary || "Recommended from semantic similarity.",
        href: paper.link,
      })),
    [result?.related_papers]
  );

  const trendingPapers = useMemo<PaperShelfItem[]>(
    () =>
      (recommendedPapers.length > 0 ? recommendedPapers : recentPapers)
        .slice(0, 8)
        .map((paper, index) => ({
          ...paper,
          id: `${paper.id}-trend-${index}`,
        })),
    [recommendedPapers, recentPapers]
  );

  useEffect(() => {
    if (!ready) return;

    let cancelled = false;
    setHistoryLoading(true);
    fetchPaperHistory()
      .then((items) => {
        if (!cancelled) setHistory(items);
      })
      .catch(() => {
        if (!cancelled) setHistory([]);
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ready, result?.paper_id]);

  useEffect(() => {
    setSimpleExplanation("");
    setSimpleExplanationError("");
    setSimpleExplanationLoading(false);
    if (result?.output_language) {
      setOutputLanguage(result.output_language);
    }
  }, [result?.paper_id]);

  useEffect(() => {
    const paperId = result?.paper_id;
    const taskStatus = result?.task_status ?? {};
    if (!paperId) return;

    const values = Object.values(taskStatus);
    const hasPending = values.length > 0 && values.some((statusValue) => statusValue !== "completed");
    if (!hasPending) return;

    let cancelled = false;
    const interval = window.setInterval(async () => {
      try {
        const latest = await fetchContentStatus(paperId);
        if (cancelled) return;
        setResult(latest);
      } catch {
        // Keep polling cycle resilient to temporary backend/network failures.
      }
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [result?.paper_id, result?.task_status]);

  if (status === "loading") {
    return (
      <main className="app-shell">
        <div className="glass-card animate-fade-in p-10 text-center">
          <p className="text-base text-slate-200">Loading your PaperCast workspace...</p>
        </div>
      </main>
    );
  }

  if (!ready) {
    return (
      <main className="app-shell">
        <section className="glass-card animate-fade-in mx-auto max-w-xl p-10 text-center">
          <h2 className="text-3xl font-semibold text-white">Sign in required</h2>
          <p className="mt-3 text-sm text-slate-300">
            Use Google OAuth to access your PaperCast dashboard and generate podcast-ready paper insights.
          </p>
          <button className="btn-primary mt-6" onClick={() => signIn("google", { callbackUrl: "/dashboard" })}>
            Sign in with Google
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <div className="mx-auto w-full max-w-7xl px-6 lg:px-12">
        <nav className="fixed top-0 left-0 right-0 z-40 animate-fade-in border-b border-white/10 bg-black/30 backdrop-blur-lg">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-6 py-2.5 lg:px-12 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-white/5 p-1.5 text-sky-200">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <p className="text-base font-semibold text-white">PaperCast</p>
                <p className="text-xs text-slate-300">Signed in as {session?.user?.email}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/profile" className="nav-pill border-white/10 bg-white/5 text-slate-200">
                Profile
              </Link>
              <a href="#dashboard" className="nav-pill border-white/10 bg-white/5 text-slate-200">
                <LayoutDashboard className="h-4 w-4" />
                Dashboard
              </a>
              <a href="#upload" className="nav-pill border-white/10 bg-white/5 text-slate-200">
                <FileUp className="h-4 w-4" />
                Upload Paper
              </a>
              <a href="#chat" className="nav-pill border-white/10 bg-white/5 text-slate-200">
                <Bot className="h-4 w-4" />
                Chat
              </a>
              <button className="nav-pill border-white/10 bg-white/5 text-slate-200" onClick={() => setActiveTab("toolkit")}>
                Research Toolkit
              </button>
              <button className="nav-pill border-white/10 bg-white/5 text-slate-200" onClick={() => signOut()}>
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          </div>
        </nav>

        <section id="dashboard" className="glass-card mt-20 animate-fade-in overflow-hidden">
          <div className="mx-auto max-w-5xl px-6 py-16 text-left">
            <span className="section-label">
              <Sparkles className="h-3.5 w-3.5" />
              AI Research Workspace
            </span>
            <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              Turn research papers into clear summaries and{" "}
              <span className="bg-gradient-to-r from-sky-300 to-blue-400 bg-clip-text text-transparent">podcasts</span>
              .
            </h1>
            <p className="mt-4 max-w-2xl text-lg text-gray-400">
              PaperCast extracts key concepts, generates student-friendly audio, and gives you grounded answers from
              your uploaded paper.
            </p>
            <div className="mt-6 flex flex-wrap gap-4">
              <a
                href="#upload"
                className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-700"
              >
                Upload Paper
              </a>
              <a
                href="#trending"
                className="inline-flex items-center justify-center rounded-xl border border-white/20 px-5 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-white/5"
              >
                Try Demo
              </a>
            </div>
            <div className="mt-6 flex flex-wrap gap-3 text-slate-300">
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm">Summary Intelligence</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm">Podcast Narration</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm">Context-Aware Chat</span>
            </div>
          </div>
        </section>

        <section id="upload" className="mt-8">
          <UploadForm
            onComplete={setResult}
            userEmail={userEmail}
            podcastLength={podcastLength}
            podcastStyle={podcastStyle}
            studyGoal={studyGoal}
            learningMode={learningMode}
            outputLanguage={outputLanguage}
            onPodcastLengthChange={setPodcastLength}
            onPodcastStyleChange={setPodcastStyle}
            onStudyGoalChange={setStudyGoal}
            onLearningModeChange={setLearningMode}
            onOutputLanguageChange={setOutputLanguage}
          />
        </section>

        <section id="trending" className="mt-10 space-y-4">
          {historyLoading ? (
            <p className="text-sm text-slate-300">Loading papers...</p>
          ) : recentPapers.length === 0 ? (
            <div className="rounded-xl border border-white/10 bg-white/5 p-8 text-center shadow-[0_12px_40px_-24px_rgba(15,23,42,0.9)]">
              <div className="mx-auto mb-4 h-20 w-20 rounded-2xl border border-white/10 bg-gradient-to-b from-white/10 to-white/5" />
              <p className="text-sm text-slate-200">Upload your first paper to get started</p>
              <div className="mt-5">
                <a
                  href="#upload"
                  className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-700"
                >
                  Upload Paper
                </a>
              </div>
            </div>
          ) : (
              <PaperRow
              title="Recently Uploaded Papers"
              papers={recentPapers}
              onView={async (paperId) => {
                const detail = await fetchPaperDetail(paperId, userEmail);
                setResult(detail);
              }}
            />
          )}
        </section>

        <section className="mt-10 space-y-4">
          {recommendedPapers.length === 0 ? (
            <p className="text-sm text-slate-300">Upload a paper to get recommendation rows.</p>
          ) : (
            <PaperRow title="Recommended Papers" papers={recommendedPapers} />
          )}
        </section>

        <section className="mt-10 space-y-4">
          {trendingPapers.length === 0 ? (
            <p className="text-sm text-slate-300">Trending papers will appear here.</p>
          ) : (
            <PaperRow
              title="Trending Research"
              papers={trendingPapers}
              onView={async (paperId) => {
                const detail = await fetchPaperDetail(paperId, userEmail);
                setResult(detail);
              }}
            />
          )}
        </section>

        <section className="mt-10 mb-6 flex flex-wrap gap-2">
          <button
            className={`btn-secondary ${activeTab === "overview" ? "border-sky-300/70 bg-sky-500/15" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview
          </button>
          <button
            className={`btn-secondary ${activeTab === "toolkit" ? "border-sky-300/70 bg-sky-500/15" : ""}`}
            onClick={() => setActiveTab("toolkit")}
          >
            Research Toolkit
          </button>
        </section>

        <section className="mt-8">
          <LearningInsights userEmail={userEmail} paperId={result?.paper_id ?? null} />
        </section>

        {activeTab === "overview" ? (
          <section className="mt-8">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 lg:items-start">
              <div className="flex h-full flex-col gap-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-200">Section 1</p>
                <div className="h-full">
                  <SummaryCard title="Research Paper Summary" content={result?.summary ?? ""} />
                </div>
                {result?.paper_id && (
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={async () => {
                        setSimpleExplanationLoading(true);
                        setSimpleExplanationError("");
                        try {
                          const response = await explainPaperLikeIm12(result.paper_id);
                          setSimpleExplanation(response.explanation);
                        } catch (error: unknown) {
                          setSimpleExplanationError(
                            error instanceof Error ? error.message : "Could not generate explanation."
                          );
                        } finally {
                          setSimpleExplanationLoading(false);
                        }
                      }}
                      disabled={simpleExplanationLoading}
                      className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-all duration-300 hover:scale-105 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {simpleExplanationLoading ? "Explaining..." : "Explain Like I'm 12"}
                    </button>
                  </div>
                )}
                {(simpleExplanation || simpleExplanationError) && (
                  <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-6">
                    {simpleExplanationError ? (
                      <p className="text-sm text-rose-200">{simpleExplanationError}</p>
                    ) : (
                      <div>
                        <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-blue-200">
                          Explain Like I&apos;m 12
                        </h3>
                        <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-100">{simpleExplanation}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex h-full flex-col gap-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-200">Section 2</p>
                <div className="h-full">
                  <PodcastAudioPlayer
                    audioPath={result?.audio_path ?? null}
                    audioReady={result?.audio_ready ?? false}
                    processingStatus={result?.processing_status ?? []}
                    transcriptPath={result?.transcript_path ?? null}
                    transcriptDownloadUrl={result?.transcript_download_url ?? null}
                    podcastScriptDownloadUrl={result?.podcast_script_download_url ?? null}
                    chapters={result?.chapters ?? []}
                    transcriptSentences={result?.transcript_sentences ?? []}
                    podcastLength={result?.podcast_length ?? podcastLength}
                    podcastStyle={result?.podcast_style ?? podcastStyle}
                    onPodcastLengthChange={setPodcastLength}
                    onPodcastStyleChange={setPodcastStyle}
                  />
                </div>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2 lg:items-start">
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-200">Methodology Diagram</p>
                <MethodologyDiagram steps={result?.methodology_steps ?? null} mermaidCode={result?.mermaid_diagram ?? null} />
              </div>
              <div className="space-y-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-200">Related Papers</p>
                <RelatedPapers papers={result?.related_papers ?? null} />
              </div>
            </div>
          </section>
        ) : (
          <section className="mt-8 animate-fade-in">
            <span className="section-label">Research Toolkit</span>
            <ResearchToolkit
              topCitations={result?.top_citations ?? null}
              studyNotes={result?.study_notes ?? null}
              importanceExtraction={result?.importance_extraction ?? null}
              notesDownloadUrl={result?.notes_download_url ?? null}
              paperId={result?.paper_id ?? null}
              userEmail={userEmail}
            />
          </section>
        )}

        <section id="chat" className="mt-10 animate-fade-in">
          <span className="section-label">Section 3 - Chatbot</span>
          <div className="glass-card p-0">
            <ChatbotPanel paperId={result?.paper_id ?? null} />
          </div>
        </section>
      </div>
    </main>
  );
}
