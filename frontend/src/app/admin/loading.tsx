export default function AdminLoading() {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed top-0 left-0 right-0 z-50 h-14 bg-[var(--bg-secondary)] border-b border-[var(--border-default)]" />

      <main className="mx-auto max-w-7xl px-4 pt-24 pb-16 sm:px-6">
        <div className="mb-6">
          <div className="skeleton h-8 w-48 mb-2" />
          <div className="skeleton h-4 w-64" />
        </div>

        <div className="mb-8 hidden space-y-2 md:block">
          {[1, 2, 3].map((item) => (
            <div key={item} className="skeleton h-12 border border-[var(--border-subtle)]" />
          ))}
        </div>

        <div className="mb-8 space-y-2 md:hidden">
          {[1, 2, 3].map((item) => (
            <div key={item} className="border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-3">
              <div className="mb-2 flex items-center justify-between">
                <div className="skeleton h-4 w-24" />
                <div className="skeleton h-3 w-12" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="skeleton h-10" />
                <div className="skeleton h-10" />
              </div>
              <div className="skeleton h-10 mt-2" />
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="skeleton h-52 border border-[var(--border-subtle)]" />
          <div className="skeleton h-52 border border-[var(--border-subtle)]" />
        </div>
      </main>
    </div>
  );
}
