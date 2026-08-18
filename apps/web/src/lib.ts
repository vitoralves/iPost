import type { JobStatus } from "./types"

export const TIMEZONE = "America/Sao_Paulo"
export const REVIEW_WINDOW = "Review window: Story 04:00—06:00 · Reel 17:00—19:00"

export function todayISO() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE }).format(new Date())
}

export function daysAgoISO(days: number) {
  const [year, month, day] = todayISO().split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() - days)
  return date.toISOString().slice(0, 10)
}

export function formatCount(value: number) {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1).replace(".0", "")}k`
  }
  return String(value)
}

export function headerDate() {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: TIMEZONE,
  }).format(new Date())
}

export function calendarDates(days = 14) {
  const today = todayISO()
  const [year, month, day] = today.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  const weekday = date.getUTCDay()
  const mondayOffset = weekday === 0 ? -6 : 1 - weekday
  date.setUTCDate(date.getUTCDate() + mondayOffset)
  return Array.from({ length: days }, (_, index) => {
    const next = new Date(date)
    next.setUTCDate(date.getUTCDate() + index)
    return next.toISOString().slice(0, 10)
  })
}

export function nextEventLabel() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date())
  const hour = Number(parts.find((part) => part.type === "hour")?.value)
  const minute = Number(parts.find((part) => part.type === "minute")?.value)
  const mins = hour * 60 + minute
  if (mins < 6 * 60) return "Next: Story 06:00"
  if (mins < 19 * 60) return "Next: Reel 19:00"
  return "Next: Story 06:00"
}

export function timeUntilLabel(date: string, publishAt: string) {
  const target = new Date(`${date}T${publishAt}:00-03:00`)
  const diff = target.getTime() - Date.now()
  if (diff <= 0) return "Publish window passed"
  const mins = Math.round(diff / 60000)
  const hours = Math.floor(mins / 60)
  const rest = mins % 60
  if (hours <= 0) return `in ${rest}m`
  return `in ${hours}h ${rest}m`
}

export function formatScore(score: number) {
  return `${score.toFixed(1)} / 10`
}

export function scoreTone(score: number): "good" | "warn" | "bad" {
  if (score >= 7) return "good"
  if (score >= 5.5) return "warn"
  return "bad"
}

export function barColor(score: number) {
  if (score >= 7.5) return "#8aa67a"
  if (score >= 6) return "#c4a570"
  if (score >= 5.5) return "#c4894a"
  return "#c45c4a"
}

export function statusLabel(status: JobStatus) {
  return status.replaceAll("_", " ")
}

export function statusClass(status: JobStatus) {
  return status.toLowerCase()
}

export function dayNum(date: string) {
  return Number(date.slice(8))
}

export function topicTitle(name: string) {
  return name.toUpperCase()
}
