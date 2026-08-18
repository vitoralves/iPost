import { useEffect, useRef, useState } from "react"
import {
  deleteBrandRef,
  getBrandKit,
  refSrc,
  saveBrandKit,
  uploadBrandRef,
} from "../api"
import { PlusIcon } from "../components/Icons"
import type { BrandKit, StyleRef } from "../types"

function emptyRef(): StyleRef {
  return { id: `ref-${crypto.randomUUID().slice(0, 8)}`, url: "", path: "", note: "" }
}

export function BrandKitPage() {
  const [kit, setKit] = useState<BrandKit | null>(null)
  const [status, setStatus] = useState("")
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const targetId = useRef<string | null>(null)

  useEffect(() => {
    getBrandKit()
      .then((loaded) => {
        setKit(loaded)
        setStatus("")
      })
      .catch((exc: unknown) => {
        setKit(null)
        setStatus(exc instanceof Error ? exc.message : "Could not load brand kit")
      })
  }, [])

  function pickFile(id: string) {
    targetId.current = id
    fileRef.current?.click()
  }

  async function onFile(file: File | undefined) {
    if (!file || !kit) return
    const id = targetId.current ?? emptyRef().id
    setUploading(id)
    try {
      const current = kit.refs.find((item) => item.id === id)
      const uploaded = await uploadBrandRef(file, id, current?.note ?? "")
      const exists = kit.refs.some((item) => item.id === uploaded.id)
      setKit({
        ...kit,
        refs: exists
          ? kit.refs.map((item) => (item.id === uploaded.id ? uploaded : item))
          : [...kit.refs, uploaded],
      })
      setStatus("Image uploaded. Save to keep notes and voice.")
    } catch (exc: unknown) {
      setStatus(exc instanceof Error ? exc.message : "Could not upload image")
    } finally {
      setUploading(null)
      targetId.current = null
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  async function onRemove(id: string) {
    if (!kit) return
    try {
      await deleteBrandRef(id)
      setKit({ ...kit, refs: kit.refs.filter((item) => item.id !== id) })
    } catch (exc: unknown) {
      setStatus(exc instanceof Error ? exc.message : "Could not remove image")
    }
  }

  async function onSave() {
    if (!kit) return
    setSaving(true)
    try {
      const saved = await saveBrandKit({
        ...kit,
        banned: kit.banned.map((item) => item.trim()).filter(Boolean),
        refs: kit.refs.filter((item) => item.url.trim() || item.path),
      })
      setKit(saved)
      setStatus("Saved. Next generate uses this kit.")
    } catch (exc: unknown) {
      setStatus(exc instanceof Error ? exc.message : "Could not save brand kit")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Brand Kit</h1>
          <p className="page-sub">
            Style references, voice, and content guardrails used by the generation agents.
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
          <div className="field-label">Style references</div>
          <div className="grid-refs">
            {kit.refs.map((ref, index) => (
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
                <input
                  className="field-box"
                  value={ref.note}
                  placeholder="Note for the creator"
                  onChange={(event) =>
                    setKit({
                      ...kit,
                      refs: kit.refs.map((item, itemIndex) =>
                        itemIndex === index ? { ...item, note: event.target.value } : item,
                      ),
                    })
                  }
                />
                <button type="button" className="ref-remove" onClick={() => void onRemove(ref.id)}>
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              className="add-ref"
              disabled={Boolean(uploading)}
              onClick={() => {
                const next = emptyRef()
                setKit({ ...kit, refs: [...kit.refs, next] })
                pickFile(next.id)
              }}
            >
              <PlusIcon />
              Add ref
            </button>
          </div>
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