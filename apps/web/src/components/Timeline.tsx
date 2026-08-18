import type { TimelineStep } from "../types"

export function Timeline({ steps }: { steps: TimelineStep[] }) {
  if (steps.length === 0) return null

  return (
    <div className="section">
      <div className="field-label">Attempt timeline</div>
      <div className="timeline">
        {steps.map((step) => (
          <div className="tl-step" key={`${step.label}-${step.sub}`}>
            <div className={`tl-dot ${step.kind}`} />
            <div className="tl-label">{step.label}</div>
            <div className="tl-sub">{step.sub}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
