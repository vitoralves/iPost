import type { JobStatus, TopicSlug } from "../types"
import { statusClass, statusLabel, topicTitle } from "../lib"

export function StatusPill({ status }: { status: JobStatus }) {
  return <span className={`pill ${statusClass(status)}`}>{statusLabel(status)}</span>
}

export function TopicPill({ topic }: { topic: TopicSlug }) {
  return <span className={`pill ${topic}`}>{topicTitle(topic)}</span>
}
