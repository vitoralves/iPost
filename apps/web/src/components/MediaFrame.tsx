import type { Job } from "../types"
import { formatScore, scoreTone } from "../lib"
import { ImageOffIcon } from "./Icons"
import { StatusPill, TopicPill } from "./Pills"

type Props = {
  job: Job
  showNote?: boolean
}

export function MediaFrame({ job, showNote = true }: Props) {
  const tone = scoreTone(job.score)
  const review = job.status === "NEEDS_REVIEW"

  return (
    <div className={`media ${review ? "review" : ""}`}>
      {job.videoUrl ? (
        <video src={job.videoUrl} poster={job.stillUrl || undefined} muted loop playsInline controls />
      ) : job.stillUrl ? (
        <img src={job.stillUrl} alt="" />
      ) : (
        <div className="media-empty">
          <ImageOffIcon size={22} />
        </div>
      )}
      <div className="media-pills">
        <StatusPill status={job.status} />
        <TopicPill topic={job.topic} />
      </div>
      <div className="media-count">
        {job.attempt}/{job.maxAttempts}
      </div>
      {job.score > 0 ? (
        <div className={`media-score ${tone}`}>{formatScore(job.score)}</div>
      ) : null}
      {showNote && job.mustFix && review ? (
        <div className="media-note">{job.mustFix}</div>
      ) : null}
    </div>
  )
}
