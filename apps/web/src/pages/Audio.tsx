import { useEffect, useMemo, useRef, useState } from "react"
import { trackFileUrl } from "../api"
import { CloudIcon, PauseIcon, PlayIcon, TrashIcon } from "../components/Icons"
import { topicTitle } from "../lib"
import { useStore } from "../store"
import type { Track } from "../types"

export function AudioPage() {
  const { tracks, topics, busy, uploadAudio, tagTrack, removeTrack } = useStore()
  const [playing, setPlaying] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const attachRef = useRef<HTMLInputElement>(null)
  const targetId = useRef<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    return () => {
      audioRef.current?.pause()
    }
  }, [])

  const sorted = useMemo(
    () => [...tracks].sort((a, b) => a.title.localeCompare(b.title)),
    [tracks],
  )

  async function onFile(file: File | undefined, trackId?: string) {
    if (!file) return
    await uploadAudio(file, trackId)
    targetId.current = null
    if (fileRef.current) fileRef.current.value = ""
    if (attachRef.current) attachRef.current.value = ""
  }

  function pickFile(id: string) {
    targetId.current = id
    attachRef.current?.click()
  }

  async function onDelete(id: string) {
    if (playing === id) {
      audioRef.current?.pause()
      setPlaying(null)
    }
    await removeTrack(id)
  }

  function togglePlay(track: Track) {
    if (!track.path) return
    if (playing === track.id) {
      audioRef.current?.pause()
      setPlaying(null)
      return
    }
    if (!audioRef.current) {
      audioRef.current = new Audio()
      audioRef.current.addEventListener("ended", () => setPlaying(null))
    }
    audioRef.current.src = trackFileUrl(track.id)
    void audioRef.current.play()
    setPlaying(track.id)
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title gold">Audio Library</h1>
        <label
          className="upload"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault()
            void onFile(event.dataTransfer.files[0])
          }}
        >
          <CloudIcon />
          {busy ? "Uploading…" : "Drop audio to upload"}
          <input
            ref={fileRef}
            type="file"
            accept="audio/mpeg,audio/wav,audio/mp4,audio/x-m4a,audio/aac,audio/ogg,audio/flac,.mp3,.wav,.m4a,.aac,.ogg,.flac"
            onChange={(event) => void onFile(event.target.files?.[0])}
          />
        </label>
        <input
          ref={attachRef}
          type="file"
          hidden
          accept="audio/mpeg,audio/wav,audio/mp4,audio/x-m4a,audio/aac,audio/ogg,audio/flac,.mp3,.wav,.m4a,.aac,.ogg,.flac"
          onChange={(event) => void onFile(event.target.files?.[0], targetId.current ?? undefined)}
        />
      </div>
      {!sorted.length ? <p className="page-sub">No tracks yet.</p> : null}
      {sorted.map((track) => {
        const ready = Boolean(track.path)
        return (
          <div className="track" key={track.id}>
            <button
              type="button"
              className="play"
              aria-label={`Play ${track.title}`}
              disabled={!ready}
              onClick={() => togglePlay(track)}
            >
              {playing === track.id ? <PauseIcon /> : <PlayIcon />}
            </button>
            <div>
              <div>{track.title}</div>
              <div className="track-artist">{track.artist}</div>
            </div>
            <div className="track-tags">
              {topics.map((topic) => {
                const on = track.topics.includes(topic.slug)
                return (
                  <button
                    key={topic.slug}
                    type="button"
                    className={`pill ${topic.slug}${on ? "" : " off"}`}
                    aria-pressed={on}
                    onClick={() => void tagTrack(track.id, topic.slug)}
                  >
                    {topicTitle(topic.slug)}
                  </button>
                )
              })}
            </div>
            <div className="track-meta">
              <span>{track.duration}</span>
              <span>{track.last_used ?? "Never"}</span>
              {ready ? null : (
                <button type="button" className="btn" disabled={busy} onClick={() => pickFile(track.id)}>
                  Add file
                </button>
              )}
              <button
                type="button"
                className="btn danger icon-btn"
                disabled={busy}
                aria-label={`Delete ${track.title}`}
                onClick={() => void onDelete(track.id)}
              >
                <TrashIcon />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
