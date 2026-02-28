import { AlertCircle, Database, Search, Plus } from "lucide-react";

type EmptyStateVariant = "no-data" | "no-results" | "error" | "offline";

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const icons = {
  "no-data": Database,
  "no-results": Search,
  "error": AlertCircle,
  "offline": AlertCircle,
};

const colors = {
  "no-data": "text-[var(--text-muted)]",
  "no-results": "text-[var(--accent)]",
  "error": "text-[var(--occupied)]",
  "offline": "text-[var(--warning)]",
};

export function EmptyState({
  variant = "no-data",
  title,
  description,
  action,
}: EmptyStateProps) {
  const Icon = icons[variant];
  const iconColor = colors[variant];

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center border border-[var(--border-default)] bg-[var(--bg-tertiary)] mb-4">
        <Icon size={28} className={iconColor} />
      </div>

      <h3 className="text-lg font-bold uppercase tracking-wider text-[var(--text-primary)] font-display mb-2">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-[var(--text-secondary)] max-w-sm mb-6">
          {description}
        </p>
      )}

      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] text-[var(--bg-primary)] font-semibold uppercase tracking-wider text-sm font-display transition-all hover:bg-[var(--accent-dim)] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-primary)]"
        >
          <Plus size={16} aria-hidden="true" />
          {action.label}
        </button>
      )}
    </div>
  );
}
