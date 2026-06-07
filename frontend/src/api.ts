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

export type ScopeLevel = 'in_scope' | 'warning_only' | 'out_of_scope'

export type VerificationAction = 'verify' | 'show_warning_only' | 'exclude'

export interface ScopePolicy {
  current_scope: ScopeLevel
  scope_reason: string
  count_in_completion_rate: boolean
  count_in_gap_matrix: boolean
  default_verification_action: VerificationAction
}

export type CapabilityStatus = 'implemented' | 'planned' | 'unsupported'

export type BillingCategory =
  | 'normal_token_plan_test'
  | 'quota_sensitive'
  | 'paid_confirm_required'
  | 'high_cost_confirm_required'
  | 'asset_required_confirm_required'

export type BillingPolicy = {
  billing_category: BillingCategory
  requires_explicit_confirmation: boolean
  may_charge_extra: boolean
  consumes_token_plan_quota: boolean
  requires_certification: boolean
  requires_uploaded_asset: boolean
  billing_note: string
  official_pricing_note: string
}

export type OperationRisk =
  | 'normal'
  | 'destructive'
  | 'asset_required'
  | 'existing_task_only'
  | 'long_running'
  | 'quota_guarded'

export interface OperationPolicy {
  operation_risk: OperationRisk
  requires_operation_confirmation: boolean
  requires_uploaded_asset: boolean
  requires_existing_task: boolean
  is_destructive: boolean
  is_long_running: boolean
  max_default_chars?: number | null
  requires_confirmation_above_chars?: number | null
  hard_block_above_chars_without_confirm?: number | null
  operation_note?: string | null
}

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
  requires_model: boolean
  tags: string[]
  example: Record<string, unknown>
  notes: string
  cost_level: 'none' | 'quota' | 'low' | 'medium' | 'high'
  cost_note: string
  has_handler: boolean
  billing_policy: BillingPolicy
  operation_policy: OperationPolicy
  scope_policy: ScopePolicy
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
  /** probe_status reflects the latest model-level probe result:
   * - 'success': probe passed
   * - 'failed': HTTP error or base_resp error (non-1004)
   * - 'probe_assertion_failed': HTTP 200 but output format mismatch (e.g., thinking block)
   * - 'parser_mismatch': HTTP 200 but parser couldn't recognize output structure
   * - 'http_success_but_output_missing': HTTP 200 but no valid output
   * - 'auth_or_token_mismatch': HTTP 200 but base_resp.status_code=1004 (Token/鉴权问题，非模型不可用)
   * - 'token_plan_required': Native 多模态需 TokenPlan Key，当前 API Key 不支持
   * - 'api_key_required': 能力需按量 API Key，TokenPlan Key 不支持
   * - 'both_keys_failed': 两类 Key 均未通过，账户权限或区域问题
   * - 'high_cost_pending': high-cost capability not executed
   * - 'not_probed': no probe performed yet
   * - null: unknown / not applicable
   */
  probe_status: 'success' | 'failed' | 'probe_assertion_failed' | 'parser_mismatch' | 'http_success_but_output_missing' | 'auth_or_token_mismatch' | 'token_plan_required' | 'api_key_required' | 'both_keys_failed' | 'high_cost_pending' | 'not_probed' | null
  /** raw_http_success indicates if the last probe returned HTTP 200, regardless of content */
  raw_http_success: boolean | null
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

export type InvokeResult = { ok: true; data: unknown } | { error: string; message: string; status?: number; blocked_reasons?: string[]; required_confirmations?: string[]; warnings?: string[] }

export async function invoke(
  capId: string,
  payload: Record<string, unknown>,
  confirmations?: Record<string, boolean>,
): Promise<InvokeResult> {
  const body: Record<string, unknown> = { payload }
  if (confirmations) body.confirmations = confirmations
  const r = await fetch(`/api/invoke/${capId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) return { error: data.error ?? 'http_error', message: data.message ?? `HTTP ${r.status}`, status: r.status, blocked_reasons: data.blocked_reasons, required_confirmations: data.required_confirmations, warnings: data.warnings }
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

export type RiskCheckResult = {
  allowed: boolean
  blocked_reasons: string[]
  required_confirmations: string[]
  warnings: string[]
}

export async function riskCheck(
  capId: string,
  payload: Record<string, unknown>,
  confirmations: Record<string, boolean>,
): Promise<RiskCheckResult> {
  const r = await fetch(`/api/capabilities/${capId}/risk-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload, confirmations }),
  })
  if (!r.ok) {
    const data = await r.json().catch(() => ({}))
    throw new Error(data.message ?? `risk-check ${r.status}`)
  }
  return r.json()
}

