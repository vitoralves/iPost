import { Link } from "react-router-dom"
import { MediaFrame } from "../components/MediaFrame"
import { PlayIcon, WarnIcon } from "../components/Icons"
import { REVIEW_WINDOW, formatScore, scoreTone, timeUntilLabel, todayISO } from "../lib"
import { useStore } from "../store"
import type { Job } from "../types"

function Slot({
  job,
  kicker,
  meta,
  metaClass,
}: {
  job: Job
  kicker: string
  meta: string
  metaClass?: string
}) {
  const { busy, publishStory, rejectStory, skipStory, generateStory, generateReel, trackById } =
    useStore()
  const track = trackById(job.audioId)
  const isStory = job.type === "STORY"
  const review = job.status === "NEEDS_REVIEW"
  const closed = job.status === "PUBLISHED" || job.status === "SKIPPED" || job.status === "REJECTED"
  const regenerate = () =>
    isStory ? generateStory(job.date, job.topic) : generateReel(job.date, job.topic)
  const canPublish = !closed && (isStory || Boolean(job.videoUrl))

  return (
    <article className="slot">
      <div className="slot-head">
        <div className="kicker">{kicker}</div>
        <div className="slot-meta">
          <span>Publishes {job.publishAt}</span>
          <span className={metaClass}>{meta}</span>
        </div>
      </div>
      <Link to={`/jobs/${job.id}`}>
        <MediaFrame job={job} />
      </Link>
      {job.caption ? <p className="field-box caption">{job.caption}</p> : null}
      {track ? (
        <div className="audio-line">
          <PlayIcon />
          {track.title} — {track.artist}
        </div>
      ) : null}
      <div className="slot-actions">
        <div className={`score-lg ${scoreTone(job.score)}`}>{formatScore(job.score)}</div>
        {!closed ? (
          <div className="btn-row">
            {canPublish ? (
              <button
                type="button"
                className="btn primary"
                disabled={busy}
                onClick={() => publishStory(job.id)}
              >
                {review ? "Approve & publish" : "Publish"}
              </button>
            ) : (
              <Link className="btn primary" to={`/jobs/${job.id}`}>
                Pick audio
              </Link>
            )}
            {review || !isStory ? (
              <button type="button" className="btn" disabled={busy} onClick={() => regenerate()}>
                Regenerate
              </button>
            ) : null}
            {isStory && review ? (
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => skipStory(job.id)}
              >
                Skip today
              </button>
            ) : null}
            {isStory && !review ? (
              <button
                type="button"
                className="btn danger"
                disabled={busy}
                onClick={() => rejectStory(job.id)}
              >
                Reject
              </button>
            ) : null}
            {!isStory ? (
              <button
                type="button"
                className="btn danger"
                disabled={busy}
                onClick={() => rejectStory(job.id)}
              >
                Reject
              </button>
            ) : null}
            <Link className="btn filled" to={`/jobs/${job.id}`}>
              View detail
            </Link>
          </div>
        ) : (
          <div className="btn-row">
            <Link className="btn filled" to={`/jobs/${job.id}`}>
              View detail
            </Link>
          </div>
        )}
        {review ? (
          <div className="warn-bar">
            <WarnIcon />
            Needs review — will not auto-publish
          </div>
        ) : null}
      </div>
    </article>
  )
}

export function TodayPage() {
  const { jobs, loading, busy, generateStory, generateReel } = useStore()
  const todayDate = todayISO()
  const story = jobs.find((item) => item.date === todayDate && item.type === "STORY")
  const reel = jobs.find((item) => item.date === todayDate && item.type === "REEL")
  const canGenerateStory = !story || !story.stillUrl
  const canGenerateReel = !reel || !reel.stillUrl

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Today</h1>
          <p className="page-sub">{REVIEW_WINDOW}</p>
        </div>
        {canGenerateStory || canGenerateReel ? (
          <div className="btn-row">
            {canGenerateStory ? (
              <button
                type="button"
                className="btn primary"
                disabled={busy || loading}
                onClick={() => generateStory(todayDate, story?.topic)}
              >
                {busy ? "Generating…" : story ? "Regenerate Story" : "Generate Story"}
              </button>
            ) : null}
            {canGenerateReel ? (
              <button
                type="button"
                className="btn"
                disabled={busy || loading}
                onClick={() => generateReel(todayDate, reel?.topic)}
              >
                {busy ? "Generating…" : reel ? "Regenerate Reel" : "Generate Reel"}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
      {!loading && !story && !reel ? <p className="page-sub">No posts for today yet.</p> : null}
      <div className="today-grid">
        {story ? (
          <Slot
            job={story}
            kicker="Morning Story"
            meta={
              story.status === "PUBLISHED"
                ? "Published"
                : timeUntilLabel(story.date, story.publishAt)
            }
            metaClass="gold-text"
          />
        ) : (
          <article className="slot">
            <div className="slot-head">
              <div className="kicker">Morning Story</div>
            </div>
            <p className="page-sub">No Story for today yet.</p>
          </article>
        )}
        {reel ? (
          <Slot
            job={reel}
            kicker="Evening Reel"
            meta={
              reel.status === "PUBLISHED"
                ? "Published"
                : reel.status === "NEEDS_REVIEW"
                  ? "Manual action required"
                  : timeUntilLabel(reel.date, reel.publishAt)
            }
            metaClass={reel.status === "NEEDS_REVIEW" ? "red-text" : "gold-text"}
          />
        ) : (
          <article className="slot">
            <div className="slot-head">
              <div className="kicker">Evening Reel</div>
            </div>
            <p className="page-sub">Generate one cream editorial still, then pick a library track.</p>
          </article>
        )}
      </div>
    </div>
  )
}
