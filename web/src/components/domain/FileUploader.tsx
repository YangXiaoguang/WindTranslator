import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileUploaderProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  className?: string;
}

const ACCEPT = {
  "application/epub+zip": [".epub"],
  "application/pdf": [".pdf"],
};

export function FileUploader({ onFile, disabled, className }: FileUploaderProps) {
  const onDrop = useCallback(
    (files: File[]) => {
      if (files[0]) onFile(files[0]);
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 transition-colors cursor-pointer",
        isDragActive
          ? "border-accent bg-accent-muted"
          : "border-border hover:border-border-hover hover:bg-bg-hover",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
    >
      <input {...getInputProps()} />
      <Upload className="h-8 w-8 text-text-muted mb-3" />
      <p className="text-sm text-text-secondary">
        {isDragActive ? "松开上传文件" : "拖拽 EPUB / PDF 到这里，或点击选择"}
      </p>
      <p className="text-xs text-text-muted mt-1">最大 50MB</p>
    </div>
  );
}