// ── Verification index ───────────────────────────────────────────────

export type VerificationSummary = {
  in_scope_total: number
  in_scope_verified: number
  in_scope_unverified: number
  in_scope_unverified_ids: string[]
  completion_rate: number
}

export type VerificationIndex = {
  schema_version: number
  updated_at: string
  updated_by: string
  capabilities: Record<string, {
    capability_id: string
    best_status: string
    verified: boolean
    last_success: string | null
    last_failure: string | null
    source: string
    evidence: Record<string, unknown>
  }>
}

export async function getVerificationSummary(): Promise<VerificationSummary> {
  const r = await fetch('/api/verification/summary')
  if (!r.ok) throw new Error(`verification summary ${r.status}`)
  return r.json()
}

export async function getVerificationIndex(): Promise<VerificationIndex> {
  const r = await fetch('/api/verification/index')
  if (!r.ok) throw new Error(`verification index ${r.status}`)
  return r.json()
}

// ── Test Console History ──────────────────────────────────────────────

export type TestConsoleHistoryItem = {
  id: string
  created_at: string
  action: 'risk_check' | 'invoke'
  capability_id: string
  payload_summary: {
    payload_keys: string[]
    payload_size_chars: number
    payload_preview: string
  }
  confirmations: Record<string, boolean>
  result: {
    ok?: boolean
    allowed?: boolean
    status?: number | null
    error?: string | null
    blocked_reasons?: string[]
    required_confirmations?: string[]
    warnings?: string[]
  }
}

export async function getTestConsoleHistory(limit = 50): Promise<{ items: TestConsoleHistoryItem[] }> {
  const r = await fetch(`/api/history/test-console?limit=${limit}`)
  if (!r.ok) throw new Error(`history ${r.status}`)
  return r.json()
}

// ── Capability Descriptions ────────────────────────────────────────────

export type CapabilityDescription = {
  summary: string
  use_cases: string[]
  not_recommended_for: string[]
  input_notes: string[]
  output_notes: string[]
  risk_notes: string[]
  billing_notes: string[]
  common_errors: string[]
  product_usage: string[]
  integration_tips: string[]
}

export type CapabilityDescriptionsResponse = {
  schema_version: number
  updated_at?: string
  descriptions: Record<string, CapabilityDescription>
}

export async function getCapabilityDescriptions(): Promise<CapabilityDescriptionsResponse> {
  const r = await fetch('/api/descriptions/capabilities')
  if (!r.ok) throw new Error(`descriptions ${r.status}`)
  return r.json()
}

// ── Capability Profiles ────────────────────────────────────────────────

export type CapabilityProfile = {
  family: string
  label: string
  user_summary: string
  token_plan_status: string
  api_status: string
  verified_capabilities: string[]
  direct_testable_capabilities: string[]
  guarded_capabilities: string[]
  not_default_executable: string[]
  model_notes: Array<{
    model: string
    label: string
    source: 'official_docs' | 'token_plan_verified' | 'local_config' | 'historical_compat' | 'risk_warning'
    recommendation_level:
      | 'official_primary'
      | 'official_current'
      | 'verified_stable'
      | 'low_latency'
      | 'high_quality'
      | 'quota_friendly'
      | 'compatible'
      | 'guarded'
      | 'free_tier'
      | 'not_default'
      | 'not_applicable'
    token_plan_status?: string
    verified_status?: string
    best_for: string[]
    not_best_for?: string[]
    notes: string
  }>
  capability_modes: Array<{
    capability_id: string
    mode?: string
    protocol?: string
    description: string
    action?: string
    risk_level: string
    streaming?: boolean
  }>
  key_parameters: Array<{ name: string; description: string }>
  outputs: string[]
  recommended_scenarios: string[]
  recommended_workflows: string[]
  risk_notes: string[]
  product_usage: string[]
}

