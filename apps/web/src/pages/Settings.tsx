import { useEffect, useState } from "react"
import { getAuthStatus } from "../api"
import type { AuthStatus } from "../types"

const schedule = [
  ["Story generation", "04:00"],
  ["Story publish", "06:00"],
  ["Insights sync", "07:30"],
  ["Reel generation", "17:00"],
  ["Reel publish", "19:00"],
]

export function SettingsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [status, setStatus] = useState("Loading…")

  useEffect(() => {
    getAuthStatus()
      .then((next) => {
        setAuth(next)
        setStatus("")
      })
      .catch((exc: unknown) => {
        setAuth(null)
        setStatus(exc instanceof Error ? exc.message : "Could not load Instagram status")
      })
  }, [])

  const days = auth?.days_until_expiry
  const reconnectHref = `${import.meta.env.VITE_API_URL ?? "/api"}/auth/instagram`

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">Settings</h1>
      </div>
      {status ? <p className="page-sub">{status}</p> : null}
      <section className="settings-block">
        <div className="field-label">Schedule — America/Sao_Paulo (read-only)</div>
        {schedule.map(([label, value]) => (
          <div className="kv" key={label}>
            <span>{label}</span>
            <span>{value}</span>
          </div>
        ))}
      </section>
      <section className="settings-block">
        <div className="field-label">Instagram</div>
        <div className="ig-row field-box">
          <div>
            <div className="connected">
              <span className="dot" />
              {auth?.connected
                ? `Connected · ${auth.username ?? "Professional account"}`
                : "Not connected"}
            </div>
            <div className="connected-sub">
              {auth?.connected && days != null
                ? `Token expires in ${days} days`
                : "Connect a Professional Instagram account"}
            </div>
            {auth?.connected && !auth.has_insights ? (
              <div className="connected-sub">
                Reconnect to grant insights access so topic weights can learn from Reels.
              </div>
            ) : null}
          </div>
          <a className="btn gold-text" href={reconnectHref}>
            {auth?.connected ? "Reconnect" : "Connect"}
          </a>
        </div>
      </section>
      <section className="settings-block">
        <div className="field-label">Auto-publish rule (read-only)</div>
        <p className="field-box">
          A post auto-publishes only if the critic score is{" "}
          <strong>7.0 / 10 or higher</strong>. After <strong>3 failed regenerations</strong>,
          the post is flagged as <strong>Needs review</strong> and will not publish
          automatically.
        </p>
      </section>
      <section className="settings-block">
        <div className="field-label">Alerts log</div>
        <p className="page-sub">No alerts yet.</p>
      </section>
    </div>
  )
}