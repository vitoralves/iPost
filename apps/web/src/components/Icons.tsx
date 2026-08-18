type IconProps = {
  size?: number
}

export function WarnIcon({ size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 3.2 2.2 20.2A1.2 1.2 0 0 0 3.2 22h17.6a1.2 1.2 0 0 0 1-1.8L12 3.2Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M12 9.5v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="17.4" r="1" fill="currentColor" />
    </svg>
  )
}

export function PlayIcon({ size = 12 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5.5v13l11-6.5L8 5.5Z" />
    </svg>
  )
}

export function PauseIcon({ size = 12 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="6" y="5" width="4" height="14" rx="1" />
      <rect x="14" y="5" width="4" height="14" rx="1" />
    </svg>
  )
}

export function PlusIcon({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

export function CloudIcon({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M7 18h10.5A3.5 3.5 0 0 0 21 14.6c0-1.7-1.2-3.1-2.8-3.4A5 5 0 0 0 8.4 9.2 3.8 3.8 0 0 0 7 18Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M12 11.5v6M12 17.5l-2.2-2.2M12 17.5l2.2-2.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function ChevronLeft({ size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M15 5 8 12l7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function ImageOffIcon({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="m5 17 5-5 3 3 2-2 4 4M4 4l16 16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
