import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  getVerificationIndex,
  getVerificationSummary,
  getTestConsoleHistory,
  getHistoryStatus,
  getCapabilityDescriptions,
  invoke,
  riskCheck,
  type Capability,
  type CapabilityDescription,
  type RiskCheckResult,
  type TestConsoleHistoryItem,
  type VerificationIndex,
  type VerificationSummary,
  type HistoryStatusResp,
} from '../api'
import { useRegistry } from '../store'
import AssetResultPreview from '../components/AssetResultPreview'
import InvocationHistoryPanel from '../components/InvocationHistoryPanel'
import { getRequiredConfirmations, allConfirmationsSatisfied, CONFIRM_LABELS } from '../domain/confirmations'
import { billingLabel, operationRiskLabel } from '../domain/workbenchLabels'
import { buildDemoPayload } from '../domain/demoPayload'

// ── Scope badge colors ─────────────────────────────────────────────────

function ScopeBadge({ scope }: { scope: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    in_scope: { label: '范围内', cls: 'bg-green-100 text-green-800' },
    warning_only: { label: '只提示', cls: 'bg-yellow-100 text-yellow-800' },
    out_of_scope: { label: '范围外', cls: 'bg-slate-100 text-slate-600' },
  }
  const s = map[scope] ?? { label: scope, cls: 'bg-slate-100 text-slate-600' }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${s.cls}`}>{s.label}</span>
}

// ── Billing badge ─────────────────────────────────────────────────────

function BillingBadge({ cat }: { cat: string }) {
  const cls: Record<string, string> = {
    normal_token_plan_test: 'bg-blue-50 text-blue-700',
    quota_sensitive: 'bg-amber-50 text-amber-700',
    paid_confirm_required: 'bg-orange-50 text-orange-700',
    high_cost_confirm_required: 'bg-red-50 text-red-700',
    asset_required_confirm_required: 'bg-purple-50 text-purple-700',
  }
  const label = billingLabel(cat)
  const color = cls[cat] ?? 'bg-slate-100 text-slate-700'
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{label}</span>
}

// ── Risk badge ────────────────────────────────────────────────────────

function RiskBadge({ risk }: { risk: string }) {
  const map: Record<string, string> = {
    normal: 'bg-green-50 text-green-700',
    destructive: 'bg-red-50 text-red-700',
    asset_required: 'bg-purple-50 text-purple-700',
    existing_task_only: 'bg-blue-50 text-blue-700',
    long_running: 'bg-yellow-50 text-yellow-700',
    quota_guarded: 'bg-orange-50 text-orange-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[risk] ?? 'bg-slate-100 text-slate-700'}`}>
      {operationRiskLabel(risk)}
    </span>
  )
}

// ── Confirmation checkboxes ────────────────────────────────────────────

function ConfirmationsEditor({
  required,
  confirmations,
  onChange,
}: {
  required: string[]
  confirmations: Record<string, boolean>
  onChange: (c: Record<string, boolean>) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {required.map((key) => (
        <label key={key} className="flex items-center gap-1.5 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={!!confirmations[key]}
            onChange={(e) => onChange({ ...confirmations, [key]: e.target.checked })}
            className="rounded"
          />
          <span className="text-slate-700">{CONFIRM_LABELS[key] ?? key}</span>
        </label>
      ))}
    </div>
  )
}

// ── Hint components ───────────────────────────────────────────────────

