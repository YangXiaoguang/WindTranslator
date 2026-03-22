import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  StopCircle,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ChapterList } from "@/components/domain/ChapterList";
import { TranslationPreview } from "@/components/domain/TranslationPreview";
import { LLMConfigForm } from "@/components/domain/LLMConfigForm";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useProjectStore } from "@/stores/projectStore";
import {
  getProject,
  startTranslation,
  cancelTranslation,
  deleteProject,
  getDownloadUrl,
} from "@/api/client";
import type { WsEvent, TranslateRequest, ProgressData } from "@/types";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id!;

  const [activeChapter, setActiveChapter] = useState<number | undefined>();
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(
    new Set()
  );
  const [showConfig, setShowConfig] = useState(false);

  const { setProgress, clearProgress, progress } = useProjectStore();
  const liveProgress = progress[projectId];

  const {
    data: project,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const isTranslating = project?.status === "translating";

  const handleWsMessage = useCallback(
    (event: WsEvent) => {
      if (event.event === "progress" || event.event === "started") {
        setProgress(projectId, event.data as unknown as ProgressData);
      }
      if (event.event === "completed" || event.event === "error") {
        clearProgress(projectId);
        refetch();
      }
    },
    [projectId, setProgress, clearProgress, refetch]
  );

  useWebSocket({
    projectId,
    enabled: isTranslating,
    onMessage: handleWsMessage,
  });

  const translateMutation = useMutation({
    mutationFn: (config: TranslateRequest) =>
      startTranslation(projectId, config),
    onSuccess: () => {
      setShowConfig(false);
      refetch();
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelTranslation(projectId),
    onSuccess: () => {
      clearProgress(projectId);
      refetch();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => navigate("/"),
  });

  const toggleChapter = (index: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton h-64" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-6 text-center text-text-muted">项目不存在</div>
    );
  }

  const pct = liveProgress?.percent ?? (project.status === "completed" ? 100 : 0);

  const activeBlocks =
    activeChapter !== undefined
      ? (project.chapters.find((c) => c.index === activeChapter) as any)
          ?.blocks ?? []
      : [];

  const canTranslate =
    project.status === "parsed" ||
    project.status === "failed" ||
    project.status === "cancelled";

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Top bar */}
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-text-primary truncate">
            {project.title || project.filename}
          </h1>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-text-muted">
            <span>{project.total_chapters} 章</span>
            <span>{project.total_blocks} 段</span>
            <StatusBadge status={project.status} />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isTranslating && (
            <Button
              variant="danger"
              size="md"
              onClick={() => cancelMutation.mutate()}
              loading={cancelMutation.isPending}
            >
              <StopCircle className="h-4 w-4" />
              取消
            </Button>
          )}
          {project.status === "completed" && (
            <a href={getDownloadUrl(projectId)} download>
              <Button variant="secondary" size="md">
                <Download className="h-4 w-4" />
                下载 PDF
              </Button>
            </a>
          )}
          {canTranslate && (
            <Button size="md" onClick={() => setShowConfig(!showConfig)}>
              开始翻译
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              if (confirm("确定删除此项目？")) deleteMutation.mutate();
            }}
            className="text-text-muted hover:text-danger"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Progress bar */}
      {(isTranslating || pct > 0) && pct < 100 && (
        <div className="mb-4">
          <ProgressBar value={pct} size="md" />
          <div className="flex justify-between text-xs text-text-muted mt-1">
            <span>{liveProgress?.current_chapter ?? ""}</span>
            <span>{pct.toFixed(1)}%</span>
          </div>
        </div>
      )}

      {/* LLM config panel */}
      {showConfig && (
        <div className="mb-6 rounded-lg border border-border bg-bg-elevated p-4">
          <LLMConfigForm
            onSubmit={(config) => {
              const chapterRange =
                selectedChapters.size > 0
                  ? Array.from(selectedChapters).sort((a, b) => a - b).join(",")
                  : undefined;
              translateMutation.mutate({ ...config, chapter_range: chapterRange });
            }}
            loading={translateMutation.isPending}
          />
          {translateMutation.isError && (
            <p className="text-xs text-danger mt-2">
              启动失败：{(translateMutation.error as Error).message}
            </p>
          )}
        </div>
      )}

      {/* Main content: chapter list + preview */}
      <div className="grid grid-cols-[240px_1fr] gap-4">
        {/* Chapter sidebar */}
        <div className="rounded-lg border border-border bg-bg-elevated p-2 max-h-[calc(100vh-220px)] overflow-y-auto">
          <div className="flex items-center justify-between px-2 py-1.5 mb-1">
            <span className="text-xs font-medium text-text-muted">章节</span>
            {canTranslate && (
              <button
                className="text-xs text-accent hover:underline"
                onClick={() => {
                  if (selectedChapters.size === project.chapters.length) {
                    setSelectedChapters(new Set());
                  } else {
                    setSelectedChapters(
                      new Set(project.chapters.map((c) => c.index))
                    );
                  }
                }}
              >
                {selectedChapters.size === project.chapters.length
                  ? "取消全选"
                  : "全选"}
              </button>
            )}
          </div>
          <ChapterList
            chapters={project.chapters}
            selectedIndices={canTranslate ? selectedChapters : undefined}
            onToggle={canTranslate ? toggleChapter : undefined}
            activeIndex={activeChapter}
            onSelect={setActiveChapter}
            selectable={canTranslate}
          />
        </div>

        {/* Preview */}
        <div className="rounded-lg border border-border bg-bg-elevated p-4 max-h-[calc(100vh-220px)] overflow-y-auto">
          <TranslationPreview blocks={activeBlocks} />
        </div>
      </div>
    </div>
  );
}
