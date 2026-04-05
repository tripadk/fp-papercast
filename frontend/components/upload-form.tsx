"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Loader2, Sparkles, UploadCloud } from "lucide-react";
import { uploadPaper } from "@/lib/api";
import type { LearningMode, OutputLanguage, PodcastLength, PodcastStyle, StudyGoal, UploadResult } from "@/lib/types";

type Props = {
  onComplete: (result: UploadResult) => void;
  userEmail: string;
  podcastLength: PodcastLength;
  podcastStyle: PodcastStyle;
  studyGoal: StudyGoal;
  learningMode: LearningMode;
  outputLanguage: OutputLanguage;
  onPodcastLengthChange: (value: PodcastLength) => void;
  onPodcastStyleChange: (value: PodcastStyle) => void;
  onStudyGoalChange: (value: StudyGoal) => void;
  onLearningModeChange: (value: LearningMode) => void;
  onOutputLanguageChange: (value: OutputLanguage) => void;
};

export function UploadForm({
  onComplete,
  userEmail,
  podcastLength,
  podcastStyle,
  studyGoal,
  learningMode,
  outputLanguage,
  onPodcastLengthChange,
  onPodcastStyleChange,
  onStudyGoalChange,
  onLearningModeChange,
  onOutputLanguageChange,
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!loading) {
      setProgress(0);
      return;
    }

    const interval = window.setInterval(() => {
      setProgress((prev) => (prev >= 92 ? prev : prev + 4));
    }, 240);

    return () => window.clearInterval(interval);
  }, [loading]);

  const setPickedFile = (picked: File | null) => {
    if (!picked) return;
    if (picked.type !== "application/pdf") {
      setError("Only PDF files are allowed.");
      return;
    }
    setError(null);
    setFile(picked);
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Please choose a PDF file.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await uploadPaper(file, {
        podcastLength,
        podcastStyle,
        studyGoal,
        learningMode,
        outputLanguage,
        userEmail,
      });
      setProgress(100);
      onComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected upload error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Upload Paper</h2>
          <p className="mt-1 text-sm text-slate-300">Drop a PDF and generate an AI summary + podcast in one flow.</p>
        </div>
        <div className="rounded-2xl border border-sky-300/30 bg-sky-500/10 p-3 text-sky-200">
          <Sparkles className="h-5 w-5" />
        </div>
      </div>

      <form onSubmit={onSubmit} className="grid gap-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <label className="grid gap-1 text-sm text-slate-200">
            Podcast Length
            <select
              className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
              value={podcastLength}
              onChange={(event) => onPodcastLengthChange(event.target.value as PodcastLength)}
              disabled={loading}
            >
              <option value="quick">Quick Brief (2 min)</option>
              <option value="standard">Standard (5 min)</option>
              <option value="deep">Deep Dive (10 min)</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm text-slate-200">
            Podcast Style
            <select
              className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
              value={podcastStyle}
              onChange={(event) => onPodcastStyleChange(event.target.value as PodcastStyle)}
              disabled={loading}
            >
              <option value="casual">Casual Podcast</option>
              <option value="lecture">Academic Lecture</option>
              <option value="debate">Debate Discussion</option>
              <option value="news">News Explanation</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm text-slate-200">
            Study Goal
            <select
              className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
              value={studyGoal}
              onChange={(event) => onStudyGoalChange(event.target.value as StudyGoal)}
              disabled={loading}
            >
              <option value="general">General Learning</option>
              <option value="upsc">UPSC</option>
              <option value="jee">JEE</option>
              <option value="neet">NEET</option>
              <option value="cat">CAT</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm text-slate-200">
            Learning Mode
            <select
              className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
              value={learningMode}
              onChange={(event) => onLearningModeChange(event.target.value as LearningMode)}
              disabled={loading}
            >
              <option value="beginner">Beginner</option>
              <option value="exam_mode">Exam Mode</option>
              <option value="deep_learning">Deep Learning</option>
              <option value="quick_revision">Quick Revision</option>
            </select>
          </label>

          <label className="grid gap-1 text-sm text-slate-200">
            Output Language
            <select
              className="rounded-xl border border-white/15 bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
              value={outputLanguage}
              onChange={(event) => onOutputLanguageChange(event.target.value as OutputLanguage)}
              disabled={loading}
            >
              <option value="english">English</option>
              <option value="hindi">Hindi</option>
            </select>
          </label>
        </div>

        <div
          className={`group rounded-2xl border-2 border-dashed p-8 transition-all duration-300 ${
            isDragging
              ? "border-sky-300 bg-sky-500/10 shadow-[0_0_0_4px_rgba(56,189,248,0.15)]"
              : "border-slate-500/60 bg-slate-900/40 hover:border-sky-300/70 hover:bg-slate-900/65"
          }`}
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragEnter={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setIsDragging(false);
          }}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            const droppedFile = event.dataTransfer.files?.[0] ?? null;
            setPickedFile(droppedFile);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(event) => setPickedFile(event.target.files?.[0] ?? null)}
          />
          <div className="mx-auto flex max-w-md flex-col items-center gap-3 text-center">
            <div className="rounded-2xl bg-white/10 p-4 text-sky-200 transition group-hover:bg-sky-500/20">
              <UploadCloud className="h-8 w-8" />
            </div>
            <p className="text-sm text-slate-200 sm:text-base">Drag and drop your PDF here, or click to browse files.</p>
            <button type="button" className="btn-secondary" onClick={() => inputRef.current?.click()}>
              Choose PDF
            </button>
          </div>
        </div>

        {file && (
          <div className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-slate-200">
            <FileText className="h-4 w-4 text-sky-300" />
            Selected: {file.name}
          </div>
        )}

        {loading && (
          <div className="space-y-2">
            <div className="h-2 rounded-full bg-slate-800/80">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-sky-400 via-blue-500 to-indigo-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-slate-300">Generating summary, transcript, and podcast audio...</p>
          </div>
        )}

        <button className="btn-primary w-full sm:w-fit" type="submit" disabled={loading}>
          {loading ? (
            <span className="inline-flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Processing...
            </span>
          ) : (
            "Generate Podcast"
          )}
        </button>

        {error && <small className="text-sm text-rose-300">{error}</small>}
      </form>
    </section>
  );
}
