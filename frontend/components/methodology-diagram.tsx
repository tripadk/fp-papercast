"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { GitFork, Loader2 } from "lucide-react";
import mermaid from "mermaid";

type Props = {
  steps: string[] | null;
  mermaidCode: string | null;
};

export function MethodologyDiagram({ steps, mermaidCode }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);

  const hasData = useMemo(() => Boolean(mermaidCode && mermaidCode.trim()), [mermaidCode]);

  useEffect(() => {
    if (!hasData || !mermaidCode) {
      setSvg("");
      setError(null);
      setRendering(false);
      return;
    }

    let cancelled = false;

    const render = async () => {
      setRendering(true);
      setError(null);
      try {
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          theme: "dark",
          flowchart: { useMaxWidth: true, htmlLabels: true, curve: "basis", nodeSpacing: 60, rankSpacing: 70 },
          themeVariables: {
            primaryColor: "#0f172a",
            primaryBorderColor: "#38bdf8",
            primaryTextColor: "#e2e8f0",
            lineColor: "#38bdf8",
            fontSize: "14px",
          },
        });
        const id = `methodology-diagram-${Date.now()}`;
        const { svg: renderedSvg } = await mermaid.render(id, mermaidCode);
        if (!cancelled) setSvg(renderedSvg);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to render diagram.");
        }
      } finally {
        if (!cancelled) setRendering(false);
      }
    };

    void render();
    return () => {
      cancelled = true;
    };
  }, [hasData, mermaidCode]);

  return (
    <section className="glass-card p-6 sm:p-8">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">Methodology Diagram</h2>
          <p className="mt-1 text-sm text-slate-300">Visual research workflow extracted from the uploaded paper.</p>
        </div>
        <div className="rounded-2xl border border-white/20 bg-white/10 p-3 text-sky-200">
          <GitFork className="h-5 w-5" />
        </div>
      </div>

      {!hasData && <p className="text-sm text-slate-300">Upload a paper to generate a methodology workflow diagram.</p>}

      {hasData && (
        <div className="space-y-4">
          {steps && steps.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {steps.map((step, idx) => (
                <span
                  key={`${step}-${idx}`}
                  className="rounded-full border border-sky-300/30 bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-100"
                >
                  {step}
                </span>
              ))}
            </div>
          )}

          <div className="rounded-2xl border border-white/15 bg-slate-950/35 p-4">
            {rendering && (
              <p className="inline-flex items-center gap-2 text-sm text-slate-300">
                <Loader2 className="h-4 w-4 animate-spin" />
                Rendering methodology diagram...
              </p>
            )}
            {error && <p className="text-sm text-rose-300">{error}</p>}
            {!rendering && !error && svg && (
              <div
                ref={containerRef}
                className="custom-scrollbar overflow-x-auto py-2 [&>svg]:mx-auto [&>svg]:min-w-[640px]"
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
