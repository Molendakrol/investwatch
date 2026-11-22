import { useEffect, useState } from 'react'

const STEPS = [100, 112.5, 125] as const
const KEY = 'iw-text-size'

function readStored(): number {
  try {
    const v = Number(localStorage.getItem(KEY))
    return STEPS.includes(v as (typeof STEPS)[number]) ? STEPS.indexOf(v as (typeof STEPS)[number]) : 0
  } catch {
    return 0
  }
}

/** Accessibility text scaling (A− / A+). All sizes are rem-based, so the whole UI scales. */
export function useTextSize() {
  const [step, setStep] = useState(readStored)

  useEffect(() => {
    document.documentElement.style.fontSize = `${STEPS[step]}%`
    try {
      localStorage.setItem(KEY, String(STEPS[step]))
    } catch {
      /* storage unavailable — scaling still works for this visit */
    }
  }, [step])

  return {
    canDecrease: step > 0,
    canIncrease: step < STEPS.length - 1,
    decrease: () => setStep((s) => Math.max(0, s - 1)),
    increase: () => setStep((s) => Math.min(STEPS.length - 1, s + 1)),
  }
}
