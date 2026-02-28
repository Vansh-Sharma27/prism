interface PageHeaderProps {
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, subtitle, children }: PageHeaderProps) {
  return (
    <div className="mb-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-6 w-1.5 bg-[var(--accent)]" />
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold uppercase tracking-wider text-[var(--text-primary)] font-display">
              {title}
            </h1>
          </div>
          <p className="ml-[18px] text-sm text-[var(--text-secondary)]">
            {subtitle}
          </p>
        </div>
        {children}
      </div>
      <div className="divider-accent mt-4" />
    </div>
  );
}

interface SectionHeaderProps {
  title: string;
  count?: number;
  subtitle?: string;
}

export function SectionHeader({ title, count, subtitle }: SectionHeaderProps) {
  return (
    <div className="mb-4 flex items-center justify-between border-b border-[var(--border-default)] pb-3">
      <div className="flex items-center gap-3">
        <div className="h-4 w-1 bg-[var(--accent)]" />
        <h2 className="text-lg font-bold uppercase tracking-wider text-[var(--text-primary)] font-display">
          {title}
        </h2>
        {subtitle && (
          <span className="text-sm text-[var(--text-muted)]">/ {subtitle}</span>
        )}
      </div>
      {count !== undefined && (
        <span className="font-mono text-sm text-[var(--accent)]">
          [{count.toString().padStart(2, "0")}]
        </span>
      )}
    </div>
  );
}

interface StatCellProps {
  label: string;
  value: number | string;
  color: string;
  size?: "sm" | "md" | "lg";
}

export function StatCell({ label, value, color, size = "md" }: StatCellProps) {
  const sizeClasses = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-3xl",
  };

  return (
    <div className="px-4 py-3 text-center">
      <div
        className={`font-mono ${sizeClasses[size]} font-bold tabular-nums`}
        style={{ color }}
      >
        {typeof value === "number" ? value.toString().padStart(2, "0") : value}
      </div>
      <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] font-display">
        {label}
      </div>
    </div>
  );
}
