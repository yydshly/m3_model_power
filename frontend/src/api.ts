export type HealthResp = {
  backend: string
  base_url: string
  group_id_tail: string
  api_key_configured: boolean
  minimax?: 'ok' | 'error' | 'no_key'
  model_count?: number
  error?: string
  status?: number
}

export type CapabilityStatus = 'implemented' | 'planned' | 'unsupported'

export type Category = {
  id: string
  label: string
  emoji: string
  desc: string
  order: number
}

export type Capability = {
  id: string
  category: string
  label: string
  desc: string
  doc_url: string
  method: string
  mm_path: string
  status: CapabilityStatus
  streaming: boolean
  async_job: boolean
  multipart: boolean
  model_family: string | null
  tags: string[]
  example: Record<string, unknown>
  notes: string
  cost_level: 'none' | 'quota' | 'low' | 'medium' | 'high'
  cost_note: string
  has_handler: boolean
}

export type Model = {
  id: string
  label: string
  family: string
  tier: 'flagship' | 'highspeed' | 'standard' | 'hd' | 'turbo' | 'legacy' | 'deprecated'
  official_current: boolean
  live_available: boolean | null
  subscription_expected: boolean | null
  enabled: boolean
  context: number | null
  input_modalities: string[]
  output_modalities: string[]
  protocols: string[]
  capabilities: string[]
  supports_tools: boolean
  supports_thinking: boolean
  thinking_can_disable: boolean
  cost_level: 'quota' | 'low' | 'medium' | 'high' | 'unknown'
  discovery_method: 'models_api' | 'capability_probe' | 'manual_official' | null
  discovery_status: 'available' | 'unavailable' | 'not_applicable' | 'unknown' | null
  discovery_note: string
  note: string
  quota_eligible: boolean
}

export type Registry = {
  categories: Category[]
  capabilities: Capability[]
  models: Model[]
}

export async function getHealth(): Promise<HealthResp> {
  const r = await fetch('/api/health')
  if (!r.ok) throw new Error(`health ${r.status}`)
  return r.json()
}

export async function getRegistry(): Promise<Registry> {
  const r = await fetch('/api/registry')
  if (!r.ok) throw new Error(`registry ${r.status}`)
  return r.json()
}

export async function getModelsFor(capId: string): Promise<Model[]> {
  const r = await fetch(`/api/registry/capabilities/${capId}/models`)
  if (!r.ok) throw new Error(`models ${r.status}`)
  return r.json()
}

export type InvokeResult = { ok: true; data: unknown } | { error: string; message: string; status?: number }

export async function invoke(capId: string, payload: Record<string, unknown>): Promise<InvokeResult> {
  const r = await fetch(`/api/invoke/${capId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) return { error: data.error ?? 'http_error', message: data.message ?? `HTTP ${r.status}`, status: r.status }
  return data
}

export async function uploadCapability(capId: string, file: File, purpose?: string): Promise<InvokeResult> {
  const fd = new FormData()
  fd.append('file', file)
  if (purpose) fd.append('purpose', purpose)
  const r = await fetch(`/api/upload/${capId}`, { method: 'POST', body: fd })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) return { error: data.error ?? 'http_error', message: data.message ?? `HTTP ${r.status}`, status: r.status }
  return data
}

/** 流式调用：返回 Response，调用方自己读 body。 */
export async function streamInvoke(capId: string, payload: Record<string, unknown>): Promise<Response> {
  return fetch(`/api/stream/${capId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
