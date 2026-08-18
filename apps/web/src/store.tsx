import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import {
  attachJobAudio,
  deleteTrack,
  generateJob,
  getJobs,
  getTopics,
  getTracks,
  publishJob,
  rejectJob,
  skipJob,
  saveTopic,
  saveTrack,
  uploadTrack,
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
    path: row.path ?? "",
  }
}

type Store = {
  jobs: Job[]
  topics: Topic[]
  tracks: Track[]
  loading: boolean
  busy: boolean
  error: string
  errorSeq: number
  notifyError: (message: string) => void
  clearError: () => void
  trackById: (id: string | null) => Track | null
  generateStory: (date?: string, topic?: string) => Promise<Job | undefined>
  generateReel: (date?: string, topic?: string) => Promise<Job | undefined>
  attachAudio: (id: string, trackId: string) => Promise<Job | undefined>
  refreshTracks: () => Promise<void>
  uploadAudio: (file: File, trackId?: string) => Promise<Track | undefined>
  tagTrack: (id: string, slug: TopicSlug) => Promise<void>
  removeTrack: (id: string) => Promise<void>
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
  const [errorSeq, setErrorSeq] = useState(0)

  const notifyError = useCallback((message: string) => {
    setError(message)
    setErrorSeq((value) => value + 1)
  }, [])

  const clearError = useCallback(() => {
    setError("")
  }, [])

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
        notifyError(exc instanceof Error ? exc.message : "API unavailable")
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
        notifyError(exc instanceof Error ? exc.message : "Request failed")
        return undefined
      } finally {
        setBusy(false)
      }
    }

    async function refreshLibrary() {
      const [nextTracks, nextTopics] = await Promise.all([getTracks(), getTopics()])
      setTracks(nextTracks.map(toTrack))
      setTopics(nextTopics.map(toTopic))
    }

    return {
      jobs,
      topics,
      tracks,
      loading,
      busy,
      error,
      errorSeq,
      notifyError,
      clearError,
      trackById(id) {
        if (!id) return null
        return tracks.find((item) => item.id === id) ?? null
      },
      generateStory(date, topic) {
        return run(() => generateJob("STORY", date ?? todayISO(), topic))
      },
      generateReel(date, topic) {
        return run(() => generateJob("REEL", date ?? todayISO(), topic))
      },
      attachAudio(id, trackId) {
        return run(async () => {
          const job = await attachJobAudio(id, trackId)
          await refreshLibrary()
          return job
        })
      },
      async refreshTracks() {
        try {
          await refreshLibrary()
        } catch (exc: unknown) {
          notifyError(exc instanceof Error ? exc.message : "Could not load tracks")
        }
      },
      async uploadAudio(file, trackId) {
        setBusy(true)
        try {
          const track = await uploadTrack(file, trackId)
          await refreshLibrary()
          setError("")
          return track
        } catch (exc: unknown) {
          notifyError(exc instanceof Error ? exc.message : "Could not upload audio")
          return undefined
        } finally {
          setBusy(false)
        }
      },
      async tagTrack(id, slug) {
        const current = tracks.find((item) => item.id === id)
        if (!current) return
        const topicsForTrack = current.topics.includes(slug)
          ? current.topics.filter((item) => item !== slug)
          : [...current.topics, slug]
        const next = { ...current, topics: topicsForTrack }
        setTracks((prev) => prev.map((item) => (item.id === id ? next : item)))
        try {
          await saveTrack(next)
          const nextTopics = await getTopics()
          setTopics(nextTopics.map(toTopic))
        } catch (exc: unknown) {
          notifyError(exc instanceof Error ? exc.message : "Could not tag track")
          await refreshLibrary().catch(() => undefined)
        }
      },
      async removeTrack(id) {
        setBusy(true)
        try {
          await deleteTrack(id)
          await refreshLibrary()
          setError("")
        } catch (exc: unknown) {
          notifyError(exc instanceof Error ? exc.message : "Could not delete track")
        } finally {
          setBusy(false)
        }
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
          notifyError(exc instanceof Error ? exc.message : "Could not save topic")
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
          notifyError(exc instanceof Error ? exc.message : "Could not save topic")
        })
      },
    }
  }, [busy, error, errorSeq, jobs, loading, notifyError, clearError, topics, tracks])

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  const store = useContext(StoreContext)
  if (!store) {
    throw new Error("useStore must be used within StoreProvider")
  }
  return store
}
