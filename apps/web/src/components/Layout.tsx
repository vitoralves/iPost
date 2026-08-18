import { useEffect, useState } from "react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { getAuthStatus } from "../api"
import { headerDate, nextEventLabel, TIMEZONE } from "../lib"
import { useStore } from "../store"
import type { AuthStatus } from "../types"
import { ErrorToast } from "./ErrorToast"
import { ChevronLeft, WarnIcon } from "./Icons"
import { SpinnerOverlay } from "./SpinnerOverlay"

const links = [
  { to: "/", label: "Today" },
  { to: "/calendar", label: "Calendar" },
  { to: "/topics", label: "Topics" },
  { to: "/audio", label: "Audio" },
  { to: "/brand-kit", label: "Brand Kit" },
  { to: "/settings", label: "Settings" },
]

export function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { error, errorSeq, clearError, loading, busy } = useStore()
  const isDetail = location.pathname.startsWith("/jobs/")
  const [auth, setAuth] = useState<AuthStatus | null>(null)

  useEffect(() => {
    getAuthStatus()
      .then(setAuth)
      .catch(() => setAuth({ connected: false }))
  }, [])

  const days = auth?.days_until_expiry

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-name">iPost</span>
          <span className="brand-mark">STUDIO</span>
        </div>
        <nav className="nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/"}
              className={({ isActive }) =>
                isActive || (link.to === "/" && isDetail) ? "active" : ""
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="connected">
            <span className="dot" />
            {auth?.connected ? "Connected" : "Not connected"}
          </div>
          <div className="connected-sub">
            {auth?.connected
              ? `${auth.username ?? "instagram"} · professional`
              : "instagram · professional"}
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            {isDetail ? (
              <button type="button" className="back" onClick={() => navigate(-1)}>
                <ChevronLeft />
                Back
              </button>
            ) : null}
            <span className="topbar-date">{headerDate()}</span>
          </div>
          <div className="topbar-meta">
            <span>{TIMEZONE}</span>
            <span>{nextEventLabel()}</span>
          </div>
          {auth?.connected && days != null ? (
            <div className="token-warn">
              <WarnIcon />
              Instagram token expires in {days} days
            </div>
          ) : null}
        </header>
        <Outlet />
        <SpinnerOverlay show={loading || busy} />
        <ErrorToast message={error} seq={errorSeq} onDismiss={clearError} />
      </div>
    </div>
  )
}