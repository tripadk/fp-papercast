import { Bot, FileUp, Podcast } from "lucide-react";

type HowItWorksProps = {
  className?: string;
};

const STEPS = [
  {
    icon: FileUp,
    title: "Upload Paper",
    description: "Upload your research PDF and choose the podcast style and depth you want.",
  },
  {
    icon: Bot,
    title: "AI Processes Content",
    description: "PaperCast extracts key ideas, methods, and findings using AI-driven analysis.",
  },
  {
    icon: Podcast,
    title: "Get Summary, Podcast, Chat",
    description: "Receive a clear summary, generated podcast audio, and contextual Q&A chat instantly.",
  },
];

export function HowItWorks({ className = "" }: HowItWorksProps) {
  return (
    <section className={className}>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-white">How It Works</h2>
      </div>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, description }) => (
          <article
            key={title}
            className="rounded-xl border border-white/10 bg-white/5 p-6 text-center transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_18px_40px_-20px_rgba(56,189,248,0.55)]"
          >
            <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full border border-white/15 bg-white/5 text-sky-200">
              <Icon className="h-5 w-5" />
            </div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

