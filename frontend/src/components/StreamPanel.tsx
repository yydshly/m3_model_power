import { useRef, useState } from 'react'
import { streamInvoke, createTraceId, getDiagnosticsTrace, type Capability, type Model } from '../api'
import { quotaLabel } from '../domain/workbenchLabels'
import { useSyncedModelSelection } from '../domain/useSyncedModelSelection'
import { buildDemoPayload } from '../domain/demoPayload'
import { validatePayloadForCapability } from '../domain/payloadValidation'

function parseBodySafely(text: string): {
  parsed: Record<string, unknown>
  error: string | null
} {
  try {
    const value = text.trim() ? JSON.parse(text) : {}
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return { parsed: {}, error: '请求体必须是 JSON 对象' }
    }
    return { parsed: value as Record<string, unknown>, error: null }
  } catch (e) {
    return { parsed: {}, error: `JSON 解析失败：${e instanceof Error ? e.message : String(e)}` }
  }
}

/**
 * 通用流式调用面板。
 * 上游 SSE/chunked 协议由后端 /api/stream/<id> 透传，前端拿到 chunks 直接追加到文本框。
 * 不解析 JSON token，目的是"看到流动"——具体 UI 后续可分协议特化。
 */
export function StreamPanel({
  cap,
  models,
  onDone,
}: {
  cap: Capability
  models: Model[]
  onDone?: (info?: { history_id?: string | null; capability_id?: string }) => void
}) {
  const { model, setModel } = useSyncedModelSelection(models)
  const [body, setBody] = useState<string>(JSON.stringify(buildDemoPayload(cap), null, 2))
  const [out, setOut] = useState<string>('')
  const [err, setErr] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [traceEvents, setTraceEvents] = useState<Record<string, unknown>[]>([])
  const [showTrace, setShowTrace] = useState(false)

  function updateJsonBodyField(bdy: string, key: string, value: unknown): string {
    const safe = parseBodySafely(bdy)
    if (safe.error || Object.keys(safe.parsed).length === 0) return bdy
    return JSON.stringify({ ...safe.parsed, [key]: value }, null, 2)
  }

  const start = async () => {
    if (!model) {
      setErr('当前能力没有可用模型，请检查模型配置或协议过滤结果。')
      return
    }
    if (running) return
    setErr(null)
    setOut('')

    const safe = parseBodySafely(body)
    if (safe.error) {
      setErr(safe.error)
      return
    }
    const parsed = safe.parsed

    // Validate payload before sending
    const validationResult = validatePayloadForCapability(cap.id, parsed)
    if (!validationResult.valid) {
      setErr(
        `参数检查未通过：${validationResult.issues
          .filter((i) => i.severity === 'error')
          .map((i) => `${i.field}: ${i.message}`)
          .join('；')}`
      )
      return
    }

    if (model && !('model' in parsed)) parsed.model = model
    const tid = createTraceId('stream')
    setTraceId(tid)
    setTraceEvents([])
    setShowTrace(false)
    setRunning(true)
    const ctl = new AbortController()
    abortRef.current = ctl
    try {
      const r = await streamInvoke(cap.id, parsed, tid)
      if (!r.ok || !r.body) {
        const txt = await r.text().catch(() => '')
        setErr(`[${r.status}] ${txt}`)
        setRunning(false)
        return
      }
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        setOut((prev) => prev + dec.decode(value))
      }
    } catch (e) {
      setErr(String(e))
    } finally {
      setRunning(false)
      abortRef.current = null
      onDone?.({ capability_id: cap.id })
    }
  }

  const stop = () => abortRef.current?.abort()

  const loadTrace = async (tid: string) => {
    try {
      const data = await getDiagnosticsTrace(tid)
      setTraceEvents(data.events ?? [])
      setShowTrace(true)
    } catch {
      setTraceEvents([])
    }
  }

  // Safe render-time validation — never throws
  const safeBody = parseBodySafely(body)
  const initialValidation = safeBody.error
    ? {
        valid: false,
        issues: [{ field: 'body', message: safeBody.error, severity: 'error' as const }],
      }
    : validatePayloadForCapability(cap.id, safeBody.parsed)

  const buttonDisabled = running || !initialValidation.valid

  return (
    <div className="space-y-4">
      {models.length > 0 && (
        <div>
          <label className="block text-xs text-slate-600 mb-1">模型</label>
          <select
            value={model}
            onChange={(e) => {
              const selected = e.target.value
              setModel(selected)
              setBody((prev) => updateJsonBodyField(prev, 'model', selected))
            }}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {quotaLabel(m.quota_eligible)} {m.label} · {m.tier}
              </option>
            ))}
          </select>
        </div>
      )}
      <div>
        <label className="block text-xs text-slate-600 mb-1">请求体 (JSON，stream=true 会自动注入)</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={10}
          className="w-full font-mono text-xs border border-slate-300 rounded p-2"
        />
      </div>
      {!initialValidation.valid && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          <div className="font-semibold mb-1">参数检查未通过：</div>
          <ul className="list-disc list-inside space-y-0.5">
            {initialValidation.issues.filter((i) => i.severity === 'error').map((issue, i) => (
              <li key={i}>
                <span className="font-mono">{issue.field}</span>：{issue.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={start}
          disabled={buttonDisabled}
          className="px-4 py-1.5 bg-sky-600 text-white rounded text-sm disabled:opacity-50"
        >
          {running ? '流式中…' : '流式调用'}
        </button>
        {running && (
          <button onClick={stop} className="px-4 py-1.5 bg-slate-200 text-slate-800 rounded text-sm">
            中断
          </button>
        )}
      </div>
      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}

      {traceId && (
        <div className="rounded border border-slate-200 bg-slate-50 p-2 text-xs">
          <div>trace_id：<span className="font-mono">{traceId}</span></div>
          {!showTrace && (
            <button onClick={() => loadTrace(traceId)} className="mt-1 text-sky-600 hover:underline">
              查看链路诊断
            </button>
          )}
          {showTrace && traceEvents.length > 0 && (
            <div className="mt-1">
              <div className="text-slate-500 mb-1">链路事件：</div>
              {traceEvents.map((e: Record<string, unknown>, i: number) => (
                <div key={i} className="font-mono text-[10px] text-slate-600">
                  {String(e.event)} {e.status !== 'ok' ? `❌ ${e.status}` : '✅'} {e.message ? String(e.message) : ''}
                </div>
              ))}
            </div>
          )}
          {showTrace && traceEvents.length === 0 && (
            <div className="mt-1 text-slate-400">暂无链路事件</div>
          )}
        </div>
      )}

      {out && (
        <pre className="text-xs bg-slate-900 text-emerald-200 rounded p-3 overflow-auto max-h-[480px] whitespace-pre-wrap">
          {out}
        </pre>
      )}
    </div>
  )
}
