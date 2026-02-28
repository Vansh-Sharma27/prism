interface SkeletonProps {
  className?: string;
  variant?: "text" | "card" | "circular";
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  className = "",
  variant = "text",
  width,
  height,
}: SkeletonProps) {
  const baseClasses = "skeleton animate-pulse";

  const variantClasses = {
    text: "h-4 rounded",
    card: "h-32 rounded-sm",
    circular: "rounded-full",
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === "number" ? `${width}px` : width;
  if (height) style.height = typeof height === "number" ? `${height}px` : height;

  return (
    <div
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

export function SlotCardSkeleton() {
  return (
    <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
      <div className="h-1 skeleton" />
      <div className="p-3">
        <div className="flex items-start justify-between">
          <div>
            <Skeleton width={60} height={10} className="mb-2" />
            <Skeleton width={40} height={28} />
          </div>
          <Skeleton variant="card" width={32} height={32} />
        </div>
        <Skeleton width={50} height={20} className="mt-3" />
      </div>
      <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-3 py-2 bg-[var(--bg-tertiary)]">
        <Skeleton width={70} height={12} />
        <Skeleton width={60} height={12} />
      </div>
    </div>
  );
}

export function LotCardSkeleton() {
  return (
    <div className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
      <div className="h-1 skeleton" />
      <div className="flex items-start justify-between p-4 border-b border-[var(--border-subtle)]">
        <div>
          <Skeleton width={140} height={20} className="mb-2" />
          <Skeleton width={100} height={14} />
        </div>
        <Skeleton width={24} height={24} />
      </div>
      <div className="grid grid-cols-3 divide-x divide-[var(--border-subtle)]">
        {[1, 2, 3].map((i) => (
          <div key={i} className="px-4 py-3 text-center">
            <Skeleton width={40} height={28} className="mx-auto mb-1" />
            <Skeleton width={50} height={12} className="mx-auto" />
          </div>
        ))}
      </div>
      <div className="h-2 skeleton" />
      <div className="flex items-center justify-between px-4 py-2.5 bg-[var(--bg-tertiary)]">
        <Skeleton width={60} height={14} />
        <Skeleton width={70} height={12} />
      </div>
    </div>
  );
}
