import { create } from "zustand";
import type { ProgressData } from "@/types";

interface ProjectStore {
  /* Live progress from WebSocket */
  progress: Record<string, ProgressData>;
  setProgress: (projectId: string, data: ProgressData) => void;
  clearProgress: (projectId: string) => void;

  /* Translation config (persisted in session) */
  lastProvider: string;
  lastModel: string;
  setLastConfig: (provider: string, model: string) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  progress: {},
  setProgress: (projectId, data) =>
    set((s) => ({ progress: { ...s.progress, [projectId]: data } })),
  clearProgress: (projectId) =>
    set((s) => {
      const next = { ...s.progress };
      delete next[projectId];
      return { progress: next };
    }),

  lastProvider: "anthropic",
  lastModel: "claude-sonnet-4-6",
  setLastConfig: (provider, model) =>
    set({ lastProvider: provider, lastModel: model }),
}));
