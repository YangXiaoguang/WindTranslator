import { Link } from "react-router-dom";
import { FileText, Trash2, Clock } from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Button } from "@/components/ui/Button";
import { formatBytes, timeAgo } from "@/lib/utils";
import { useProjectStore } from "@/stores/projectStore";
import type { Project } from "@/types";

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const progress = useProjectStore((s) => s.progress[project.id]);
  const pct = progress?.percent ?? (project.status === "completed" ? 100 : 0);

  return (
    <Link
      to={`/projects/${project.id}`}
      className="block rounded-lg border border-border bg-bg-elevated p-4 transition-colors hover:border-border-hover hover:bg-bg-hover group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <FileText className="h-4 w-4 text-text-muted flex-shrink-0" />
          <h3 className="text-sm font-medium truncate">
            {project.title || project.filename}
          </h3>
        </div>
        <StatusBadge status={project.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-text-muted">
        <span>{project.total_chapters} 章</span>
        <span>{project.total_blocks} 段</span>
        <span>{formatBytes(project.file_size)}</span>
        <span className="ml-auto flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {timeAgo(project.created_at)}
        </span>
      </div>

      {(project.status === "translating" || pct > 0) && (
        <div className="mt-3">
          <ProgressBar value={pct} />
          {pct > 0 && pct < 100 && (
            <span className="text-xs text-text-muted mt-1 block">
              {pct.toFixed(1)}%
            </span>
          )}
        </div>
      )}

      <div className="mt-3 flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(project.id);
          }}
          className="text-text-muted hover:text-danger"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </Link>
  );
}
