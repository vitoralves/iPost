import { useEffect, useState } from "react"
import { Navigate, Outlet } from "react-router-dom"
import { getSession } from "../api"

export function RequireAuth() {
  const [state, setState] = useState<"loading" | "in" | "out">("loading")

  useEffect(() => {
    getSession()
      .then(() => setState("in"))
      .catch(() => setState("out"))
  }, [])

  if (state === "loading") {
    return <div className="login-page" />
  }
  if (state === "out") {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
