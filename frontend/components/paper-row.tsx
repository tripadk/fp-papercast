import { PaperCard, type PaperShelfItem } from "@/components/paper-card";

type Props = {
  title: string;
  papers: PaperShelfItem[];
  onView?: (paperId: string) => void;
};

export function PaperRow({ title, papers, onView }: Props) {
  const uniquePapers: PaperShelfItem[] = [];
  const seenTitles = new Set<string>();

  for (const paper of papers) {
    const normalizedTitle = paper.title.trim().toLowerCase();
    if (!normalizedTitle || seenTitles.has(normalizedTitle)) {
      continue;
    }
    seenTitles.add(normalizedTitle);
    uniquePapers.push(paper);
  }

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-900/60">
        {uniquePapers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} onView={onView} />
        ))}
      </div>
    </section>
  );
}
