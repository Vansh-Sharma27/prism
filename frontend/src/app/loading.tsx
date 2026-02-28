export default function DashboardLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Navbar placeholder */}
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        {/* Header skeleton */}
        <div className="mb-6">
          <div className="skeleton h-8 w-64 mb-2" />
          <div className="skeleton h-4 w-48" />
        </div>

        {/* Stats skeleton */}
        <div className="mb-8 border border-[var(--border-default)] bg-[var(--bg-secondary)]">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border-default)] bg-[var(--bg-tertiary)]">
            <div className="skeleton h-3 w-24" />
            <div className="skeleton h-3 w-12" />
          </div>
          <div className="grid grid-cols-5 divide-x divide-[var(--border-default)]">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="px-4 py-4 flex flex-col items-center">
                <div className="skeleton h-9 w-12 mb-1" />
                <div className="skeleton h-3 w-16" />
              </div>
            ))}
          </div>
          <div className="h-2 skeleton" />
        </div>

        {/* Section header skeleton */}
        <div className="mb-4 flex items-center justify-between border-b border-[var(--border-default)] pb-3">
          <div className="flex items-center gap-3">
            <div className="h-4 w-1 bg-[var(--accent)]" />
            <div className="skeleton h-5 w-32" />
          </div>
          <div className="skeleton h-4 w-10" />
        </div>

        {/* Lot cards skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
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

        {/* Slot section header skeleton */}
        <div className="mb-4 flex items-center justify-between border-b border-[var(--border-default)] pb-3">
          <div className="flex items-center gap-3">
            <div className="h-4 w-1 bg-[var(--accent)]" />
            <div className="skeleton h-5 w-44" />
          </div>
        </div>

        {/* Slot cards skeleton */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
              <div className="h-1 skeleton" />
              <div className="p-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="skeleton h-2.5 w-14 mb-2" />
                    <div className="skeleton h-7 w-8" />
                  </div>
                  <div className="skeleton h-8 w-8" />
                </div>
                <div className="skeleton h-5 w-12 mt-3" />
              </div>
              <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-3 py-2 bg-[var(--bg-tertiary)]">
                <div className="skeleton h-3 w-16" />
                <div className="skeleton h-3 w-14" />
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
