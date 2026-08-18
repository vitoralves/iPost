import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { login } from "../api"

export function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError("")
    try {
      await login(username, password)
      navigate("/", { replace: true })
    } catch (exc: unknown) {
      setError(exc instanceof Error ? exc.message : "Could not sign in")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={(event) => void onSubmit(event)}>
        <div className="brand">
          <span className="brand-name">iPost</span>
          <span className="brand-mark">STUDIO</span>
        </div>
        <label className="field-label" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          className="field-box"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
        <label className="field-label" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          className="field-box"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {error ? <p className="login-error">{error}</p> : null}
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  )
}
