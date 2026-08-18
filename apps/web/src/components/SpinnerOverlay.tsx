export function SpinnerOverlay({ show }: { show: boolean }) {
  if (!show) return null
  return (
    <div className="spinner-overlay" role="status" aria-live="polite" aria-busy="true">
      <span className="spinner" />
      <span className="spinner-label">Working…</span>
    </div>
  )
}
