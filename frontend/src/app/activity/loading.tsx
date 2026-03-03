export default function ActivityLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 mb-2" />
          <div className="skeleton h-4 w-64" />
        </div>

        <div className="hidden border border-[var(--border-default)] bg-[var(--bg-secondary)] md:block">
          <div className="border-b border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3">
            <div className="skeleton h-3 w-full max-w-lg" />
          </div>
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div
              key={i}
              className="flex items-center gap-4 border-b border-[var(--border-subtle)] px-4 py-3"
            >
              <div className="skeleton h-4 w-16" />
              <div className="skeleton h-6 w-6" />
              <div className="skeleton h-4 w-10" />
              <div className="skeleton h-4 w-24 flex-1" />
              <div className="skeleton h-4 w-20" />
            </div>
          ))}
        </div>

        <div className="space-y-2 md:hidden">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="skeleton h-7 w-7" />
                  <div className="skeleton h-4 w-20" />
                </div>
                <div className="skeleton h-3 w-14" />
              </div>
              <div className="flex items-center justify-between">
                <div className="skeleton h-3 w-24" />
                <div className="skeleton h-3 w-16" />
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
