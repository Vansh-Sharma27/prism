export default function ActivityLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 mb-2" />
          <div className="skeleton h-4 w-64" />
        </div>

        <div className="border border-[var(--border-default)] bg-[var(--bg-secondary)]">
          <div className="px-4 py-3 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)]">
            <div className="skeleton h-3 w-full max-w-md" />
          </div>
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div
              key={i}
              className="px-4 py-3 border-b border-[var(--border-subtle)] flex items-center gap-4"
            >
              <div className="skeleton h-4 w-16" />
              <div className="skeleton h-6 w-6" />
              <div className="skeleton h-4 w-10" />
              <div className="skeleton h-4 w-24 flex-1" />
              <div className="skeleton h-4 w-20" />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
