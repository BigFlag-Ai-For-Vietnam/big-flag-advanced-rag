import { useRef, useState } from "react";
import { UploadCloud, FileText } from "lucide-react";
import { cn } from "../lib/cn";

interface Props {
  file: File | null;
  onFile: (f: File | null) => void;
  disabled?: boolean;
}

export default function Dropzone({ file, onFile, disabled }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const pick = (f?: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) return;
    onFile(f);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) pick(e.dataTransfer.files?.[0]);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) inputRef.current?.click();
      }}
      className={cn(
        "group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-all",
        dragging ? "border-accent bg-accent-soft" : "border-border hover:border-accent/60 hover:bg-surface-2",
        disabled && "pointer-events-none opacity-60"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => pick(e.target.files?.[0])}
      />

      {file ? (
        <>
          <span className="grid size-14 place-items-center rounded-xl bg-accent-soft text-accent">
            <FileText className="size-7" />
          </span>
          <div>
            <p className="font-semibold text-fg">{file.name}</p>
            <p className="mt-0.5 text-sm text-muted">
              {(file.size / 1024 / 1024).toFixed(2)} MB · nhấn để đổi file
            </p>
          </div>
        </>
      ) : (
        <>
          <span
            className={cn(
              "grid size-14 place-items-center rounded-xl bg-surface-2 text-muted transition-colors",
              "group-hover:bg-accent-soft group-hover:text-accent"
            )}
          >
            <UploadCloud className="size-7" />
          </span>
          <div>
            <p className="font-semibold text-fg">Kéo &amp; thả file PDF vào đây</p>
            <p className="mt-0.5 text-sm text-muted">hoặc nhấn để chọn từ máy · chỉ nhận .pdf</p>
          </div>
        </>
      )}
    </div>
  );
}
