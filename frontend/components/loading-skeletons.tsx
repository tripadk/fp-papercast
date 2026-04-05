export function SummarySectionSkeleton() {
  return (
    <div className="animate-pulse rounded-xl bg-slate-900 p-5 shadow-md">
      <div className="mb-4 h-6 w-48 rounded bg-slate-700/70" />
      <div className="space-y-3">
        <div className="h-4 w-full rounded bg-slate-700/60" />
        <div className="h-4 w-11/12 rounded bg-slate-700/60" />
        <div className="h-4 w-10/12 rounded bg-slate-700/60" />
        <div className="h-4 w-9/12 rounded bg-slate-700/60" />
      </div>
    </div>
  );
}

export function PodcastPlayerSkeleton() {
  return (
    <div className="mt-4 animate-pulse space-y-4">
      <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
        <div className="mb-3 h-4 w-32 rounded bg-slate-700/70" />
        <div className="h-10 w-full rounded-xl bg-slate-700/60" />
      </div>
      <div className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
        <div className="mb-3 h-4 w-36 rounded bg-slate-700/70" />
        <div className="h-2 w-full rounded-full bg-slate-700/60" />
      </div>
    </div>
  );
}

export function NotesSectionSkeleton() {
  return (
    <div className="grid animate-pulse gap-3 sm:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <article key={index} className="rounded-xl border border-white/15 bg-slate-950/35 p-4">
          <div className="h-3 w-24 rounded bg-slate-700/70" />
          <div className="mt-3 space-y-2">
            <div className="h-3 w-full rounded bg-slate-700/60" />
            <div className="h-3 w-10/12 rounded bg-slate-700/60" />
            <div className="h-3 w-8/12 rounded bg-slate-700/60" />
          </div>
        </article>
      ))}
    </div>
  );
}

