import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ProjectCard } from "@/components/domain/ProjectCard";
import { FileUploader } from "@/components/domain/FileUploader";
import { listProjects, uploadBook, deleteProject } from "@/api/client";

export default function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showUpload, setShowUpload] = useState(false);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadBook,
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate(`/projects/${project.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const filtered = projects.filter(
    (p) =>
      !search ||
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.filename.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-text-primary">项目</h1>
        <Button size="md" onClick={() => setShowUpload(!showUpload)}>
          <Plus className="h-4 w-4" />
          上传书籍
        </Button>
      </div>

      {/* Upload area */}
      {showUpload && (
        <div className="mb-6">
          <FileUploader
            onFile={(file) => uploadMutation.mutate(file)}
            disabled={uploadMutation.isPending}
          />
          {uploadMutation.isError && (
            <p className="text-xs text-danger mt-2">
              上传失败：{(uploadMutation.error as Error).message}
            </p>
          )}
        </div>
      )}

      {/* Search */}
      {projects.length > 0 && (
        <div className="relative mb-4">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索项目…"
            className="pl-8"
          />
        </div>
      )}

      {/* Project list */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-28 rounded-lg" />
          ))}
        </div>
      ) : filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      ) : projects.length > 0 ? (
        <p className="text-sm text-text-muted text-center py-12">
          没有匹配的项目
        </p>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <BookOpen className="h-10 w-10 mb-3" />
          <p className="text-sm">还没有项目，上传一本书开始吧</p>
        </div>
      )}
    </div>
  );
}
