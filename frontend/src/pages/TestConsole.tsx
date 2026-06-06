import { useEffect, useState } from 'react'
import {
  getVerificationIndex,
  getVerificationSummary,
  getTestConsoleHistory,
  invoke,
  riskCheck,
  type Capability,
  type RiskCheckResult,
  type TestConsoleHistoryItem,
  type VerificationIndex,
  type VerificationSummary,
} from '../api'
import { useRegistry } from '../store'
import { JsonView } from '../components/JsonView'

// ── Confirmation logic (mirrors InvokePanel.tsx) ───────────────────────

function getRequiredConfirmations(cap: Capability): string[] {
  const required: string[] = []
  const bp = cap.billing_policy
  const op = cap.operation_policy
  if (bp?.may_charge_extra) required.push('confirm_paid')
  if (bp?.billing_category === 'high_cost_confirm_required') required.push('confirm_high_cost')
  if (op?.is_destructive) required.push('confirm_destructive')
  if (op?.requires_uploaded_asset) required.push('confirm_asset_source')
  if (op?.is_long_running) required.push('confirm_long_running')
  if (op?.requires_existing_task) required.push('confirm_existing_task')
  if (cap.id === 'tts-async') required.push('confirm_quota')
  return required
}

function allConfirmationsSatisfied(
  required: string[],
  confirmations: Record<string, boolean>,
): boolean {
  return required.every((r) => confirmations[r])
}

// ── Scope badge colors ─────────────────────────────────────────────────

function ScopeBadge({ scope }: { scope: string }) {
  if (scope === 'in_scope')
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">in_scope</span>
  if (scope === 'warning_only')
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">warning_only</span>
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">out_of_scope</span>
}

// ── Billing badge ─────────────────────────────────────────────────────

function BillingBadge({ cat }: { cat: string }) {
  const map: Record<string, string> = {
    normal_token_plan_test: 'token-plan',
    quota_sensitive: 'quota',
    paid_confirm_required: 'paid',
    high_cost_confirm_required: 'high-cost',
    asset_required_confirm_required: 'asset',
  }
  const cls: Record<string, string> = {
    normal_token_plan_test: 'bg-blue-50 text-blue-700',
    quota_sensitive: 'bg-slate-100 text-slate-700',
    paid_confirm_required: 'bg-orange-50 text-orange-700',
    high_cost_confirm_required: 'bg-red-50 text-red-700',
    asset_required_confirm_required: 'bg-purple-50 text-purple-700',
  }
  const label = map[cat] ?? cat
  const color = cls[cat] ?? 'bg-slate-100 text-slate-700'
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{label}</span>
}

// ── Risk badge ────────────────────────────────────────────────────────

function RiskBadge({ risk }: { risk: string }) {
  const map: Record<string, string> = {
    normal: 'bg-green-50 text-green-700',
    destructive: 'bg-red-50 text-red-700',
    asset_required: 'bg-purple-50 text-purple-700',
    existing_task_only: 'bg-orange-50 text-orange-700',
    long_running: 'bg-yellow-50 text-yellow-700',
    quota_guarded: 'bg-slate-100 text-slate-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[risk] ?? 'bg-slate-100 text-slate-700'}`}>
      {risk}
    </span>
  )
}

// ── Confirmation checkboxes ────────────────────────────────────────────

