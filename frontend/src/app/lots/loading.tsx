export default function LotsLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <div className="mb-6">
          <div className="skeleton h-8 w-40 mb-2" />
          <div className="skeleton h-4 w-56" />
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
              <div className="h-1 skeleton" />
              <div className="p-4 border-b border-[var(--border-subtle)]">
                <div className="skeleton h-5 w-36 mb-2" />
                <div className="skeleton h-3 w-28" />
              </div>
              <div className="grid grid-cols-3 divide-x divide-[var(--border-subtle)]">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="px-4 py-3 flex flex-col items-center">
                    <div className="skeleton h-7 w-8 mb-1" />
                    <div className="skeleton h-3 w-14" />
                  </div>
                ))}
              </div>
              <div className="h-2 skeleton" />
              <div className="px-4 py-2.5 bg-[var(--bg-tertiary)] flex items-center justify-between">
                <div className="skeleton h-3 w-16" />
                <div className="skeleton h-3 w-20" />
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
