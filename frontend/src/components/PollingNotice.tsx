interface PollingNoticeAction {
  label: string;
  onClick: () => void;
}

interface PollingNoticeProps {
  message: string;
  actions?: PollingNoticeAction[];
}

export function PollingNotice({ message, actions = [] }: PollingNoticeProps) {
  return (
    <div className="mb-6 border border-[var(--warning)]/40 bg-[var(--warning)]/10 px-4 py-3 text-sm text-[var(--warning)]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {actions.map((action) => (
              <button
                key={action.label}
                type="button"
                onClick={action.onClick}
                className="min-h-11 border border-[var(--warning)]/50 px-3 py-2 text-xs font-display font-semibold uppercase tracking-wider transition-colors hover:bg-[var(--warning)]/15"
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
