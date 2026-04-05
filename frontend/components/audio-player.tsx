"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Download, FileText, Headphones, Loader2, PlayCircle } from "lucide-react";
import { backendAssetUrl } from "@/lib/backend-url";
import { fetchTranscript } from "@/lib/api";
import { PodcastPlayerSkeleton } from "@/components/loading-skeletons";
import type { PodcastChapter, PodcastLength, PodcastStyle, TranscriptSentence } from "@/lib/types";

type Props = {
  audioPath: string | null;
  audioReady?: boolean;
  processingStatus?: string[];
  transcriptPath: string | null;
  transcriptDownloadUrl: string | null;
  podcastScriptDownloadUrl: string | null;
  chapters: PodcastChapter[];
  transcriptSentences: TranscriptSentence[];
  podcastLength: PodcastLength;
  podcastStyle: PodcastStyle;
  onPodcastLengthChange: (value: PodcastLength) => void;
  onPodcastStyleChange: (value: PodcastStyle) => void;
};

export function PodcastAudioPlayer({
  audioPath,
  audioReady = false,
  processingStatus = [],
  transcriptPath,
  transcriptDownloadUrl,
  podcastScriptDownloadUrl,
  chapters,
  transcriptSentences,
  podcastLength,
  podcastStyle,
  onPodcastLengthChange,
  onPodcastStyleChange,
}: Props) {
  const src = audioPath ? backendAssetUrl(audioPath) : null;
  const transcriptPdfUrl = transcriptDownloadUrl ? backendAssetUrl(transcriptDownloadUrl) : null;
  const scriptPdfUrl = podcastScriptDownloadUrl ? backendAssetUrl(podcastScriptDownloadUrl) : null;
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [transcriptError, setTranscriptError] = useState<string | null>(null);
  const [isTranscriptOpen, setIsTranscriptOpen] = useState(false);
  const [duration, setDuration] = useState<number | null>(null);
  const [currentSentenceIndex, setCurrentSentenceIndex] = useState<number>(-1);
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState<number>(0);

  const hasTimestampedTranscript = transcriptSentences.length > 0;

  const formattedDuration = useMemo(() => {
    if (!duration || Number.isNaN(duration)) return "--:--";
    const mins = Math.floor(duration / 60);
    const secs = Math.floor(duration % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }, [duration]);

  useEffect(() => {
    let cancelled = false;

    if (!transcriptPath || !isTranscriptOpen || hasTimestampedTranscript) {
      setTranscript(null);
      setTranscriptError(null);
      setIsLoadingTranscript(false);
      return;
    }

    setIsLoadingTranscript(true);
    setTranscriptError(null);
    setTranscript(null);

    fetchTranscript(transcriptPath)
      .then((text) => {
        if (!cancelled) {
          setTranscript(text);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setTranscriptError(error instanceof Error ? error.message : "Could not load transcript.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingTranscript(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [transcriptPath, isTranscriptOpen, hasTimestampedTranscript]);

  useEffect(() => {
    if (!hasTimestampedTranscript) {
      setCurrentSentenceIndex(-1);
      return;
    }
    const index = transcriptSentences.findIndex((sentence, idx) => {
      const nextStart = transcriptSentences[idx + 1]?.start_seconds ?? Number.POSITIVE_INFINITY;
      return currentPlaybackTime >= sentence.start_seconds && currentPlaybackTime < nextStart;
    });
    setCurrentSentenceIndex(index);
  }, [currentPlaybackTime, hasTimestampedTranscript, transcriptSentences]);

  const jumpToChapter = (time: string) => {
    if (!audioRef.current) return;
    const [minsText, secsText] = time.split(":");
    const mins = Number(minsText || 0);
    const secs = Number(secsText || 0);
    if (Number.isNaN(mins) || Number.isNaN(secs)) return;
    audioRef.current.currentTime = mins * 60 + secs;
    void audioRef.current.play().catch(() => undefined);
  };

  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-white">Podcast Player</h2>
          <p className="mt-1 text-sm text-slate-300">Listen to the generated audio breakdown.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <Headphones className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium uppercase tracking-[0.16em] text-slate-300">Podcast Length</label>
          <select
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
            value={podcastLength}
            onChange={(event) => onPodcastLengthChange(event.target.value as PodcastLength)}
          >
            <option value="quick">Quick Brief (2 min)</option>
            <option value="standard">Standard (5 min)</option>
            <option value="deep">Deep Dive (10 min)</option>
          </select>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium uppercase tracking-[0.16em] text-slate-300">Podcast Style</label>
          <select
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-100 outline-none focus:border-sky-300/70"
            value={podcastStyle}
            onChange={(event) => onPodcastStyleChange(event.target.value as PodcastStyle)}
          >
            <option value="casual">Casual Podcast</option>
            <option value="lecture">Academic Lecture</option>
            <option value="debate">Debate Discussion</option>
            <option value="news">News Explanation</option>
          </select>
        </div>
      </div>

      {processingStatus.length > 0 && (
        <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900 p-5 pt-4">
          <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">Processing Status</h3>
          <ul className="space-y-2 text-sm text-slate-100">
            {processingStatus.map((item, index) => (
              <li key={`${item}-${index}`} className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 rounded-full bg-sky-300" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {src && audioReady ? (
        <div className="mt-4 space-y-4">
          <div className="flex items-center justify-between rounded-2xl border border-white/15 bg-slate-950/35 px-4 py-3">
            <div className="inline-flex items-center gap-2 text-slate-200">
              <PlayCircle className="h-5 w-5 text-sky-300" />
              <span className="text-sm font-medium">Ready to play</span>
            </div>
            <span className="text-xs text-slate-300">Length: {formattedDuration}</span>
          </div>
          <audio
            ref={audioRef}
            controls
            src={src}
            className="w-full rounded-xl"
            onLoadedMetadata={() => setDuration(audioRef.current?.duration ?? null)}
            onTimeUpdate={() => setCurrentPlaybackTime(audioRef.current?.currentTime ?? 0)}
          />

          {chapters.length > 0 && (
            <div className="rounded-2xl border border-white/15 bg-slate-950/30 p-4">
              <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-sky-200">Podcast Chapters</h3>
              <div className="mt-3 grid gap-2">
                {chapters.map((chapter) => (
                  <button
                    key={`${chapter.time}-${chapter.title}`}
                    type="button"
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-left text-sm text-slate-100 transition hover:border-sky-300/60 hover:bg-sky-500/10"
                    onClick={() => jumpToChapter(chapter.time)}
                  >
                    <span className="font-mono text-xs text-sky-200">{chapter.time}</span>
                    <span className="ml-3 flex-1">{chapter.title}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <PodcastPlayerSkeleton />
      )}

      {transcriptPath && (
        <div className="mt-5 rounded-2xl border border-white/15 bg-slate-950/30 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button className="btn-secondary" onClick={() => setIsTranscriptOpen((prev) => !prev)} type="button">
              <FileText className="h-4 w-4" />
              {isTranscriptOpen ? "Hide Transcript" : "View Transcript"}
            </button>
            <div className="flex flex-wrap items-center gap-2">
              {transcriptPdfUrl && (
                <a href={transcriptPdfUrl} download className="btn-secondary">
                  <Download className="h-4 w-4" />
                  Download Transcript (PDF)
                </a>
              )}
              {scriptPdfUrl && (
                <a href={scriptPdfUrl} download className="btn-secondary">
                  <Download className="h-4 w-4" />
                  Download Podcast Script (PDF)
                </a>
              )}
            </div>
          </div>
          {isTranscriptOpen && (
            <div className="mt-4 animate-fade-in">
              {isLoadingTranscript && (
                <p className="inline-flex items-center gap-2 text-sm text-slate-300">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading transcript...
                </p>
              )}
              {transcriptError && <p className="text-sm text-rose-300">{transcriptError}</p>}
              {hasTimestampedTranscript ? (
                <div className="custom-scrollbar max-h-72 space-y-2 overflow-auto pr-1">
                  {transcriptSentences.map((sentence, idx) => (
                    <p
                      key={`${sentence.start_seconds}-${idx}`}
                      className={`rounded-lg border border-white/10 px-3 py-2 text-sm leading-7 text-slate-200 transition ${
                        idx === currentSentenceIndex ? "bg-blue-500/20" : "bg-black/20"
                      }`}
                    >
                      <span className="mr-2 font-mono text-xs text-sky-200">{sentence.time}</span>
                      <span>{sentence.text}</span>
                    </p>
                  ))}
                </div>
              ) : transcript ? (
                <pre className="custom-scrollbar max-h-72 overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-black/20 p-4 text-sm leading-7 text-slate-200">
                  {transcript}
                </pre>
              ) : null}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
