import { useEffect, useMemo, useState } from "react"
import { getTracks } from "../api"
import { CloudIcon, PauseIcon, PlayIcon } from "../components/Icons"
import { TopicPill } from "../components/Pills"
import type { TopicSlug, Track } from "../types"

function toTrack(row: Track): Track {
  return {
    ...row,
    duration: row.duration ?? "",
    last_used: row.last_used ?? null,
    topics: row.topics ?? [],
  }
}

export function AudioPage() {
  const [playing, setPlaying] = useState<string | null>(null)
  const [items, setItems] = useState<Track[]>([])
  const [status, setStatus] = useState("Loading…")

  useEffect(() => {
    getTracks()
      .then((rows) => {
        setItems(rows.map(toTrack))
        setStatus("")
      })
      .catch((exc: unknown) => {
        setItems([])
        setStatus(exc instanceof Error ? exc.message : "Could not load tracks")
      })
  }, [])

  const groups = useMemo(() => {
    const slugs = new Set<TopicSlug>()
    for (const track of items) {
      for (const slug of track.topics) slugs.add(slug)
    }
    return [...slugs]
  }, [items])

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title gold">Audio Library</h1>
        <div className="upload">
          <CloudIcon />
          Drop audio to upload
        </div>
      </div>
      {status ? <p className="page-sub">{status}</p> : null}
      {!status && items.length === 0 ? <p className="page-sub">No tracks yet.</p> : null}
      {groups.map((slug) => {
        const group = items.filter((track) => track.topics.includes(slug))
        return (
          <section key={slug}>
            <div className="group-h">
              <TopicPill topic={slug} />
              <span className="muted-count">{group.length} tracks</span>
            </div>
            {group.map((track) => (
              <div className="track" key={`${slug}-${track.id}`}>
                <button
                  type="button"
                  className="play"
                  aria-label={`Play ${track.title}`}
                  onClick={() => setPlaying(playing === track.id ? null : track.id)}
                >
                  {playing === track.id ? <PauseIcon /> : <PlayIcon />}
                </button>
                <div>
                  <div>{track.title}</div>
                  <div className="track-artist">{track.artist}</div>
                </div>
                <div className="track-meta">
                  <span>{track.duration}</span>
                  <span>{track.last_used ?? "Never"}</span>
                  {track.topics.map((item) => (
                    <TopicPill key={item} topic={item} />
                  ))}
                </div>
              </div>
            ))}
          </section>
        )
      })}
    </div>
  )
}