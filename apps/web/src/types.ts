export type JobType = "STORY" | "REEL"
export type JobStatus =
  | "SCHEDULED"
  | "GENERATING"
  | "CRITIQUE"
  | "REGENERATING"
  | "APPROVED"
  | "NEEDS_REVIEW"
  | "REJECTED"
  | "PUBLISHING"
  | "PUBLISHED"
  | "FAILED"
  | "SKIPPED"

export type TopicSlug = string

export type CriticSubscores = {
  brand: number
  clarity: number
  spec: number
  originality: number
  safety: number
}

export type TimelineStep = {
  label: string
  sub: string
  kind: "neutral" | "bad" | "current"
}

export type JobInsights = {
  views: number
  reach: number
  saved: number
  likes: number
  comments: number
  shares: number
  replies: number
  total_interactions: number
}

export type Job = {
  id: string
  type: JobType
  slot: "morning" | "evening"
  date: string
  publishAt: string
  topic: TopicSlug
  status: JobStatus
  stillUrl: string
  videoUrl: string
  caption: string
  audioId: string | null
  score: number
  attempt: number
  maxAttempts: number
  mustFix: string | null
  subscores: CriticSubscores
  timeline: TimelineStep[]
  igMediaId: string | null
  insights: JobInsights | null
  insightsSyncedAt: string | null
}

export type Topic = {
  slug: TopicSlug
  name: string
  last_used: string | null
  weight: number
  audio_ids: string[]
  enabled: boolean
  refs: string[]
}

export type Track = {
  id: string
  title: string
  artist: string
  duration: string
  last_used: string | null
  topics: TopicSlug[]
  path?: string
}

export type AlertItem = {
  at: string
  message: string
}

export type SchedulerRun = {
  id: string
  action: string
  status: "ok" | "skipped" | "error" | string
  source: string
  job_type: string | null
  job_id: string | null
  message: string
  duration_ms: number
  memory_mb: number
  estimated_cost_usd: number
  request_id: string | null
  created_at: string
}

export type AuthStatus = {
  connected: boolean
  user_id?: string
  username?: string
  days_until_expiry?: number | null
  permissions?: string[]
  has_insights?: boolean
}

export type JobPayload = {
  id: string
  type: JobType
  slot: "morning" | "evening"
  date: string
  publish_at: string
  topic: TopicSlug
  status: JobStatus
  still_path: string
  still_url?: string
  video_path?: string
  video_url?: string
  caption: string
  audio_id: string | null
  score: number
  attempt: number
  max_attempts: number
  must_fix: string | null
  subscores: CriticSubscores | null
  timeline: TimelineStep[]
  hook?: string
  visual_prompt?: string
  ig_media_id?: string | null
  insights?: JobInsights | null
  insights_synced_at?: string | null
}

export type StyleRef = {
  id: string
  url: string
  path?: string
  note: string
  topic: string
}

export type BrandKit = {
  voice_tone: string
  banned: string[]
  refs: StyleRef[]
}