export async function getProfiles(): Promise<{ schema_version: number; profiles: Record<string, CapabilityProfile> }> {
  const r = await fetch('/api/profiles')
  if (!r.ok) throw new Error(`profiles ${r.status}`)
  return r.json()
}

export async function getProfile(family: string): Promise<{ family: string; profile: CapabilityProfile | null }> {
  const r = await fetch(`/api/profiles/${family}`)
  if (!r.ok) throw new Error(`profile ${r.status}`)
  return r.json()
}

// ── Capability Workflows ────────────────────────────────────────────────

export type WorkflowStep = {
  step_id: string
  label: string
  type: 'capability' | 'parameter' | 'result' | 'loop'
  capability_id?: string
  action?: string
  input: string
  output: string
  next_usage?: string
  risk_level: string
}

export type CapabilityWorkflow = {
  id: string
  label: string
  family: string
  summary: string
  steps: WorkflowStep[]
  default_inputs: Record<string, unknown>
  risk_policy: {
    allow_direct: string[]
    guarded: string[]
    blocked: string[]
  }
  expected_outputs: string[]
  product_usage: string[]
}

export async function getWorkflows(): Promise<{ schema_version: number; workflows: Record<string, CapabilityWorkflow> }> {
  const r = await fetch('/api/workflows')
  if (!r.ok) throw new Error(`workflows ${r.status}`)
  return r.json()
}

export async function getWorkflow(workflowId: string): Promise<{ id: string; workflow: CapabilityWorkflow | null }> {
  const r = await fetch(`/api/workflows/${workflowId}`)
  if (!r.ok) throw new Error(`workflow ${r.status}`)
  return r.json()
}

// ── Capability Scenarios ────────────────────────────────────────────────

export type CapabilityScenario = {
  id: string
  label: string
  summary: string
  recommended_for: string[]
  capability_family: string
  workflow_id: string
  capabilities: string[]
  recommended_models: Array<{ model: string; reason: string }>
  risk_level: string
  expected_output: string
  default_inputs: Record<string, unknown>
  cta: string
}

export async function getScenarios(): Promise<{ schema_version: number; scenarios: Record<string, CapabilityScenario> }> {
  const r = await fetch('/api/scenarios')
  if (!r.ok) throw new Error(`scenarios ${r.status}`)
  return r.json()
}

export async function getScenario(scenarioId: string): Promise<{ id: string; scenario: CapabilityScenario | null }> {
  const r = await fetch(`/api/scenarios/${scenarioId}`)
  if (!r.ok) throw new Error(`scenario ${r.status}`)
  return r.json()
}

// ── Runner Templates ────────────────────────────────────────────────

export type RunnerTemplate = {
  capability_id: string
  label: string
  description: string
  suitable_for: string[]
  risk_level: string
  result_type: 'text' | 'audio' | 'image' | 'voice_list' | 'chat'
  form_schema: Record<string, {
    type: 'input' | 'textarea' | 'select' | 'number' | 'slider'
    label: string
    default: string
    placeholder?: string
    max_chars?: number
    value_type?: 'string' | 'number' | 'boolean'
    min?: number
    max?: number
    step?: number
    options?: Array<{ value: string; label: string }>
  }>
  payload_template: Record<string, unknown>
  next_steps: Array<{
    capability_id: string
    label: string
    note: string
    blocked: boolean
  }>
}

export type RunnerTemplatesResponse = {
  schema_version: number
  supported: string[]
  templates: Record<string, RunnerTemplate>
}

export async function getRunnerTemplates(): Promise<RunnerTemplatesResponse> {
  const r = await fetch('/api/runner/templates')
  if (!r.ok) throw new Error(`runner templates ${r.status}`)
  return r.json()
}

export async function getRunnerTemplate(capabilityId: string): Promise<RunnerTemplate> {
  const r = await fetch(`/api/runner/template/${capabilityId}`)
  if (!r.ok) throw new Error(`runner template ${capabilityId} ${r.status}`)
  return r.json()
}