function TtsAsyncHint({ text }: { text: string }) {
  const len = text.length
  let level: 'ok' | 'warning' | 'quota' | 'blocked' = 'ok'
  let note = `当前 ${len} 字符，≤300 默认允许`
  if (len > 5000) { level = 'blocked'; note = `当前 ${len} 字符，>5000 禁止默认执行` }
  else if (len > 1000) { level = 'quota'; note = `当前 ${len} 字符，1001~5000 需要 confirm_quota` }
  else if (len > 300) { level = 'warning'; note = `当前 ${len} 字符，301~1000 warning` }

  const cls = level === 'ok' ? 'text-green-700 bg-green-50 border-green-200'
    : level === 'warning' ? 'text-yellow-700 bg-yellow-50 border-yellow-200'
    : level === 'quota' ? 'text-orange-700 bg-orange-50 border-orange-200'
    : 'text-red-700 bg-red-50 border-red-200'
  return <div className={`text-xs px-2 py-1 rounded border ${cls}`}>{note}</div>
}

function RequiresExistingTaskHint() {
  return (
    <div className="text-xs px-2 py-1 rounded border border-orange-200 bg-orange-50 text-orange-700">
      payload 中必须包含 task_id 或 file_id
    </div>
  )
}

function ImageI2IHint() {
  return (
    <div className="text-xs px-2 py-1 rounded border border-purple-200 bg-purple-50 text-purple-700">
      必须包含 img_url 或 reference image 参数，并勾选 confirm_asset_source
    </div>
  )
}

// ── Risk Check Panel ──────────────────────────────────────────────────

