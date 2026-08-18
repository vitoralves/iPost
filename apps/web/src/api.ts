import type { AuthStatus, BrandKit, Job, JobPayload, StyleRef, Topic, Track } from "./types"

const base = import.meta.env.VITE_API_URL ?? "/api"

const emptySubscores = {
  brand: 0,
  clarity: 0,
  spec: 0,
  originality: 0,
  safety: 0,
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
    caption: row.caption,
    audioId: row.audio_id,
    score: row.score,
    attempt: row.attempt,
    maxAttempts: row.max_attempts,
    mustFix: row.must_fix,
    subscores: row.subscores ?? emptySubscores,
    timeline: row.timeline ?? [],
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
    caption: job.caption,
    audio_id: job.audioId,
    score: job.score,
    attempt: job.attempt,
    max_attempts: job.maxAttempts,
    must_fix: job.mustFix,
    subscores: job.subscores,
    timeline: job.timeline,
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

export function refSrc(url: string) {
  if (url.startsWith("http") || url.startsWith("/media") || url.startsWith("blob:")) {
    return url
  }
  if (url.startsWith("/api")) return url
  return `${base}${url.startsWith("/") ? url : `/${url}`}`
}

export async function uploadBrandRef(file: File, id: string, note: string) {
  const body = new FormData()
  body.append("file", file)
  body.append("ref_id", id)
  body.append("note", note)
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

export function publishJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/publish`, { method: "POST" }).then(toJob)
}

export function rejectJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/reject`, { method: "POST" }).then(toJob)
}

export function skipJob(id: string) {
  return request<JobPayload>(`/jobs/${id}/skip`, { method: "POST" }).then(toJob)
}