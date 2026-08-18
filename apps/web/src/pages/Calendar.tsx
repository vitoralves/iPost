import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ImageOffIcon } from "../components/Icons"
import { calendarDates, dayNum, formatCount, scoreTone, todayISO } from "../lib"
import { useStore } from "../store"
import type { Job, JobStatus, TopicSlug } from "../types"

const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

function Thumb({ job, letter }: { job: Job | undefined; letter: string }) {
  if (!job) {
    return (
      <div className="thumb empty">
        <span>{letter}</span>
      </div>
    )
  }

  return (
    <Link className="thumb" to={`/jobs/${job.id}`}>
      {job.stillUrl ? (
        <img src={job.stillUrl} alt="" />
      ) : (
        <div className="media-empty">
          <ImageOffIcon size={16} />
        </div>
      )}
      {job.status === "PUBLISHED" && (job.insights?.views || job.insights?.reach) ? (
        <span className="thumb-score">
          {formatCount((job.insights?.views || job.insights?.reach) ?? 0)} views
        </span>
      ) : job.score > 0 ? (
        <span className="thumb-score">{job.score.toFixed(1)}</span>
      ) : null}
    </Link>
  )
}

function SlotLabel({ job, letter }: { job: Job | undefined; letter: string }) {
  const tone = job ? scoreTone(job.score || 0) : "muted"
  const failed = job?.status === "FAILED" || job?.status === "NEEDS_REVIEW"
  return (
    <div className="thumb-label">
      <span className={`status-dot ${failed ? "bad" : job ? tone : "muted"}`} />
      {letter}
    </div>
  )
}

export function CalendarPage() {
  const { jobs, topics } = useStore()
  const [status, setStatus] = useState<"all" | JobStatus>("all")
  const [topic, setTopic] = useState<"all" | TopicSlug>("all")
  const dates = calendarDates()
  const todayDate = todayISO()

  const filtered = useMemo(() => {
    return jobs.filter((job) => {
      if (status !== "all" && job.status !== status) return false
      if (topic !== "all" && job.topic !== topic) return false
      return true
    })
  }, [jobs, status, topic])

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">Calendar</h1>
        <div className="filters">
          <select
            className="select"
            value={status}
            onChange={(event) => setStatus(event.target.value as "all" | JobStatus)}
          >
            <option value="all">All statuses</option>
            <option value="PUBLISHED">Published</option>
            <option value="APPROVED">Approved</option>
            <option value="NEEDS_REVIEW">Needs review</option>
            <option value="FAILED">Failed</option>
          </select>
          <select
            className="select"
            value={topic}
            onChange={(event) => setTopic(event.target.value as "all" | TopicSlug)}
          >
            <option value="all">All topics</option>
            {topics.map((item) => (
              <option key={item.slug} value={item.slug}>
                {item.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="cal">
        {weekdays.map((day) => (
          <div className="cal-h" key={day}>
            {day}
          </div>
        ))}
        {dates.map((date, index) => {
          const story = filtered.find((job) => job.date === date && job.type === "STORY")
          const reel = filtered.find((job) => job.date === date && job.type === "REEL")
          const isToday = date === todayDate
          return (
            <div className={`cal-cell ${isToday ? "today" : ""}`} key={date}>
              <div className={`cal-date ${isToday ? "today" : ""}`}>
                <span>
                  {weekdays[index % 7]} {dayNum(date)}
                </span>
                {isToday ? <span className="gold-text">TODAY</span> : null}
              </div>
              <div className="cal-slots">
                <div>
                  <Thumb job={story} letter="S" />
                  {story ? <SlotLabel job={story} letter="S" /> : null}
                </div>
                <div>
                  <Thumb job={reel} letter="R" />
                  {reel ? <SlotLabel job={reel} letter="R" /> : null}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
