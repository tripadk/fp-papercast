"use client";

import Link from "next/link";
import { signIn, signOut, useSession } from "next-auth/react";
import { ArrowRight, BrainCircuit, FileAudio, MessageSquareText, Sparkles } from "lucide-react";

export default function HomePage() {
  const { data: session } = useSession();

  return (
    <main className="app-shell mx-auto max-w-6xl py-24">
      <section className="glass-card animate-fade-in overflow-hidden p-8 sm:p-12">
        <span className="section-label">
          <Sparkles className="h-3.5 w-3.5" />
          PaperCast
        </span>
        <h1 className="font-hero mt-5 max-w-[800px] text-5xl font-semibold leading-tight tracking-tight text-white sm:mt-6 md:text-6xl">
          Research paper intelligence designed for{" "}
          <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">students</span>,{" "}
          <span className="bg-gradient-to-r from-sky-300 to-indigo-300 bg-clip-text text-transparent">creators</span>,
          and{" "}
          <span className="bg-gradient-to-r from-cyan-300 to-blue-500 bg-clip-text text-transparent">
            curious minds
          </span>
          .
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-gray-300 sm:mt-7">
          Upload any paper and convert complex content into clear summaries, podcast-ready audio, and contextual Q&A.
          Built for fast understanding without losing academic rigor.
        </p>

        <div className="mt-9 flex flex-wrap gap-3">
          {session ? (
            <>
              <Link className="btn-primary" href="/dashboard">
                Open Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
              <button className="btn-secondary" onClick={() => signOut()}>
                Sign out
              </button>
            </>
          ) : (
            <button className="btn-primary" onClick={() => signIn("google", { callbackUrl: "/dashboard" })}>
              Sign in with Google
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </section>

      <section className="mt-6 grid gap-4 sm:grid-cols-3">
        <article className="glass-card p-5">
          <BrainCircuit className="h-5 w-5 text-sky-300" />
          <h2 className="mt-3 text-lg font-semibold text-white">Smart Summary</h2>
          <p className="mt-2 text-sm text-slate-300">Understand methods, findings, and relevance in minutes.</p>
        </article>
        <article className="glass-card p-5">
          <FileAudio className="h-5 w-5 text-sky-300" />
          <h2 className="mt-3 text-lg font-semibold text-white">Podcast Output</h2>
          <p className="mt-2 text-sm text-slate-300">Generate a transcript-driven audio briefing from each upload.</p>
        </article>
        <article className="glass-card p-5">
          <MessageSquareText className="h-5 w-5 text-sky-300" />
          <h2 className="mt-3 text-lg font-semibold text-white">Context Chat</h2>
          <p className="mt-2 text-sm text-slate-300">Ask focused follow-ups and get paper-grounded answers.</p>
        </article>
      </section>
    </main>
  );
}
