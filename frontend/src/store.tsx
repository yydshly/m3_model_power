import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getRegistry, type Registry } from './api'

type Ctx = {
  registry: Registry | null
  error: string | null
  reload: () => void
}

const RegistryCtx = createContext<Ctx>({ registry: null, error: null, reload: () => {} })

export function RegistryProvider({ children }: { children: ReactNode }) {
  const [registry, setRegistry] = useState<Registry | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    setError(null)
    getRegistry()
      .then(setRegistry)
      .catch((e) => setError(String(e)))
  }, [nonce])

  return (
    <RegistryCtx.Provider value={{ registry, error, reload: () => setNonce((n) => n + 1) }}>
      {children}
    </RegistryCtx.Provider>
  )
}

export function useRegistry() {
  return useContext(RegistryCtx)
}
