import { useState } from 'react'

const SEEN_KEY = 'intro-seen'
// Each step starts when the previous one ends: mascot 0–0.7s, "MyCareer" 0.7–1.25s, "AI" 1.25–1.75s, then a short hold.
const FADE_OUT_AT = '2.6s'

/** Plays once per browser tab; skipped when the user asks for reduced motion. */
function shouldShow() {
  try {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return false
    if (sessionStorage.getItem(SEEN_KEY)) return false
    sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    // Storage blocked (private mode): show it this time.
  }
  return true
}

/** Splash over the app on first open; the page underneath loads meanwhile, so deep links still work. Click to skip. */
export function Intro() {
  const [show, setShow] = useState(shouldShow)
  if (!show) return null

  return (
    <div
      aria-hidden="true"
      onClick={() => setShow(false)}
      // Only the overlay's own fade-out ends the intro, not the children's animations.
      onAnimationEnd={e => e.target === e.currentTarget && setShow(false)}
      className="fixed inset-0 z-50 grid cursor-pointer place-items-center bg-canvas"
      style={{ animation: `intro-out .4s ease-in ${FADE_OUT_AT} forwards` }}
    >
      <div className="flex flex-col items-center gap-4">
        <img src="/mascot.png" alt="" width={112} height={112} style={{ animation: 'intro-fade .7s ease-out both' }} />
        <p className="flex text-3xl font-bold tracking-tight">
          <span style={{ animation: 'intro-slide .55s cubic-bezier(.2,.8,.2,1) .7s both' }}>MyCareer</span>
          {/* The clip hides "AI" below the line, so it looks like it surfaces upwards. */}
          <span className="overflow-hidden">
            <span className="inline-block text-primary" style={{ animation: 'intro-rise .5s cubic-bezier(.2,.8,.2,1) 1.25s both' }}>AI</span>
          </span>
        </p>
      </div>
    </div>
  )
}
