import { useEffect, useState } from 'react'
import type { Model } from '../api'

/**
 * Keeps the selected model id in sync with the available models list.
 *
 * Rules:
 * - If models list is empty → clear selection.
 * - If current selection is still in the list → keep it (user's choice).
 * - Otherwise → default to models[0].id (first available).
 *
 * Does NOT override a user's manual selection as long as that model
 * is still present in the list.
 */
export function useSyncedModelSelection(models: Model[]) {
  const [model, setModel] = useState('')

  useEffect(() => {
    if (models.length === 0) {
      setModel('')
      return
    }

    setModel((current) => {
      if (current && models.some((m) => m.id === current)) return current
      return models[0].id
    })
  }, [models])

  return { model, setModel }
}
