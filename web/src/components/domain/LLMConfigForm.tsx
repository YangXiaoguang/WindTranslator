import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Eye, EyeOff, Plug } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { getProviders, testApiKey } from "@/api/client";
import { useProjectStore } from "@/stores/projectStore";
import type { TranslateRequest } from "@/types";

interface LLMConfigFormProps {
  onSubmit: (config: TranslateRequest) => void;
  loading?: boolean;
  chapterRange?: string;
}

export function LLMConfigForm({ onSubmit, loading, chapterRange }: LLMConfigFormProps) {
  const { lastProvider, lastModel, setLastConfig } = useProjectStore();
  const [provider, setProvider] = useState(lastProvider);
  const [model, setModel] = useState(lastModel);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [showKey, setShowKey] = useState(false);

  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
  });

  const testMutation = useMutation({
    mutationFn: testApiKey,
  });

  const providerOptions = providers
    ? Object.entries(providers).map(([k, v]) => ({ value: k, label: v.name }))
    : [{ value: "anthropic", label: "Anthropic" }];

  const currentProvider = providers?.[provider];
  const modelSuggestions = currentProvider?.models ?? [];

  useEffect(() => {
    if (modelSuggestions.length > 0 && !modelSuggestions.includes(model)) {
      setModel(modelSuggestions[0]);
    }
  }, [provider, modelSuggestions, model]);

  const handleSubmit = () => {
    setLastConfig(provider, model);
    onSubmit({
      provider,
      model,
      api_key: apiKey,
      base_url: baseUrl || undefined,
      chapter_range: chapterRange || undefined,
    });
  };

  const canSubmit = provider && model && apiKey.trim();

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-text-primary">LLM 配置</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted mb-1 block">Provider</label>
          <Select
            options={providerOptions}
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="w-full"
          />
        </div>
        <div>
          <label className="text-xs text-text-muted mb-1 block">Model</label>
          <Input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="模型名称"
            list="model-suggestions"
          />
          {modelSuggestions.length > 0 && (
            <datalist id="model-suggestions">
              {modelSuggestions.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          )}
        </div>
      </div>

      <div>
        <label className="text-xs text-text-muted mb-1 block">API Key</label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full pr-8"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
            >
              {showKey ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
          <Button
            variant="secondary"
            size="md"
            onClick={() =>
              testMutation.mutate({ provider, model, api_key: apiKey, base_url: baseUrl || undefined })
            }
            loading={testMutation.isPending}
            disabled={!apiKey.trim()}
          >
            <Plug className="h-3.5 w-3.5" />
            测试
          </Button>
        </div>
        {testMutation.data && (
          <p
            className={`text-xs mt-1 ${
              testMutation.data.success ? "text-accent" : "text-danger"
            }`}
          >
            {testMutation.data.message}
          </p>
        )}
      </div>

      {currentProvider?.requires_base_url && (
        <div>
          <label className="text-xs text-text-muted mb-1 block">Base URL</label>
          <Input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.example.com/v1"
          />
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={!canSubmit}
        loading={loading}
        className="w-full"
        size="lg"
      >
        开始翻译
      </Button>
    </div>
  );
}
