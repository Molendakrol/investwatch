import { createContext, useContext } from 'react'

export const FindingContext = createContext<(id: number) => void>(() => {})

/** Opens the finding detail drawer from anywhere (tables, toasts, charts). */
export const useOpenFinding = () => useContext(FindingContext)
