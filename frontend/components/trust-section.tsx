type TrustSectionProps = {
  className?: string;
};

const BADGES = ["Fast AI Processing", "Accurate Summaries", "Interactive Learning"];

export function TrustSection({ className = "" }: TrustSectionProps) {
  return (
    <section className={className}>
      <div className="rounded-xl border border-white/10 bg-white/5 p-6 shadow-[0_12px_40px_-24px_rgba(15,23,42,0.9)]">
        <h2 className="text-2xl font-semibold text-white">Built for Students & Researchers</h2>

        <div className="mt-4 flex flex-wrap gap-3">
          {BADGES.map((badge) => (
            <span
              key={badge}
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200"
            >
              {badge}
            </span>
          ))}
        </div>

        <div className="mt-5 rounded-xl border border-white/10 bg-white/5 p-6 shadow-[0_10px_30px_-20px_rgba(15,23,42,0.85)]">
          <p className="text-sm text-slate-200">"This saved me hours of reading" — Student</p>
        </div>
      </div>
    </section>
  );
}

