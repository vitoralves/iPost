import type { CriticSubscores } from "../types"
import { barColor, formatScore, scoreTone } from "../lib"

const rows: { key: keyof CriticSubscores; label: string }[] = [
  { key: "brand", label: "Brand alignment" },
  { key: "clarity", label: "Clarity" },
  { key: "spec", label: "Spec compliance" },
  { key: "originality", label: "Originality" },
  { key: "safety", label: "Safety" },
]

export function ScoreBars({
  score,
  subscores,
}: {
  score: number
  subscores: CriticSubscores
}) {
  return (
    <div>
      <div className="section-head">
        <div className="field-label">Critic breakdown</div>
        <div className={`score-lg ${scoreTone(score)}`}>{formatScore(score)}</div>
      </div>
      <div className="metrics">
        {rows.map((row) => {
          const value = subscores[row.key]
          return (
            <div className="metric" key={row.key}>
              <span>{row.label}</span>
              <div className="bar">
                <span style={{ width: `${value * 10}%`, background: barColor(value) }} />
              </div>
              <span>{value.toFixed(1)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
