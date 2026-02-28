export default function SettingsLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <div className="mb-6">
          <div className="skeleton h-8 w-56 mb-2" />
          <div className="skeleton h-4 w-72" />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
              <div className="h-1 skeleton" />
              <div className="p-4">
                <div className="flex items-start gap-3">
                  <div className="skeleton h-10 w-10" />
                  <div>
                    <div className="skeleton h-4 w-28 mb-2" />
                    <div className="skeleton h-3 w-40" />
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <div className="skeleton h-9 w-full" />
                  <div className="skeleton h-9 w-full" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
