import { useMemo } from "react"
import { Link, Navigate, useNavigate, useParams } from "react-router-dom"
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
    tracks,
    loading,
    busy,
    trackById,
    generateStory,
    generateReel,
    attachAudio,
    publishStory,
    rejectStory,
    skipStory,
    refreshInsights,
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
  const readyTracks = tracks.filter((item) => Boolean(item.path))
  const slotLabel = `${current.type} · ${current.slot}`
  const closed =
    current.status === "PUBLISHED" ||
    current.status === "SKIPPED" ||
    current.status === "REJECTED"
  const isReel = current.type === "REEL"
  const canPublish = !closed && (current.type === "STORY" || Boolean(current.videoUrl))
  const regenerate = () =>
    current.type === "STORY"
      ? generateStory(current.date, current.topic)
      : generateReel(current.date, current.topic)

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
          {isReel ? (
            <>
              <div className="field-label">Caption</div>
              <p className="field-box">{current.caption || "No caption"}</p>
              <div className="field-label">Audio track</div>
              <div className="audio-card">
                <button type="button" className="play" aria-label="Play" disabled>
                  <PlayIcon />
                </button>
                <div>
                  <div>
                    {track ? `${track.title} — ${track.artist}` : "No track yet"}
                  </div>
                  <div className="track-meta">{track?.duration}</div>
                </div>
                <div className="wave" />
              </div>
              {!closed ? (
                <>
                  <select
                    className="select"
                    value={current.audioId ?? ""}
                    disabled={busy || readyTracks.length === 0}
                    onChange={(event) => {
                      const trackId = event.target.value
                      if (trackId) void attachAudio(current.id, trackId)
                    }}
                  >
                    <option value="">
                      {readyTracks.length ? "Change library track" : "Upload audio first"}
                    </option>
                    {readyTracks.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title} — {item.artist}
                      </option>
                    ))}
                  </select>
                  {readyTracks.length === 0 ? (
                    <p className="page-sub">
                      Upload a file on the <Link to="/audio">Audio</Link> page and tag this topic.
                    </p>
                  ) : (
                    <p className="page-sub">
                      Generate picks a track tagged for this topic. Change it only to remux.
                    </p>
                  )}
                </>
              ) : null}
            </>
          ) : null}
          <ScoreBars score={current.score} subscores={current.subscores} />
          {current.status === "PUBLISHED" ? (
            <>
              <div className="field-label">Instagram insights</div>
              {current.insights ? (
                <div className="insights-grid">
                  {(current.type === "REEL"
                    ? [
                        ["Views", current.insights.views],
                        ["Reach", current.insights.reach],
                        ["Saves", current.insights.saved],
                        ["Likes", current.insights.likes],
                        ["Comments", current.insights.comments],
                        ["Shares", current.insights.shares],
                      ]
                    : [
                        ["Views", current.insights.views],
                        ["Reach", current.insights.reach],
                        ["Replies", current.insights.replies],
                        ["Shares", current.insights.shares],
                      ]
                  ).map(([label, value]) => (
                    <div className="insights-cell" key={String(label)}>
                      <span>{label}</span>
                      <strong>{value}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="field-box">No insights yet. Numbers appear after Instagram has views.</p>
              )}
              <p className="page-sub">
                {current.insightsSyncedAt
                  ? `Last synced ${current.insightsSyncedAt.replace("T", " ").slice(0, 19)}`
                  : "Not synced yet"}
              </p>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn"
                  disabled={busy || !current.igMediaId}
                  onClick={() => void refreshInsights(current.id)}
                >
                  Refresh insights
                </button>
              </div>
            </>
          ) : null}
          <Timeline steps={current.timeline} />
          {!closed ? (
            <div className="btn-row">
              {canPublish ? (
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy}
                  onClick={() => publishStory(current.id)}
                >
                  {current.status === "NEEDS_REVIEW" ? "Approve & publish" : "Publish"}
                </button>
              ) : null}
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
                  void regenerate().then((next) => {
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
