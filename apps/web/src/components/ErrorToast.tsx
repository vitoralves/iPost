import { useEffect } from "react"
import { CloseIcon, WarnIcon } from "./Icons"

type Props = {
  message: string
  seq: number
  onDismiss: () => void
}

export function ErrorToast({ message, seq, onDismiss }: Props) {
  useEffect(() => {
    if (!message) return
    const timer = window.setTimeout(onDismiss, 7000)
    return () => window.clearTimeout(timer)
  }, [message, seq, onDismiss])

  if (!message) return null

  return (
    <div className="error-toast" role="alert" aria-live="assertive">
      <WarnIcon size={16} />
      <p>{message}</p>
      <button type="button" className="error-toast-close" aria-label="Dismiss" onClick={onDismiss}>
        <CloseIcon />
      </button>
    </div>
  )
}