function RiskCheckPanel({
  cap,
  payload,
  onPayloadChange,
  confirmations,
  onConfirmationsChange,
  onClose,
  onDone,
}: {
  cap: Capability
  payload: string
  onPayloadChange: (v: string) => void
  confirmations: Record<string, boolean>
  onConfirmationsChange: (c: Record<string, boolean>) => void
  onClose: () => void
  onDone?: () => void
}) {
  const required = getRequiredConfirmations(cap)
  const [result, setResult] = useState<RiskCheckResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  let parsedPayload: object = {}
  let payloadErr: string | null = null
  try { parsedPayload = JSON.parse(payload) } catch { payloadErr = 'JSON 格式错误' }

  const runCheck = async () => {
    if (payloadErr) { setErr(payloadErr); return }
    setLoading(true)
    setErr(null)
    setResult(null)
    try {
      const r = await riskCheck(cap.id, parsedPayload as Record<string, unknown>, confirmations)
      setResult(r)
      onDone?.()
    } catch (e: any) {
      setErr(e.message)
      onDone?.()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-sky-200 bg-sky-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sky-900">安全检查 — {cap.id}</h3>
        <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-800">✕ 关闭</button>
      </div>

      {cap.id === 'tts-async' && (
        <div className="mb-3"><TtsAsyncHint text={typeof parsedPayload === 'object' && parsedPayload !== null && 'text' in parsedPayload ? String((parsedPayload as any).text ?? '') : ''} /></div>
      )}
      {cap.operation_policy?.requires_existing_task && (
        <div className="mb-3"><RequiresExistingTaskHint /></div>
      )}
      {cap.id === 'image-i2i' && (
        <div className="mb-3"><ImageI2IHint /></div>
      )}

      {required.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">需要确认项：</p>
          <ConfirmationsEditor required={required} confirmations={confirmations} onChange={onConfirmationsChange} />
        </div>
      )}

      <div className="mb-3">
        <p className="text-xs text-slate-500 mb-1">Payload (JSON)：</p>
        <p className="text-[10px] text-amber-600 mb-1">这是开发者 raw JSON payload，必须匹配该能力 handler 的入参。不确定怎么填时，请去「能力体验」页面。</p>
        <textarea
          value={payload}
          onChange={(e) => onPayloadChange(e.target.value)}
          rows={6}
          className={`w-full font-mono text-xs border rounded p-2 ${payloadErr ? 'border-red-400 bg-red-50' : 'border-slate-300'}`}
        />
        {payloadErr && <p className="text-xs text-red-600 mt-1">{payloadErr}</p>}
      </div>

      <button
        onClick={runCheck}
        disabled={loading || !!payloadErr}
        className="px-4 py-1.5 bg-sky-600 text-white text-sm rounded hover:bg-sky-700 disabled:opacity-50"
      >
        {loading ? '检查中…' : '安全检查'}
      </button>

      {err && <p className="mt-2 text-sm text-red-600">错误: {err}</p>}

      {result && (
        <div className="mt-3">
          <div className={`text-sm font-medium ${result.allowed ? 'text-green-700' : 'text-red-700'}`}>
            allowed: {String(result.allowed)}
          </div>
          {result.blocked_reasons.length > 0 && (
            <div className="text-sm text-red-600 mt-1">blocked_reasons: {result.blocked_reasons.join(', ')}</div>
          )}
          {result.required_confirmations.length > 0 && (
            <div className="text-sm text-orange-700 mt-1">
              required_confirmations: {result.required_confirmations.join(', ')}
            </div>
          )}
          {result.warnings.length > 0 && (
            <div className="text-sm text-yellow-700 mt-1">warnings: {result.warnings.join(', ')}</div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Invoke Panel ──────────────────────────────────────────────────────

function InvokePanel({
  cap,
  payload,
  onPayloadChange,
  confirmations,
  onConfirmationsChange,
  onClose,
  onDone,
}: {
  cap: Capability
  payload: string
  onPayloadChange: (v: string) => void
  confirmations: Record<string, boolean>
  onConfirmationsChange: (c: Record<string, boolean>) => void
  onClose: () => void
  onDone?: () => void
}) {
  const required = getRequiredConfirmations(cap)
  const allConfirmed = allConfirmationsSatisfied(required, confirmations)

  const [result, setResult] = useState<object | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  let parsedPayload: object = {}
  let payloadErr: string | null = null
  try { parsedPayload = JSON.parse(payload) } catch { payloadErr = 'JSON 格式错误' }

  const runInvoke = async () => {
    if (payloadErr) { setErr(payloadErr); return }
    setLoading(true)
    setErr(null)
    setResult(null)
    try {
      const res = await invoke(cap.id, parsedPayload as Record<string, unknown>, confirmations)
      if ('error' in res) {
        setErr(`${res.error}: ${res.message}`)
        if ('blocked_reasons' in res) setResult(res)
      } else {
        setResult(res)
      }
      onDone?.()
    } catch (e: any) {
      setErr(String(e))
      onDone?.()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-indigo-900">真实调用 — {cap.id}</h3>
        <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-800">✕ 关闭</button>
      </div>

      {!allConfirmed && required.length > 0 && (
        <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          需要全部确认才能执行
        </div>
      )}

      {cap.id === 'tts-async' && (
        <div className="mb-3"><TtsAsyncHint text={typeof parsedPayload === 'object' && parsedPayload !== null && 'text' in parsedPayload ? String((parsedPayload as any).text ?? '') : ''} /></div>
      )}
      {cap.operation_policy?.requires_existing_task && (
        <div className="mb-3"><RequiresExistingTaskHint /></div>
      )}
      {cap.id === 'image-i2i' && (
        <div className="mb-3"><ImageI2IHint /></div>
      )}

      {required.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">需要确认项：</p>
          <ConfirmationsEditor required={required} confirmations={confirmations} onChange={onConfirmationsChange} />
        </div>
      )}

      <div className="mb-3">
        <p className="text-xs text-slate-500 mb-1">Payload (JSON)：</p>
        <p className="text-[10px] text-amber-600 mb-1">这是开发者 raw JSON payload，必须匹配该能力 handler 的入参。不确定怎么填时，请去「能力体验」页面。</p>
        <textarea
          value={payload}
          onChange={(e) => onPayloadChange(e.target.value)}
          rows={8}
          className={`w-full font-mono text-xs border rounded p-2 ${payloadErr ? 'border-red-400 bg-red-50' : 'border-slate-300'}`}
        />
        {payloadErr && <p className="text-xs text-red-600 mt-1">{payloadErr}</p>}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onPayloadChange(JSON.stringify(buildDemoPayload(cap), null, 2))}
          className="px-3 py-1.5 text-xs border border-slate-300 rounded bg-white hover:bg-slate-100"
        >
          重置为示例 payload
        </button>
        <button
          onClick={() => navigator.clipboard.writeText(payload)}
          className="px-3 py-1.5 text-xs border border-slate-300 rounded bg-white hover:bg-slate-100"
        >
          复制 payload
        </button>
      </div>

      <button
        onClick={runInvoke}
        disabled={loading || !allConfirmed || !!payloadErr}
        className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-40 mt-3"
      >
        {loading ? '执行中…' : '真实调用'}
      </button>

      {err && <p className="mt-2 text-sm text-red-600">错误: {err}</p>}

      {result && (
        <div className="mt-3">
          <AssetResultPreview data={result} />
        </div>
      )}
    </div>
  )
}

// ── Main TestConsole page ─────────────────────────────────────────────

export default function TestConsole() {
  const { registry } = useRegistry()
  const [summary, setSummary] = useState<VerificationSummary | null>(null)
  const [verIndex, setVerIndex] = useState<VerificationIndex | null>(null)
  const [summaryErr, setSummaryErr] = useState<string | null>(null)

  // Per-capability state
  const [selectedCapId, setSelectedCapId] = useState<string | null>(null)
  const [panelType, setPanelType] = useState<'none' | 'risk-check' | 'invoke'>('none')
  const [confirmations, setConfirmations] = useState<Record<string, Record<string, boolean>>>({})
  const [payloads, setPayloads] = useState<Record<string, string>>({})
  const [filterScope, setFilterScope] = useState<string>('all')
  const [filterCat, setFilterCat] = useState<string>('all')
  const [filterRisk, setFilterRisk] = useState<string>('all')
  const [search, setSearch] = useState<string>('')
  const [history, setHistory] = useState<TestConsoleHistoryItem[]>([])
  const [historyErr, setHistoryErr] = useState<string | null>(null)
  const [historyStatus, setHistoryStatus] = useState<HistoryStatusResp | null>(null)
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null)
  const [filterHistoryAction, setFilterHistoryAction] = useState<'all'|'risk_check'|'invoke'>('all')
  const [filterHistoryHasAssets, setFilterHistoryHasAssets] = useState(false)
  const [descriptions, setDescriptions] = useState<Record<string, CapabilityDescription>>({})

  // Ref for scroll-into-view of test panel
  const panelRef = useRef<HTMLDivElement>(null)

  // Support ?capability=xxx URL param to auto-select a capability
  const [searchParams] = useSearchParams()
  const urlCapId = searchParams.get('capability')

  useEffect(() => {
    if (urlCapId && registry?.capabilities.some((c) => c.id === urlCapId)) {
      setSelectedCapId(urlCapId)
    }
  }, [urlCapId, registry])

  const refreshHistoryStatus = () => {
    getHistoryStatus()
      .then(s => setHistoryStatus(s))
      .catch(() => setHistoryStatus(null))
  }

  const refreshHistory = () => {
    getTestConsoleHistory(50)
      .then(r => { setHistory(r.items); setHistoryErr(null) })
      .catch((e: any) => setHistoryErr(e.message))
    refreshHistoryStatus()
  }

  useEffect(() => { refreshHistory() }, [])

  useEffect(() => {
    getCapabilityDescriptions()
      .then(r => setDescriptions(r.descriptions))
      .catch(() => {})
  }, [])

  useEffect(() => {
    getVerificationSummary()
      .then(setSummary)
      .catch((e: any) => setSummaryErr(e.message))
  }, [])

  useEffect(() => {
    getVerificationIndex().then(setVerIndex).catch(() => {})
  }, [])

  const isVerified = (capId: string): boolean => {
    if (!verIndex) return false
    return !!verIndex.capabilities[capId]?.verified
  }

  const caps = registry?.capabilities ?? []
  const filtered = caps.filter((c) => {
    if (filterScope !== 'all' && c.scope_policy?.current_scope !== filterScope) return false
    if (filterCat !== 'all' && c.category !== filterCat) return false
    if (filterRisk !== 'all') {
      const risk = c.operation_policy?.operation_risk ?? 'normal'
      if (risk !== filterRisk) return false
    }
    if (search && !c.id.includes(search) && !c.label.includes(search)) return false
    return true
  })

  const openRiskCheck = (cap: Capability) => {
    setSelectedCapId(cap.id)
    setPanelType('risk-check')
    setConfirmations({})
    if (payloads[cap.id] === undefined) {
      setPayloads(p => ({ ...p, [cap.id]: JSON.stringify(buildDemoPayload(cap), null, 2) }))
    }
    setTimeout(() => panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  const openInvoke = (cap: Capability) => {
    setSelectedCapId(cap.id)
    setPanelType('invoke')
    setConfirmations({})
    if (payloads[cap.id] === undefined) {
      setPayloads(p => ({ ...p, [cap.id]: JSON.stringify(buildDemoPayload(cap), null, 2) }))
    }
    setTimeout(() => panelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  const selectedCap = registry?.capabilities.find((c) => c.id === selectedCapId) ?? null

  const categories = registry?.categories ?? []
  const scopeOptions = ['all', 'in_scope', 'warning_only', 'out_of_scope']

  const completionPct = summary?.completion_rate ?? 0
  const bannerColor = completionPct >= 100 ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'

  return (
    <div className="p-6 space-y-6">
      {/* ── Advanced console banner ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 flex items-start gap-3">
        <span className="text-base">🧪</span>
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-medium text-slate-700">开发者测试控制台</p>
          <p className="text-xs text-slate-500">
            开发者测试控制台 · 直接调用 /api/invoke/&#123;&#123;capability_id&#125;&#125;，不会自动套用能力体验页的表单模板。
          </p>
          <p className="text-xs text-slate-500 mt-1">
            推荐流程：1. 搜索或筛选能力 → 2. 点击「安全检查」验证 RiskGate → 3. 确认 payload 和确认项 → 4. 再点击「真实调用」→ 5. 在最近调用记录中查看结果和资产
          </p>
          <div className="flex flex-wrap gap-4 text-[10px] text-slate-400 mt-1">
            <span>💡 <strong>普通体验请使用「能力体验」：</strong>表单化、带提示、带结果预览</span>
            <span>⚠️ <strong>开发者测试：</strong>手动填写 raw JSON payload</span>
            <span>📖 <strong>能力详情：</strong>查看 API、风险、计费、scope、说明</span>
          </div>
          <div className="flex flex-wrap gap-3 text-xs mt-2">
            <Link to="/capability-runner" className="text-sky-600 hover:underline">去能力体验 →</Link>
            <Link to="/capability-profiles" className="text-sky-600 hover:underline">去能力画像 →</Link>
            <Link to="/" className="text-sky-600 hover:underline">去总览 →</Link>
          </div>
        </div>
      </div>

      {/* ── Summary Banner ── */}
      <div className={`rounded-xl border p-5 ${bannerColor}`}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-slate-900">Token Plan 验收进度</h2>
          <span className="text-2xl font-bold text-green-700">
            {summary ? `${summary.in_scope_verified}/${summary.in_scope_total}` : '…'}
            <span className="text-sm font-normal text-slate-500 ml-1">
              ({completionPct}%)
            </span>
          </span>
        </div>

        {summaryErr ? (
          <p className="text-sm text-red-600">无法加载验收摘要: {summaryErr}</p>
        ) : summary ? (
          <div className="space-y-1 text-sm text-slate-700">
            <div>in_scope_total: <strong>{summary.in_scope_total}</strong></div>
            <div>in_scope_verified: <strong className="text-green-700">{summary.in_scope_verified}</strong></div>
            <div>in_scope_unverified: <strong className="text-red-600">{summary.in_scope_unverified}</strong></div>
            {summary.in_scope_unverified_ids.length > 0 && (
              <div className="text-red-500">未验收: {summary.in_scope_unverified_ids.join(', ')}</div>
            )}
            {(() => {
              const caps = registry?.capabilities ?? []
              const inScopeTotal = caps.filter(c => c.scope_policy?.current_scope === 'in_scope' && c.scope_policy?.count_in_completion_rate).length
              const describedInScope = caps.filter(c => c.scope_policy?.current_scope === 'in_scope' && descriptions[c.id]).length
              return (
                <div className="text-blue-700">
                  说明覆盖: <strong>{describedInScope}</strong> / {inScopeTotal} in_scope
                </div>
              )
            })()}
          </div>
        ) : (
          <p className="text-sm text-slate-500">加载中…</p>
        )}

        {/* Progress bar */}
        <div className="mt-3 h-3 bg-white rounded-full overflow-hidden border border-slate-200">
          <div
            className={`h-full transition-all ${completionPct >= 100 ? 'bg-green-500' : 'bg-yellow-400'}`}
            style={{ width: `${Math.min(completionPct, 100)}%` }}
          />
        </div>
      </div>


      {/* ── Capability Description Panel ── */}
      {selectedCap && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-blue-900">能力说明 — {selectedCap.id}</h3>
          </div>
          {descriptions[selectedCap.id] ? (() => {
            const d = descriptions[selectedCap.id]
            return (
              <div className="space-y-2 text-sm">
                <div className="text-slate-700">{d.summary}</div>
                {d.use_cases.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-green-700 bg-green-100 px-1.5 py-0.5 rounded mr-1">适合场景</span>
                    <span className="text-slate-600">{d.use_cases.join('、')}</span>
                  </div>
                )}
                {d.not_recommended_for.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-red-700 bg-red-100 px-1.5 py-0.5 rounded mr-1">不适合</span>
                    <span className="text-slate-600">{d.not_recommended_for.join('、')}</span>
                  </div>
                )}
                {d.input_notes.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded mr-1">输入</span>
                    <span className="text-slate-600">{d.input_notes.join('；')}</span>
                  </div>
                )}
                {d.risk_notes.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-orange-700 bg-orange-100 px-1.5 py-0.5 rounded mr-1">风险/计费</span>
                    <span className="text-slate-600">{d.risk_notes.join('；')}</span>
                  </div>
                )}
                {d.billing_notes.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-purple-700 bg-purple-100 px-1.5 py-0.5 rounded mr-1">计费说明</span>
                    <span className="text-slate-600">{d.billing_notes.join('；')}</span>
                  </div>
                )}
                {d.output_notes.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-teal-700 bg-teal-100 px-1.5 py-0.5 rounded mr-1">输出说明</span>
                    <span className="text-slate-600">{d.output_notes.join('；')}</span>
                  </div>
                )}
                {d.common_errors.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded mr-1">常见错误</span>
                    <span className="text-slate-600">{d.common_errors.join('；')}</span>
                  </div>
                )}
                {d.product_usage.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-indigo-700 bg-indigo-100 px-1.5 py-0.5 rounded mr-1">产品化建议</span>
                    <span className="text-slate-600">{d.product_usage.join('；')}</span>
                  </div>
                )}
                {d.integration_tips.length > 0 && (
                  <div>
                    <span className="text-xs font-medium text-blue-700 bg-blue-100 px-1.5 py-0.5 rounded mr-1">集成建议</span>
                    <span className="text-slate-600">{d.integration_tips.join('；')}</span>
                  </div>
                )}
              </div>
            )
          })() : (
            <p className="text-sm text-slate-400">暂无能力说明</p>
          )}
          {/* 下一步引导 */}
          <div className="mt-3 pt-3 border-t border-blue-200">
            <p className="text-xs font-medium text-blue-800 mb-1">下一步：</p>
            <ol className="text-xs text-blue-700 space-y-0.5 list-decimal list-inside">
              <li>点击「安全检查」</li>
              <li>勾选必要确认项</li>
              <li>检查 allowed=true</li>
              <li>再执行「真实调用」</li>
            </ol>
          </div>
        </div>
      )}

      {/* ── Filter bar (sticky) ── */}
      <div className="sticky top-0 z-10 bg-white border border-slate-200 rounded-xl px-4 py-3 flex flex-wrap gap-3 items-center shadow-sm">
        <input
          type="text"
          placeholder="搜索 capability…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm w-48"
        />
        <select
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="all">全部分类</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.emoji} {c.label}</option>
          ))}
        </select>
        <select
          value={filterScope}
          onChange={(e) => setFilterScope(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm"
        >
          {scopeOptions.map((s) => {
            const labelMap: Record<string, string> = {
              all: '全部范围',
              in_scope: '范围内',
              warning_only: '只提示',
              out_of_scope: '范围外',
            }
            return <option key={s} value={s}>{labelMap[s] ?? s}</option>
          })}
        </select>
        <select
          value={filterRisk}
          onChange={(e) => setFilterRisk(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="all">全部风险</option>
          <option value="normal">普通</option>
          <option value="destructive">破坏性</option>
          <option value="asset_required">素材型</option>
          <option value="long_running">长时运行</option>
          <option value="quota_guarded">配额门禁</option>
          <option value="existing_task_only">仅已有任务</option>
        </select>
        <span className="text-sm text-slate-500 ml-auto">{filtered.length} 个能力</span>
      </div>

      {/* ── Capability Table ── */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 max-h-[400px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">能力 ID</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">能力名称</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">分类</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">范围</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">计费/额度</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">操作风险</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">已验收</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">有说明</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((cap) => {
              const scope = cap.scope_policy?.current_scope ?? 'unknown'
              const billing = cap.billing_policy?.billing_category ?? 'unknown'
              const risk = cap.operation_policy?.operation_risk ?? 'normal'
              const verified = isVerified(cap.id)
              const isImplemented = cap.status === 'implemented'

              return (
                <tr key={cap.id} className={`hover:bg-slate-50 ${selectedCapId === cap.id ? 'bg-sky-100 ring-2 ring-sky-300' : ''}`}>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-800">{cap.id}</td>
                  <td className="px-4 py-2.5 text-slate-800">{cap.label}</td>
                  <td className="px-4 py-2.5 text-slate-600">{registry?.categories.find(c => c.id === cap.category)?.label ?? cap.category}</td>
                  <td className="px-4 py-2.5"><ScopeBadge scope={scope} /></td>
                  <td className="px-4 py-2.5"><BillingBadge cat={billing} /></td>
                  <td className="px-4 py-2.5"><RiskBadge risk={risk} /></td>
                  <td className="px-4 py-2.5">
                    {verified
                      ? <span className="text-green-600 font-medium">✓</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {descriptions[cap.id]
                      ? <span className="text-blue-600 font-medium">✓</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {scope === 'out_of_scope' ? (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <span>🔒</span> 范围外
                      </span>
                    ) : isImplemented ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => openRiskCheck(cap)}
                          className="px-2 py-1 text-xs rounded border border-slate-300 bg-white hover:bg-slate-100"
                        >
                          安全检查
                        </button>
                        <button
                          onClick={() => openInvoke(cap)}
                          disabled={scope === 'warning_only'}
                          title={scope === 'warning_only' ? '该能力只做风险提示，默认不执行' : ''}
                          className="px-2 py-1 text-xs rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          真实调用
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Inline Action Panel ── */}
      {selectedCap && panelType !== 'none' && (
        <div ref={panelRef} className="animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center gap-2 mb-3 px-1">
            <span className="text-sm font-semibold text-slate-800">
              测试 {selectedCap.id}
            </span>
            <span className="text-xs text-slate-400">（{panelType === 'risk-check' ? '安全检查' : '真实调用'}）</span>
          </div>
          {panelType === 'risk-check' && (
            <RiskCheckPanel
              cap={selectedCap}
              payload={payloads[selectedCap.id] ?? '{}'}
              onPayloadChange={(v) => setPayloads(p => ({ ...p, [selectedCap.id]: v }))}
              confirmations={confirmations[selectedCap.id] ?? {}}
              onConfirmationsChange={(c) => setConfirmations({ ...confirmations, [selectedCap.id]: c })}
              onClose={() => { setPanelType('none'); setSelectedCapId(null) }}
              onDone={refreshHistory}
            />
          )}
          {panelType === 'invoke' && (
            <InvokePanel
              cap={selectedCap}
              payload={payloads[selectedCap.id] ?? '{}'}
              onPayloadChange={(v) => setPayloads(p => ({ ...p, [selectedCap.id]: v }))}
              confirmations={confirmations[selectedCap.id] ?? {}}
              onConfirmationsChange={(c) => setConfirmations({ ...confirmations, [selectedCap.id]: c })}
              onClose={() => { setPanelType('none'); setSelectedCapId(null) }}
              onDone={refreshHistory}
            />
          )}
        </div>
      )}

      {/* ── History Panel ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h3 className="font-semibold text-slate-800">
            最近调用记录
            {historyStatus?.exists && (
              <span className="ml-2 text-[10px] text-slate-400 font-normal">
                {historyStatus.line_count} 行 / {historyStatus.valid_record_count} 条有效
                {historyStatus.line_count > historyStatus.valid_record_count && (
                  <span className="text-amber-500"> · 有损坏记录</span>
                )}
                {' '}· {historyStatus.last_modified ? new Date(historyStatus.last_modified).toLocaleString() : '无修改时间'}
              </span>
            )}
          </h3>
          <button
            onClick={refreshHistory}
            className="px-3 py-1 text-xs border border-slate-300 rounded bg-white hover:bg-slate-100"
          >
            刷新
          </button>
        </div>

        {historyErr && (
          <p className="text-xs text-red-600 mb-2">加载失败: {historyErr}</p>
        )}

        {history.length === 0 && !historyErr && (
          <div className="text-xs text-slate-500 space-y-1">
            <p className="text-sm text-slate-400">还没有调用记录。</p>
            <p className="text-slate-400">执行一次「安全检查」或「真实调用」后会在这里显示。</p>
            {!historyStatus?.exists ? (
              <details className="group mt-2">
                <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700">调试信息 ▼</summary>
                <div className="mt-2 p-2 rounded bg-amber-50 border border-amber-200 text-amber-700">
                  <ol className="ml-4 list-decimal list-inside space-y-0.5">
                    <li>当前 <code className="bg-amber-100 px-1 rounded">{historyStatus?.history_path ?? 'backend/runtime/test_console/history.jsonl'}</code> 尚未生成</li>
                    <li>后端进程刚重启</li>
                    <li>还没有执行安全检查 / 真实调用</li>
                    <li>当前运行目录与预期不一致</li>
                  </ol>
                  <p className="mt-1 text-[10px]">文件不存在 · 路径：{historyStatus?.history_path ?? '(未获取到)'}</p>
                </div>
              </details>
            ) : null}
          </div>
        )}

        {history.length > 0 && (
          <InvocationHistoryPanel
            items={history}
            expandedId={expandedHistoryId}
            onToggleExpand={setExpandedHistoryId}
            filterAction={filterHistoryAction}
            onFilterChange={setFilterHistoryAction}
            filterHasAssets={filterHistoryHasAssets}
            onFilterHasAssetsChange={setFilterHistoryHasAssets}
          />
        )}
      </div>
    </div>
  )
}
