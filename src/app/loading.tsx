import { InlineSpinner } from "@/components/common/states";

export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center gap-2 text-caption text-on-surface-variant">
      <InlineSpinner />
      Memuat…
    </div>
  );
}
