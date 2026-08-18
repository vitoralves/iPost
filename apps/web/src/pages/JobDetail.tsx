import { useMemo } from "react"
import { Navigate, useNavigate, useParams } from "react-router-dom"
import { MediaFrame } from "../components/MediaFrame"
import { PlayIcon } from "../components/Icons"
import { ScoreBars } from "../components/ScoreBars"
import { Timeline } from "../components/Timeline"
import { StatusPill, TopicPill } from "../components/Pills"
import { useStore } from "../store"

export function JobDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    jobs,
    loading,
    busy,
    trackById,
    generateStory,
    publishStory,
    rejectStory,
    skipStory,
  } = useStore()
  const job = jobs.find((item) => item.id === id)

  const title = useMemo(() => {
    if (!job) return ""
    const kind = job.type === "STORY" ? "Story" : "Reel"
    const topic = job.topic[0].toUpperCase() + job.topic.slice(1)
    return `${job.date} — ${topic} ${kind}`
  }, [job])

  if (loading) return <p className="page-sub">Loading…</p>
  if (!job) return <Navigate to="/" replace />

  const current = job
  const track = trackById(current.audioId)
  const slotLabel = `${current.type} · ${current.slot}`
  const closed =
    current.status === "PUBLISHED" ||
    current.status === "SKIPPED" ||
    current.status === "REJECTED"
  const canPublish = current.type === "STORY" && !closed

  return (
    <div className="page">
      <div className="detail">
        <MediaFrame job={current} showNote={false} />
        <div>
          <div className="detail-head">
            <span>{slotLabel}</span>
            <TopicPill topic={current.topic} />
            <StatusPill status={current.status} />
          </div>
          <div className="detail-title-row">
            <h1 className="detail-title">{title}</h1>
          </div>
          {current.type === "REEL" ? (
            <>
              <div className="field-label">Caption</div>
              <p className="field-box">{current.caption || "No caption"}</p>
              <div className="field-label">Audio track</div>
              <div className="audio-card">
                <button type="button" className="play" aria-label="Play">
                  <PlayIcon />
                </button>
                <div>
                  <div>
                    {track ? `${track.title} — ${track.artist}` : "No track"}
                  </div>
                  <div className="track-meta">{track?.duration}</div>
                </div>
                <div className="wave" />
              </div>
            </>
          ) : null}
          <ScoreBars score={current.score} subscores={current.subscores} />
          <Timeline steps={current.timeline} />
          {canPublish ? (
            <div className="btn-row">
              <button
                type="button"
                className="btn primary"
                disabled={busy}
                onClick={() => publishStory(current.id)}
              >
                {current.status === "NEEDS_REVIEW" ? "Approve & publish" : "Publish"}
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => rejectStory(current.id)}
              >
                Reject
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => {
                  void generateStory(current.date, current.topic).then((next) => {
                    if (next) navigate(`/jobs/${next.id}`)
                  })
                }}
              >
                Regenerate
              </button>
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => skipStory(current.id)}
              >
                Skip
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}