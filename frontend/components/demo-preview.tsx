import { Play } from "lucide-react";

type DemoPreviewProps = {
  className?: string;
};

const WAVE_BARS = [14, 24, 18, 30, 20, 28, 16, 26, 18, 22];

export function DemoPreview({ className = "" }: DemoPreviewProps) {
  return (
    <section className={className}>
      <div className="mb-6">
        <h2 className="text-3xl font-semibold text-white">See PaperCast in Action</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-300">
          Upload a paper, preview extracted content, and listen to an AI-generated podcast summary in seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <article className="rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm font-medium text-slate-200">Paper Preview</p>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
              PDF
            </span>
          </div>
          <div className="rounded-lg border border-white/10 bg-slate-950/60 p-4">
            <div className="mb-3 h-4 w-2/3 rounded bg-white/10" />
            <div className="space-y-2">
              <div className="h-2.5 w-full rounded bg-white/10" />
              <div className="h-2.5 w-11/12 rounded bg-white/10" />
              <div className="h-2.5 w-10/12 rounded bg-white/10" />
              <div className="h-2.5 w-full rounded bg-white/10" />
              <div className="h-2.5 w-9/12 rounded bg-white/10" />
              <div className="h-2.5 w-8/12 rounded bg-white/10" />
            </div>
          </div>
        </article>

        <article className="rounded-xl border border-white/10 bg-white/5 p-6">
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm font-medium text-slate-200">Podcast Player</p>
            <span className="text-xs text-slate-300">03:42</span>
          </div>

          <div className="rounded-lg border border-white/10 bg-slate-950/60 p-4">
            <button
              type="button"
              className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-full bg-blue-600 text-white transition-all duration-200 hover:scale-105 hover:bg-blue-700"
              aria-label="Play demo"
            >
              <Play className="ml-0.5 h-5 w-5" />
            </button>

            <div className="flex h-10 items-end gap-1.5">
              {WAVE_BARS.map((height, index) => (
                <span
                  key={`${height}-${index}`}
                  className="w-1.5 rounded-full bg-sky-300/90 animate-pulse"
                  style={{
                    height: `${height}px`,
                    animationDelay: `${index * 120}ms`,
                    animationDuration: "1.2s",
                  }}
                />
              ))}
            </div>

            <div className="mt-4 h-1.5 w-full rounded-full bg-white/10">
              <div className="h-full w-2/5 rounded-full bg-blue-500" />
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}

