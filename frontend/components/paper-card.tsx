import { ExternalLink } from "lucide-react";

export type PaperShelfItem = {
  id: string;
  title: string;
  description: string;
  paperId?: string;
  href?: string;
};

type Props = {
  paper: PaperShelfItem;
  onView?: (paperId: string) => void;
};

export function PaperCard({ paper, onView }: Props) {
  const description = (paper.description || "").trim();
  const hasAction = Boolean((paper.paperId && onView) || paper.href);

  const handleOpen = () => {
    if (paper.href) {
      window.open(paper.href, "_blank", "noopener,noreferrer");
      return;
    }
    if (paper.paperId && onView) {
      onView(paper.paperId);
    }
  };

  return (
    <article
      className="w-full cursor-pointer border-b border-white/10 px-4 py-4 transition-colors duration-200 hover:bg-white/5"
      role="button"
      tabIndex={0}
      onClick={handleOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleOpen();
        }
      }}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-base font-medium text-white">{paper.title}</h3>
          {description && <p className="mt-1 line-clamp-1 text-sm text-gray-400">{description}</p>}
        </div>
        <button
          type="button"
          aria-label={`Open ${paper.title}`}
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-white/20 px-3 py-1.5 text-xs font-semibold text-slate-100 transition-colors duration-200 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={(event) => {
            event.stopPropagation();
            handleOpen();
          }}
          disabled={!hasAction}
        >
          Open
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      </div>
    </article>
  );
}
