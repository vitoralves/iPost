import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import {
  generateJob,
  getJobs,
  getTopics,
  getTracks,
  publishJob,
  rejectJob,
  skipJob,
  saveTopic,
} from "./api"
import { todayISO } from "./lib"
import type { Job, Topic, TopicSlug, Track } from "./types"

function toTopic(row: Topic): Topic {
  return {
    ...row,
    audio_ids: row.audio_ids ?? [],
    refs: row.refs ?? [],
    last_used: row.last_used ?? null,
  }
}

function toTrack(row: Track): Track {
  return {
    ...row,
    duration: row.duration ?? "",
    last_used: row.last_used ?? null,
    topics: row.topics ?? [],
  }
}

type Store = {
  jobs: Job[]
  topics: Topic[]
  tracks: Track[]
  loading: boolean
  busy: boolean
  error: string
  trackById: (id: string | null) => Track | null
  generateStory: (date?: string, topic?: string) => Promise<Job | undefined>
  publishStory: (id: string) => Promise<Job | undefined>
  rejectStory: (id: string) => Promise<Job | undefined>
  skipStory: (id: string) => Promise<Job | undefined>
  toggleTopic: (slug: TopicSlug) => void
  addTopic: (name: string) => void
}

const StoreContext = createContext<Store | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [topics, setTopics] = useState<Topic[]>([])
  const [tracks, setTracks] = useState<Track[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([getJobs(), getTopics(), getTracks()])
      .then(([nextJobs, nextTopics, nextTracks]) => {
        if (cancelled) return
        setJobs(nextJobs)
        setTopics(nextTopics.map(toTopic))
        setTracks(nextTracks.map(toTrack))
        setError("")
      })
      .catch((exc: unknown) => {
        if (cancelled) return
        setJobs([])
        setTopics([])
        setTracks([])
        setError(exc instanceof Error ? exc.message : "API unavailable")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo<Store>(() => {
    function replaceJob(next: Job) {
      setJobs((prev) => {
        const without = prev.filter(
          (item) => !(item.date === next.date && item.type === next.type && item.id !== next.id),
        )
        return [next, ...without.filter((item) => item.id !== next.id)]
      })
    }

    async function run(action: () => Promise<Job>) {
      setBusy(true)
      try {
        const job = await action()
        replaceJob(job)
        setError("")
        return job
      } catch (exc: unknown) {
        setError(exc instanceof Error ? exc.message : "Request failed")
        return undefined
      } finally {
        setBusy(false)
      }
    }

    return {
      jobs,
      topics,
      tracks,
      loading,
      busy,
      error,
      trackById(id) {
        if (!id) return null
        return tracks.find((item) => item.id === id) ?? null
      },
      generateStory(date, topic) {
        return run(() => generateJob("STORY", date ?? todayISO(), topic))
      },
      publishStory(id) {
        return run(() => publishJob(id))
      },
      rejectStory(id) {
        return run(() => rejectJob(id))
      },
      skipStory(id) {
        return run(() => skipJob(id))
      },
      toggleTopic(slug) {
        const current = topics.find((item) => item.slug === slug)
        if (!current) return
        const next = { ...current, enabled: !current.enabled }
        setTopics((prev) => prev.map((item) => (item.slug === slug ? next : item)))
        saveTopic(next).catch((exc: unknown) => {
          setError(exc instanceof Error ? exc.message : "Could not save topic")
        })
      },
      addTopic(name) {
        const slug = name.trim().toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")
        if (!slug || topics.some((item) => item.slug === slug)) return
        const next: Topic = {
          slug,
          name: name.trim(),
          last_used: null,
          weight: 10,
          audio_ids: [],
          enabled: true,
          refs: [],
        }
        setTopics((prev) => [...prev, next])
        saveTopic(next).catch((exc: unknown) => {
          setError(exc instanceof Error ? exc.message : "Could not save topic")
        })
      },
    }
  }, [busy, error, jobs, loading, topics, tracks])

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  const store = useContext(StoreContext)
  if (!store) {
    throw new Error("useStore must be used within StoreProvider")
  }
  return store
}