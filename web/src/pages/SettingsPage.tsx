import { useQuery } from "@tanstack/react-query";
import { getProviders } from "@/api/client";

export default function SettingsPage() {
  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
  });

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold text-text-primary mb-6">设置</h1>

      <section className="rounded-lg border border-border bg-bg-elevated p-4">
        <h2 className="text-sm font-medium text-text-primary mb-3">
          支持的 LLM 供应商
        </h2>
        {providers ? (
          <div className="space-y-2">
            {Object.entries(providers).map(([key, info]) => (
              <div
                key={key}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2"
              >
                <div>
                  <span className="text-sm text-text-primary">{info.name}</span>
                  <span className="text-xs text-text-muted ml-2">
                    {info.models.length} 模型
                  </span>
                </div>
                <span className="text-xs text-text-muted font-mono">{key}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="skeleton h-20" />
        )}
      </section>

      <section className="mt-6 rounded-lg border border-border bg-bg-elevated p-4">
        <h2 className="text-sm font-medium text-text-primary mb-2">关于</h2>
        <p className="text-xs text-text-muted leading-relaxed">
          WindTranslator — EPUB / PDF 英译中翻译工具。
          <br />
          基于大语言模型进行高质量书籍翻译，保留原始格式并输出 PDF。
        </p>
        <p className="text-xs text-text-muted mt-2">版本 0.3.0</p>
      </section>
    </div>
  );
}
