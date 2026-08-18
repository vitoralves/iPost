import type { AuthStatus, BrandKit, Job, JobPayload, StyleRef, Topic, Track } from "./types"

const base = import.meta.env.VITE_API_URL ?? "/api"

const emptySubscores = {
  brand: 0,
  clarity: 0,
  spec: 0,
  originality: 0,
  safety: 0,
}

const REEL_HASHTAGS = "#fé #deus #devocional #esperança #oração"

function splitCaptionSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
}

export function formatReelCaption(caption: string): string {
  const stripped = caption.replaceAll(REEL_HASHTAGS, " ").trim()
  if (!stripped) {
    return REEL_HASHTAGS
  }
  let parts: string[]
  if (stripped.includes("\n")) {
    parts = stripped
      .split(/\n+/)
      .map((part) => part.trim())
      .filter(Boolean)
    if (parts.length < 2) {
      parts = splitCaptionSentences(parts[0] ?? stripped)
    }
  } else {
    parts = splitCaptionSentences(stripped)
  }
  return `${parts.join("\n\n")}\n\n${REEL_HASHTAGS}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text()
    try {
      const payload = JSON.parse(detail) as { detail?: unknown }
      if (typeof payload.detail === "string") {
        throw new Error(payload.detail)
      }
    } catch (exc) {
      if (exc instanceof Error && exc.message !== detail) {
        throw exc
      }
    }
    throw new Error(detail || `API ${response.status}`)
  }
  return (await response.json()) as T
}

export function toJob(row: JobPayload): Job {
  return {
    id: row.id,
    type: row.type,
    slot: row.slot,
    date: row.date,
    publishAt: row.publish_at,
    topic: row.topic,
    status: row.status,
    stillUrl: row.still_url || (row.still_path.startsWith("http") ? row.still_path : ""),
    videoUrl: row.video_url || (row.video_path?.startsWith("http") ? row.video_path : "") || "",
    caption: row.type === "REEL" && row.caption ? formatReelCaption(row.caption) : row.caption,
    audioId: row.audio_id,
    score: row.score,
    attempt: row.attempt,
    maxAttempts: row.max_attempts,
    mustFix: row.must_fix,
    subscores: row.subscores ?? emptySubscores,
    timeline: row.timeline ?? [],
    igMediaId: row.ig_media_id ?? null,
    insights: row.insights ?? null,
    insightsSyncedAt: row.insights_synced_at ?? null,
  }
}

export function toJobPayload(job: Job): JobPayload {
  return {
    id: job.id,
    type: job.type,
    slot: job.slot,
    date: job.date,
    publish_at: job.publishAt,
    topic: job.topic,
    status: job.status,
    still_path: job.stillUrl,
    still_url: job.stillUrl,
    video_url: job.videoUrl,
    caption: job.caption,
    audio_id: job.audioId,
    score: job.score,
    attempt: job.attempt,
    max_attempts: job.maxAttempts,
    must_fix: job.mustFix,
    subscores: job.subscores,
    timeline: job.timeline,
    ig_media_id: job.igMediaId,
    insights: job.insights,
    insights_synced_at: job.insightsSyncedAt,
  }
}

export function getAuthStatus() {
  return request<AuthStatus>("/auth/status")
}

export function getBrandKit() {
  return request<BrandKit>("/brand-kit")
}

export function saveBrandKit(kit: BrandKit) {
  return request<BrandKit>("/brand-kit", {
    method: "PUT",
    body: JSON.stringify(kit),
  })
}

function brandRefId(value: string) {
  const text = value.trim()
  if (!text) return ""
  const match = text.match(/(?:brand-kit\/refs\/|brand\/refs\/)([^/?#]+)/i)
  const raw = match?.[1] ?? (/^ref-[\w-]+(?:\.(?:png|jpe?g|webp))?$/i.test(text) ? text : "")
  return raw.replace(/\.(png|jpe?g|webp)$/i, "")
}

export function refSrc(url: string) {
  if (!url) return ""
  const refId = brandRefId(url)
  if (refId) {
    return `${base}/brand-kit/refs/${refId}`
  }
  if (url.startsWith("http") || url.startsWith("/media") || url.startsWith("blob:")) {
    return url
  }
  if (url.startsWith("/api")) return url
  return `${base}${url.startsWith("/") ? url : `/${url}`}`
}

export function styleRefSrc(ref: { id?: string; url?: string; path?: string }) {
  const refId = brandRefId(ref.path || "") || brandRefId(ref.url || "") || brandRefId(ref.id || "")
  if (refId) {
    return `${base}/brand-kit/refs/${refId}`
  }
  return refSrc(ref.url || "")
}

export async function uploadBrandRef(file: File, id: string, note: string, topic: string) {
  const body = new FormData()
  body.append("file", file)
  body.append("ref_id", id)
  body.append("note", note)
  body.append("topic", topic)
  const response = await fetch(`${base}/brand-kit/refs`, { method: "POST", body })
  if (!response.ok) {
    const detail = await response.text()
    try {
      const payload = JSON.parse(detail) as { detail?: unknown }
      if (typeof payload.detail === "string") {
        throw new Error(payload.detail)
      }
    } catch (exc) {
      if (exc instanceof Error && exc.message !== detail) {
        throw exc
      }
    }
    throw new Error(detail || `API ${response.status}`)
  }
  return (await response.json()) as StyleRef
}

export function deleteBrandRef(id: string) {
  return request<{ ok: boolean }>(`/brand-kit/refs/${id}`, { method: "DELETE" })
}

export async function getTopics() {
  const payload = await request<{ topics: Topic[] }>("/topics")
  return payload.topics
}

export function saveTopic(topic: Topic) {
  return request<Topic>(`/topics/${topic.slug}`, {
    method: "PUT",
    body: JSON.stringify(topic),
  })
}

export async function getTracks() {
  const payload = await request<{ tracks: Track[] }>("/tracks")
  return payload.tracks
}

export function saveTrack(track: Track) {
  return request<Track>(`/tracks/${track.id}`, {
    method: "PUT",
    body: JSON.stringify(track),
  })
}

export function deleteTrack(id: string) {
  return request<{ ok: boolean }>(`/tracks/${id}`, { method: "DELETE" })
}

export function trackFileUrl(id: string) {
  return `${base}/tracks/${id}/file`
}

export async function uploadTrack(file: File, trackId?: string, title?: string, artist?: string) {
  const body = new FormData()
  body.append("file", file)
  if (trackId) body.append("track_id", trackId)
  if (title) body.append("title", title)
  if (artist) body.append("artist", artist)
  const response = await fetch(`${base}/tracks`, { method: "POST", body })
  if (!response.ok) {
    const detail = await response.text()
    try {
      const payload = JSON.parse(detail) as { detail?: unknown }
      if (typeof payload.detail === "string") {
        throw new Error(payload.detail)
      }
    } catch (exc) {
      if (exc instanceof Error && exc.message !== detail) {
        throw exc
      }
    }
    throw new Error(detail || `API ${response.status}`)
  }
  return (await response.json()) as Track
}

export async function getJobs() {
  const payload = await request<{ jobs: JobPayload[] }>("/jobs")
  return payload.jobs.map(toJob)
}

export function saveJob(job: Job) {
  return request<JobPayload>(`/jobs/${job.id}`, {
    method: "PUT",
    body: JSON.stringify(toJobPayload(job)),
  }).then(toJob)
}

export function generateJob(type: Job["type"] = "STORY", date?: string, topic?: string) {
  return request<JobPayload>("/jobs/generate", {
    method: "POST",
    body: JSON.stringify({ type, date, topic }),
  }).then(toJob)
}

export function attachJobAudio(id: string, trackId: string) {
  return request<JobPayload>(`/jobs/${id}/audio`, {
    method: "POST",
    body: JSON.stringify({ track_id: trackId }),
  }).then(toJob)
}

export function publishJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/publish`, { method: "POST" }).then(toJob)
}

export function rejectJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/reject`, { method: "POST" }).then(toJob)
}

export function skipJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/skip`, { method: "POST" }).then(toJob)
}

export function refreshJobInsights(id: string) {
  return request<JobPayload>(`/jobs/${id}/insights`, { method: "POST" }).then(toJob)
}

export function syncInsights() {
  return request<{
    synced: number
    skipped: number
    errors: string[]
    performance_note: string
    weights: Record<string, number>
  }>("/insights/sync", { method: "POST" })
}