const CONFIRM_LABELS: Record<string, string> = {
  confirm_paid: 'confirm_paid (may charge)',
  confirm_high_cost: 'confirm_high_cost (high cost)',
  confirm_destructive: 'confirm_destructive (destructive)',
  confirm_asset_source: 'confirm_asset_source (external asset)',
  confirm_long_running: 'confirm_long_running (long running)',
  confirm_existing_task: 'confirm_existing_task (existing task)',
  confirm_quota: 'confirm_quota (quota guard)',
}

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
        <h3 className="font-semibold text-sky-900">RiskGate 检查 — {cap.id}</h3>
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
          <p className="text-xs text-slate-500 mb-1">Required confirmations:</p>
          <ConfirmationsEditor required={required} confirmations={confirmations} onChange={onConfirmationsChange} />
        </div>
      )}

      <div className="mb-3">
        <p className="text-xs text-slate-500 mb-1">Payload (JSON):</p>
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
        {loading ? '检查中…' : 'Run Risk Check'}
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
        <h3 className="font-semibold text-indigo-900">Invoke — {cap.id}</h3>
        <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-800">✕ 关闭</button>
      </div>

      {!allConfirmed && required.length > 0 && (
        <div className="mb-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
          需要全部确认才能执行: {required.join(', ')}
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
          <p className="text-xs text-slate-500 mb-1">Confirmations:</p>
          <ConfirmationsEditor required={required} confirmations={confirmations} onChange={onConfirmationsChange} />
        </div>
      )}

      <div className="mb-3">
        <p className="text-xs text-slate-500 mb-1">Payload (JSON):</p>
        <textarea
          value={payload}
          onChange={(e) => onPayloadChange(e.target.value)}
          rows={8}
          className={`w-full font-mono text-xs border rounded p-2 ${payloadErr ? 'border-red-400 bg-red-50' : 'border-slate-300'}`}
        />
        {payloadErr && <p className="text-xs text-red-600 mt-1">{payloadErr}</p>}
      </div>

      <button
        onClick={runInvoke}
        disabled={loading || !allConfirmed || !!payloadErr}
        className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-40"
      >
        {loading ? '执行中…' : 'Execute'}
      </button>

      {err && <p className="mt-2 text-sm text-red-600">错误: {err}</p>}

      {result && (
        <div className="mt-3">
          <JsonView data={result} />
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
  const [search, setSearch] = useState<string>('')
  const [history, setHistory] = useState<TestConsoleHistoryItem[]>([])
  const [historyErr, setHistoryErr] = useState<string | null>(null)

  const refreshHistory = () => {
    getTestConsoleHistory(50)
      .then(r => { setHistory(r.items); setHistoryErr(null) })
      .catch((e: any) => setHistoryErr(e.message))
  }

  useEffect(() => { refreshHistory() }, [])

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
    if (search && !c.id.includes(search) && !c.label.includes(search)) return false
    return true
  })

  const openRiskCheck = (cap: Capability) => {
    setSelectedCapId(cap.id)
    setPanelType('risk-check')
    setConfirmations({})
    if (payloads[cap.id] === undefined) {
      setPayloads(p => ({ ...p, [cap.id]: JSON.stringify(cap.example ?? {}, null, 2) }))
    }
  }

  const openInvoke = (cap: Capability) => {
    setSelectedCapId(cap.id)
    setPanelType('invoke')
    setConfirmations({})
    if (payloads[cap.id] === undefined) {
      setPayloads(p => ({ ...p, [cap.id]: JSON.stringify(cap.example ?? {}, null, 2) }))
    }
  }

  const selectedCap = registry?.capabilities.find((c) => c.id === selectedCapId) ?? null

  const categories = registry?.categories ?? []
  const scopeOptions = ['all', 'in_scope', 'warning_only', 'out_of_scope']

  const completionPct = summary?.completion_rate ?? 0
  const bannerColor = completionPct >= 100 ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'

  return (
    <div className="p-6 space-y-6">
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

      {/* ── History Panel ── */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-800">调用历史</h3>
          <button
            onClick={refreshHistory}
            className="px-3 py-1 text-xs border border-slate-300 rounded bg-white hover:bg-slate-100"
          >
            刷新历史
          </button>
        </div>

        {historyErr && (
          <p className="text-xs text-red-600 mb-2">加载失败: {historyErr}</p>
        )}

        {history.length === 0 && !historyErr ? (
          <p className="text-sm text-slate-400">暂无历史记录</p>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {history.map((item) => {
              const ok = item.result?.ok ?? item.result?.allowed ?? false
              const err = item.result?.error ?? (item.result?.blocked_reasons?.length ? item.result.blocked_reasons.join('; ') : null)
              const time = item.created_at ? new Date(item.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''
              return (
                <div key={item.id} className="flex items-start gap-3 text-xs border-b border-slate-100 pb-1 last:border-0">
                  <span className="text-slate-400 shrink-0 w-20">{time}</span>
                  <span className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-medium ${item.action === 'risk_check' ? 'bg-sky-100 text-sky-700' : 'bg-indigo-100 text-indigo-700'}`}>
                    {item.action === 'risk_check' ? 'RC' : 'INV'}
                  </span>
                  <span className="font-mono text-slate-700">{item.capability_id}</span>
                  <span className={`shrink-0 ${ok ? 'text-green-600' : 'text-red-600'}`}>
                    {ok ? '✓' : '✗'}
                  </span>
                  {err && <span className="text-red-500 truncate">{err}</span>}
                  <span className="ml-auto text-slate-400 shrink-0">
                    {item.payload_summary.payload_size_chars > 0 ? `${item.payload_summary.payload_size_chars} chars` : ''}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Filter bar ── */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="搜索 capability…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm w-48"
        />
        <select
          value={filterScope}
          onChange={(e) => setFilterScope(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm"
        >
          {scopeOptions.map((s) => (
            <option key={s} value={s}>{s === 'all' ? '全部 Scope' : s}</option>
          ))}
        </select>
        <select
          value={filterCat}
          onChange={(e) => setFilterCat(e.target.value)}
          className="border border-slate-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="all">全部 Category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.emoji} {c.label}</option>
          ))}
        </select>
        <span className="text-sm text-slate-500 ml-auto">{filtered.length} 个能力</span>
      </div>

      {/* ── Capability Table ── */}
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">ID</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Name</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Category</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Scope</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Billing</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Risk</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Verified</th>
              <th className="text-left px-4 py-2.5 font-medium text-slate-700">Actions</th>
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
                <tr key={cap.id} className={`hover:bg-slate-50 ${selectedCapId === cap.id ? 'bg-sky-50' : ''}`}>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-800">{cap.id}</td>
                  <td className="px-4 py-2.5 text-slate-800">{cap.label}</td>
                  <td className="px-4 py-2.5 text-slate-600">{cap.category}</td>
                  <td className="px-4 py-2.5"><ScopeBadge scope={scope} /></td>
                  <td className="px-4 py-2.5"><BillingBadge cat={billing} /></td>
                  <td className="px-4 py-2.5"><RiskBadge risk={risk} /></td>
                  <td className="px-4 py-2.5">
                    {verified
                      ? <span className="text-green-600 font-medium">✓</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {scope === 'out_of_scope' ? (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <span>🔒</span> out_of_scope
                      </span>
                    ) : isImplemented ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => openRiskCheck(cap)}
                          className="px-2 py-1 text-xs rounded border border-slate-300 bg-white hover:bg-slate-100"
                        >
                          Risk Check
                        </button>
                        <button
                          onClick={() => openInvoke(cap)}
                          disabled={scope === 'warning_only'}
                          title={scope === 'warning_only' ? 'warning_only capability' : ''}
                          className="px-2 py-1 text-xs rounded border border-indigo-300 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          Invoke
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
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">
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
    </div>
  )
}
