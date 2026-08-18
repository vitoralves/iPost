import { useEffect, useRef, useState } from "react"
import {
  deleteBrandRef,
  getBrandKit,
  refSrc,
  saveBrandKit,
  uploadBrandRef,
} from "../api"
import { PlusIcon } from "../components/Icons"
import { TopicPill } from "../components/Pills"
import { topicTitle } from "../lib"
import { useStore } from "../store"
import type { BrandKit, StyleRef } from "../types"

function emptyRef(topic: string): StyleRef {
  return { id: `ref-${crypto.randomUUID().slice(0, 8)}`, url: "", path: "", note: "", topic }
}

export function BrandKitPage() {
  const { topics, notifyError } = useStore()
  const [kit, setKit] = useState<BrandKit | null>(null)
  const [status, setStatus] = useState("")
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const targetId = useRef<string | null>(null)

  useEffect(() => {
    getBrandKit()
      .then((loaded) => {
        setKit({
          ...loaded,
          refs: loaded.refs.map((ref) => ({ ...ref, topic: ref.topic ?? "" })),
        })
        setStatus("")
      })
      .catch((exc: unknown) => {
        setKit(null)
        notifyError(exc instanceof Error ? exc.message : "Could not load brand kit")
      })
  }, [notifyError])

  function pickFile(id: string) {
    targetId.current = id
    fileRef.current?.click()
  }

  async function onFile(file: File | undefined) {
    if (!file || !kit) return
    const id = targetId.current ?? emptyRef("").id
    const current = kit.refs.find((item) => item.id === id)
    const topic = current?.topic ?? ""
    if (!topic) {
      notifyError("Pick a topic before uploading a style ref.")
      targetId.current = null
      if (fileRef.current) fileRef.current.value = ""
      return
    }
    setUploading(id)
    try {
      const uploaded = await uploadBrandRef(file, id, current?.note ?? "", topic)
      const exists = kit.refs.some((item) => item.id === uploaded.id)
      setKit({
        ...kit,
        refs: exists
          ? kit.refs.map((item) => (item.id === uploaded.id ? uploaded : item))
          : [...kit.refs, uploaded],
      })
      setStatus("Image uploaded. Save to keep notes and voice.")
    } catch (exc: unknown) {
      notifyError(exc instanceof Error ? exc.message : "Could not upload image")
    } finally {
      setUploading(null)
      targetId.current = null
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  function setRef(id: string, patch: Partial<StyleRef>) {
    if (!kit) return
    setKit({
      ...kit,
      refs: kit.refs.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    })
  }

  async function onRemove(id: string) {
    if (!kit) return
    try {
      await deleteBrandRef(id)
      setKit({ ...kit, refs: kit.refs.filter((item) => item.id !== id) })
    } catch (exc: unknown) {
      notifyError(exc instanceof Error ? exc.message : "Could not remove image")
    }
  }

  async function onSave() {
    if (!kit) return
    const missing = kit.refs.filter((item) => (item.url.trim() || item.path) && !item.topic)
    if (missing.length) {
      notifyError("Every style ref needs a topic.")
      return
    }
    setSaving(true)
    try {
      const saved = await saveBrandKit({
        ...kit,
        banned: kit.banned.map((item) => item.trim()).filter(Boolean),
        refs: kit.refs.filter((item) => item.url.trim() || item.path),
      })
      setKit(saved)
      setStatus("Saved. Next generate uses refs for that topic only.")
    } catch (exc: unknown) {
      notifyError(exc instanceof Error ? exc.message : "Could not save brand kit")
    } finally {
      setSaving(false)
    }
  }

  const unassigned = kit?.refs.filter((item) => !item.topic) ?? []
  const groups = [
    ...topics.map((topic) => ({
      slug: topic.slug,
      name: topic.name,
      refs: kit?.refs.filter((item) => item.topic === topic.slug) ?? [],
    })),
    ...(unassigned.length
      ? [{ slug: "", name: "Unassigned", refs: unassigned }]
      : []),
  ]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Brand Kit</h1>
          <p className="page-sub">
            Style references are used only when generating that topic. Voice and
            guardrails apply to every post.
          </p>
        </div>
        <button type="button" className="btn primary" onClick={onSave} disabled={saving || !kit}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
      {status ? <p className="page-sub">{status}</p> : null}
      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(event) => void onFile(event.target.files?.[0])}
      />
      {!kit ? null : (
        <>
          <div className="field-label">Style references by topic</div>
          {groups.map((group) => (
            <section key={group.slug || "unassigned"}>
              <div className="group-h">
                {group.slug ? <TopicPill topic={group.slug} /> : <span>{group.name}</span>}
                <span className="muted-count">{group.refs.length}</span>
              </div>
              <div className="grid-refs">
                {group.refs.map((ref) => (
                  <div className="ref-card" key={ref.id}>
                    <button
                      type="button"
                      className={ref.url ? "ref-media" : "add-ref"}
                      disabled={uploading === ref.id}
                      onClick={() => pickFile(ref.id)}
                    >
                      {ref.url ? (
                        <img src={refSrc(ref.url)} alt="" />
                      ) : (
                        <>
                          <PlusIcon />
                          {uploading === ref.id ? "Uploading…" : "Upload image"}
                        </>
                      )}
                    </button>
                    <select
                      className="field-box"
                      value={ref.topic}
                      onChange={(event) => setRef(ref.id, { topic: event.target.value })}
                    >
                      <option value="">Topic</option>
                      {topics.map((topic) => (
                        <option key={topic.slug} value={topic.slug}>
                          {topicTitle(topic.slug)}
                        </option>
                      ))}
                    </select>
                    <input
                      className="field-box"
                      value={ref.note}
                      placeholder="Note for the creator"
                      onChange={(event) => setRef(ref.id, { note: event.target.value })}
                    />
                    <button type="button" className="ref-remove" onClick={() => void onRemove(ref.id)}>
                      Remove
                    </button>
                  </div>
                ))}
                {group.slug ? (
                  <button
                    type="button"
                    className="add-ref"
                    disabled={Boolean(uploading)}
                    onClick={() => {
                      const next = emptyRef(group.slug)
                      setKit({ ...kit, refs: [...kit.refs, next] })
                      pickFile(next.id)
                    }}
                  >
                    <PlusIcon />
                    Add {topicTitle(group.slug)} ref
                  </button>
                ) : null}
              </div>
            </section>
          ))}
          <div className="split">
            <div>
              <div className="field-label gold">Voice & tone</div>
              <textarea
                className="field-box"
                rows={8}
                value={kit.voice_tone}
                onChange={(event) => setKit({ ...kit, voice_tone: event.target.value })}
              />
            </div>
            <div>
              <div className="field-label gold">Banned topics</div>
              <textarea
                className="field-box"
                rows={8}
                value={kit.banned.join("\n")}
                onChange={(event) =>
                  setKit({ ...kit, banned: event.target.value.split("\n") })
                }
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
