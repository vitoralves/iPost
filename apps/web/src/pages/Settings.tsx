import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { getAuthStatus, getRuns } from "../api"
import type { AuthStatus, SchedulerRun } from "../types"

const schedule = [
  ["Story generation", "04:00"],
  ["Story publish", "06:00"],
  ["Insights sync", "07:30"],
  ["Reel generation", "17:00"],
  ["Reel publish", "19:00"],
]

function formatWhen(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })
}

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

function formatUsd(value: number) {
  return `US$ ${value.toFixed(4)}`
}

export function SettingsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [runs, setRuns] = useState<SchedulerRun[]>([])
  const [status, setStatus] = useState("Loading…")
  const [runsError, setRunsError] = useState("")

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
    getRuns()
      .then((next) => {
        setRuns(next)
        setRunsError("")
      })
      .catch((exc: unknown) => {
        setRuns([])
        setRunsError(exc instanceof Error ? exc.message : "Could not load worker runs")
      })
  }, [])

  const days = auth?.days_until_expiry
  const reconnectHref = `${import.meta.env.VITE_API_URL ?? "/api"}/auth/instagram`
  const lambdaCost = runs.reduce((sum, run) => sum + (run.estimated_cost_usd || 0), 0)
  const failed = runs.filter((run) => run.status === "error").length
  const skipped = runs.filter((run) => run.status === "skipped").length

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
        <div className="field-label">Worker runs</div>
        <div className="kv">
          <span>Lambda compute (this list)</span>
          <span>{formatUsd(lambdaCost)}</span>
        </div>
        <div className="kv">
          <span>Failed / skipped</span>
          <span>
            {failed} / {skipped}
          </span>
        </div>
        <p className="page-sub">
          This is Lambda GB-seconds only. gpt-image-2 and Bedrock Nova Pro show on the OpenAI and
          AWS bills. Viewing those consoles is free. Email goes out on failures and when a clock
          skips because a post is not ready.
        </p>
        {runsError ? <p className="page-sub">{runsError}</p> : null}
        {runs.length === 0 && !runsError ? (
          <p className="page-sub">No worker runs yet.</p>
        ) : (
          runs.map((run) => (
            <article className={`run-row ${run.status}`} key={run.id}>
              <div className="run-head">
                <span className={`pill ${run.status}`}>
                  {run.status} · {run.action}
                  {run.job_type ? ` ${run.job_type}` : ""}
                </span>
                <time dateTime={run.created_at}>{formatWhen(run.created_at)}</time>
              </div>
              <p className="run-meta">
                {formatDuration(run.duration_ms)}
                {run.estimated_cost_usd ? ` · ${formatUsd(run.estimated_cost_usd)}` : ""}
                {run.source === "api" ? " · dashboard" : " · clock"}
                {run.job_id ? (
                  <>
                    {" · "}
                    <Link to={`/jobs/${run.job_id}`}>{run.job_id}</Link>
                  </>
                ) : null}
              </p>
              {run.message ? <p className="run-msg">{run.message}</p> : null}
            </article>
          ))
        )}
      </section>
    </div>
  )
}
