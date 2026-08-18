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
  const { busy, publishStory, rejectStory, skipStory, generateStory, trackById } = useStore()
  const track = trackById(job.audioId)
  const isStory = job.type === "STORY"
  const review = job.status === "NEEDS_REVIEW"
  const closed = job.status === "PUBLISHED" || job.status === "SKIPPED" || job.status === "REJECTED"

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
        {isStory && !closed ? (
          <div className="btn-row">
            {review ? (
              <>
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy}
                  onClick={() => publishStory(job.id)}
                >
                  Approve & publish
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={busy}
                  onClick={() => generateStory(job.date, job.topic)}
                >
                  Regenerate
                </button>
                <button
                  type="button"
                  className="btn"
                  disabled={busy}
                  onClick={() => skipStory(job.id)}
                >
                  Skip today
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy}
                  onClick={() => publishStory(job.id)}
                >
                  Publish
                </button>
                <button
                  type="button"
                  className="btn danger"
                  disabled={busy}
                  onClick={() => rejectStory(job.id)}
                >
                  Reject
                </button>
                <Link className="btn filled" to={`/jobs/${job.id}`}>
                  View detail
                </Link>
              </>
            )}
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
  const { jobs, loading, busy, generateStory } = useStore()
  const todayDate = todayISO()
  const story = jobs.find((item) => item.date === todayDate && item.type === "STORY")
  const reel = jobs.find((item) => item.date === todayDate && item.type === "REEL")

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Today</h1>
          <p className="page-sub">{REVIEW_WINDOW}</p>
        </div>
        {!story ? (
          <button
            type="button"
            className="btn primary"
            disabled={busy || loading}
            onClick={() => generateStory(todayDate)}
          >
            {busy ? "Generating…" : "Generate Story"}
          </button>
        ) : null}
      </div>
      {loading ? <p className="page-sub">Loading…</p> : null}
      {!loading && !story ? <p className="page-sub">No Story for today yet.</p> : null}
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
        ) : null}
        {reel ? (
          <Slot
            job={reel}
            kicker="Evening Reel"
            meta={
              reel.status === "NEEDS_REVIEW"
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
            <p className="page-sub">Reel automation is Phase 2.</p>
          </article>
        )}
      </div>
    </div>
  )
}