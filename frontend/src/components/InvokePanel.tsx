import { useEffect, useMemo, useState } from 'react'
import { invoke, riskCheck, createTraceId, getDiagnosticsTrace, type Capability, type Model, type RiskCheckResult } from '../api'
import { getRequiredConfirmations, allConfirmationsSatisfied } from '../domain/confirmations'
import { JsonView } from './JsonView'
import { quotaLabel } from '../domain/workbenchLabels'
import { useSyncedModelSelection } from '../domain/useSyncedModelSelection'
import { validatePayloadForCapability } from '../domain/payloadValidation'

export function InvokePanel({
  cap,
  models,
  defaultPayload,
  confirmations,
  riskCheckResult,
  setRiskCheckResult,
  onDone,
}: {
  cap: Capability
  models: Model[]
  defaultPayload?: Record<string, unknown>
  confirmations: Record<string, boolean>
  riskCheckResult: RiskCheckResult | null
  setRiskCheckResult: (r: RiskCheckResult | null) => void
  onDone?: (info?: { history_id?: string | null; capability_id?: string }) => void
}) {
  const required = getRequiredConfirmations(cap)
  const allConfirmed = allConfirmationsSatisfied(required, confirmations)
  const requiresExistingTask = cap.operation_policy.requires_existing_task

  const { model, setModel } = useSyncedModelSelection(models)
  const requiresModelSelection = models.length > 0
  const hasModelSelection = !requiresModelSelection || !!model
  const [body, setBody] = useState<string>(JSON.stringify(defaultPayload ?? {}, null, 2))
  const [result, setResult] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastHistoryId, setLastHistoryId] = useState<string | null>(null)
  const [lastInvokeCapabilityId, setLastInvokeCapabilityId] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [traceEvents, setTraceEvents] = useState<Record<string, unknown>[]>([])
  const [showTrace, setShowTrace] = useState(false)

  // Sync body when defaultPayload prop changes (e.g. capability switch)
  const defaultPayloadText = JSON.stringify(defaultPayload ?? {}, null, 2)
  const [lastDefaultPayloadText, setLastDefaultPayloadText] = useState(defaultPayloadText)
  useEffect(() => {
    if (defaultPayloadText !== lastDefaultPayloadText) {
      setBody(defaultPayloadText)
      setLastDefaultPayloadText(defaultPayloadText)
      if (cap.id === 'tts-async') {
        try {
          const parsed = JSON.parse(defaultPayloadText)
          setTextValue(typeof parsed.text === 'string' ? parsed.text : '')
        } catch {
          setTextValue('')
        }
      }
    }
  }, [cap.id, defaultPayloadText, lastDefaultPayloadText])
  const [riskCheckLoading, setRiskCheckLoading] = useState(false)

  // ── Model → body.model sync ────────────────────────────────────────────────

  function updateJsonBodyField(body: string, key: string, value: unknown): string {
    try {
      const parsed = JSON.parse(body || '{}')
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return body
      return JSON.stringify({ ...parsed, [key]: value }, null, 2)
    } catch {
      return body
    }
  }

  // ── Payload validation ─────────────────────────────────────────────────────

  const validationResult = useMemo(() => {
    try {
      const parsed = JSON.parse(body)
      return validatePayloadForCapability(cap.id, parsed)
    } catch {
      return { valid: false, issues: [{ field: 'body', message: 'JSON 格式错误', severity: 'error' }] }
    }
  }, [cap.id, body])

  // tts-async character count display
  const [textValue, setTextValue] = useState('')
  const maxDefaultChars = cap.operation_policy.max_default_chars ?? null
  const confirmAboveChars = cap.operation_policy.requires_confirmation_above_chars ?? null
  const hardBlockChars = cap.operation_policy.hard_block_above_chars_without_confirm ?? null

  // existing_task_only task_id/file_id input
  const [taskIdValue, setTaskIdValue] = useState('')

  const updateBodyText = (newBody: string) => {
    setBody(newBody)
    if (cap.id === 'tts-async') {
      try {
        const parsed = JSON.parse(newBody)
        setTextValue(typeof parsed.text === 'string' ? parsed.text : '')
      } catch {
        setTextValue('')
      }
    }
  }

  const handleTaskIdChange = (value: string) => {
    setTaskIdValue(value)
    // Update the JSON body with the task_id or file_id
    try {
      const parsed = JSON.parse(body || '{}')
      if (cap.id === 'video-query' || cap.id === 'video-download') {
        parsed.task_id = value
        parsed.file_id = value
      }
      setBody(JSON.stringify(parsed, null, 2))
    } catch {
      // ignore parse errors while typing
    }
  }

  // Parse body to check if task_id/file_id is present
  const hasTaskIdInPayload = (() => {
    try {
      const parsed = JSON.parse(body || '{}')
      return !!(parsed.task_id || parsed.file_id)
    } catch {
      return false
    }
  })()

  const canInvoke = hasModelSelection && allConfirmed && (!requiresExistingTask || hasTaskIdInPayload) && validationResult.valid
  const invokeDisabled = !canInvoke || loading
  const invokeDisabledReason = requiresModelSelection && !model
    ? '请选择模型'
    : !allConfirmed
    ? '请先完成执行前确认'
    : requiresExistingTask && !hasTaskIdInPayload
    ? '该能力仅限已有任务，请填写 task_id 或 file_id'
    : !validationResult.valid
    ? '参数检查未通过'
    : ''

  const submit = async () => {
    if (requiresModelSelection && !model) {
      setErr('当前能力没有可用模型，请检查模型配置或协议过滤结果。')
      return
    }
    setErr(null)
    setResult(null)
    let parsed: Record<string, unknown>
    try {
      parsed = body.trim() ? JSON.parse(body) : {}
    } catch (e) {
      setErr(`JSON 解析失败：${e}`)
      return
    }
    if (model && !('model' in parsed)) parsed.model = model
    const tid = createTraceId()
    setTraceId(tid)
    setTraceEvents([])
    setShowTrace(false)
    setLoading(true)
    let invokeResult: Awaited<ReturnType<typeof invoke>> | null = null
    try {
      invokeResult = await invoke(cap.id, parsed, confirmations, tid)
    } catch (e: any) {
      setLoading(false)
      setErr(`调用失败：${e?.message ?? String(e)}`)
      setLastHistoryId(null)
      setLastInvokeCapabilityId(cap.id)
      onDone?.({ history_id: null, capability_id: cap.id })
      return
    }
    setLoading(false)
    const histId = 'history_id' in invokeResult && typeof invokeResult.history_id === 'string'
      ? invokeResult.history_id
      : null
    setLastHistoryId(histId)
    setLastInvokeCapabilityId(cap.id)

    if ('error' in invokeResult) {
      setErr(`[${invokeResult.status ?? '-'}]: ${invokeResult.message}`)
      if (invokeResult.blocked_reasons?.length) {
        setRiskCheckResult({
          allowed: false,
          blocked_reasons: invokeResult.blocked_reasons,
          required_confirmations: invokeResult.required_confirmations ?? [],
          warnings: invokeResult.warnings ?? [],
        })
      }
      onDone?.({ history_id: histId, capability_id: cap.id })
    } else {
      setResult(invokeResult.data)
      setRiskCheckResult({
        allowed: true,
        blocked_reasons: [],
        required_confirmations: [],
        warnings: [],
      })
      onDone?.({ history_id: histId, capability_id: cap.id })
    }
  }

  const handleDryRun = async () => {
    setErr(null)
    setResult(null)
    let parsed: Record<string, unknown>
    try {
      parsed = body.trim() ? JSON.parse(body) : {}
    } catch (e) {
      setErr(`JSON 解析失败：${e}`)
      return
    }
    if (model && !('model' in parsed)) parsed.model = model
    setRiskCheckLoading(true)
    try {
      const r = await riskCheck(cap.id, parsed, confirmations)
      setRiskCheckResult(r)
    } catch (e) {
      setRiskCheckResult({
        allowed: false,
        blocked_reasons: [`检查失败: ${e instanceof Error ? e.message : String(e)}`],
        required_confirmations: [],
        warnings: [],
      })
    } finally {
      setRiskCheckLoading(false)
    }
  }

  const loadTrace = async (tid: string) => {
    try {
      const data = await getDiagnosticsTrace(tid)
      setTraceEvents(data.events ?? [])
      setShowTrace(true)
    } catch {
      setTraceEvents([])
    }
  }

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
              setBody(prev => updateJsonBodyField(prev, 'model', selected))
            }}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {quotaLabel(m.quota_eligible)} {m.label} · {m.tier}
                {m.context ? ` · ${(m.context / 1000).toFixed(0)}k` : ''}
              </option>
            ))}
          </select>
          {models.find((m) => m.id === model)?.note && (
            <div className="mt-1 text-xs text-slate-500">{models.find((m) => m.id === model)!.note}</div>
          )}
        </div>
      )}

      {/* task_id/file_id input for existing_task_only capabilities */}
      {requiresExistingTask && (
        <div>
          <label className="block text-xs text-slate-600 mb-1">
            {cap.id === 'video-download' ? 'file_id' : 'task_id'}
          </label>
          <input
            type="text"
            value={taskIdValue}
            onChange={(e) => handleTaskIdChange(e.target.value)}
            placeholder={cap.id === 'video-download' ? '请输入 file_id' : '请输入 task_id'}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
          />
          <div className="mt-1 text-xs text-blue-600">
            该能力仅限已有任务，请填写 task_id 或 file_id
          </div>
        </div>
      )}

      {/* tts-async character count display */}
      {cap.id === 'tts-async' && (
        <div className="rounded border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <div>
              <span className="text-slate-500">当前字符数：</span>
              <span className="font-medium">{textValue.length}</span>
            </div>
            {maxDefaultChars != null && (
              <div>
                <span className="text-slate-500">默认测试阈值：</span>
                <span className="text-emerald-600">{maxDefaultChars} 字</span>
              </div>
            )}
            {confirmAboveChars != null && (
              <div>
                <span className="text-slate-500">二次确认阈值：</span>
                <span className={textValue.length > confirmAboveChars ? 'text-amber-600 font-medium' : 'text-slate-700'}>
                  {confirmAboveChars} 字
                </span>
              </div>
            )}
            {hardBlockChars != null && (
              <div>
                <span className="text-slate-500">硬阻断阈值：</span>
                <span className={textValue.length > hardBlockChars ? 'text-red-600 font-medium' : 'text-slate-700'}>
                  {hardBlockChars} 字
                </span>
              </div>
            )}
          </div>
          {textValue.length > (confirmAboveChars ?? Infinity) && (
            <div className="mt-2 pt-2 border-t border-slate-200 text-amber-600">
              当前文本超过二次确认阈值，需要确认后才能执行
            </div>
          )}
          {textValue.length > (hardBlockChars ?? Infinity) && (
            <div className="mt-1 text-red-600">
              当前文本超过硬阻断阈值，无确认时禁止执行
            </div>
          )}
        </div>
      )}

      <div>
        <label className="block text-xs text-slate-600 mb-1">请求体 (JSON)</label>
        <textarea
          value={body}
          onChange={(e) => updateBodyText(e.target.value)}
          rows={10}
          className="w-full font-mono text-xs border border-slate-300 rounded p-2"
        />
      </div>

      {/* Validation error display */}
      {!validationResult.valid && (
        <div className="rounded p-3 text-xs bg-red-50 border border-red-200 text-red-800">
          <div className="font-semibold mb-1">参数检查未通过：</div>
          <ul className="list-disc list-inside space-y-0.5">
            {validationResult.issues.filter(i => i.severity === 'error').map((issue, i) => (
              <li key={i}>{issue.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* RiskGate 检查结果 */}
      {riskCheckResult && (
        <div className={`rounded p-3 text-xs ${
          riskCheckResult.allowed
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          <div className="font-semibold mb-1">
            风险检查：{riskCheckResult.allowed ? '✅ 通过' : '❌ 未通过'}
          </div>
          {riskCheckResult.allowed
            ? <div className="text-emerald-700">当前请求已满足风险/额度/素材确认要求</div>
            : <div className="text-red-700">当前请求会被后端阻断</div>
          }
          {riskCheckResult.blocked_reasons.length > 0 && (
            <div className="mt-1">
              <span className="font-medium">阻断原因：</span>
              <ul className="list-disc list-inside mt-0.5">
                {riskCheckResult.blocked_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {riskCheckResult.required_confirmations.length > 0 && (
            <div className="mt-1">
              <span className="font-medium">需要确认项：</span>
              {riskCheckResult.required_confirmations.join(', ')}
            </div>
          )}
          {riskCheckResult.warnings.length > 0 && (
            <div className="mt-1">
              <span className="font-medium">警告：</span>
              <ul className="list-disc list-inside mt-0.5">
                {riskCheckResult.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleDryRun}
          disabled={riskCheckLoading}
          className={`px-3 py-1.5 rounded text-xs font-medium ${
            riskCheckLoading
              ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
              : allConfirmed
              ? 'bg-emerald-600 text-white hover:bg-emerald-700'
              : 'bg-slate-300 text-slate-500 cursor-not-allowed'
          }`}
        >
          {riskCheckLoading ? '检查中…' : allConfirmed ? '门禁检查 / Dry Run' : '请先完成执行前确认'}
        </button>

        <button
          onClick={submit}
          disabled={invokeDisabled}
          className={`px-4 py-1.5 rounded text-sm font-medium ${
            invokeDisabled
              ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
              : 'bg-slate-900 text-white hover:bg-slate-800'
          }`}
          title={invokeDisabledReason}
        >
          {loading ? '调用中…' : '调用'}
        </button>

        {!allConfirmed && (
          <span className="text-xs text-rose-600">请先完成执行前确认</span>
        )}
        {allConfirmed && !validationResult.valid && (
          <span className="text-xs text-rose-600">参数检查未通过，暂不能执行真实调用</span>
        )}
        {allConfirmed && requiresExistingTask && !hasTaskIdInPayload && (
          <span className="text-xs text-blue-600">请填写 task_id 或 file_id</span>
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
      {lastHistoryId && (
        <div className="rounded border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-700">
          历史已写入：<span className="font-mono">{lastHistoryId}</span>
          <span className="ml-2 text-slate-500">capability_id: {lastInvokeCapabilityId}</span>
        </div>
      )}
      {!lastHistoryId && result !== null && (
        <div className="rounded border border-slate-200 bg-slate-50 p-2 text-xs text-slate-500">
          未收到 history_id，请检查后端是否为最新版本或历史写入是否失败。
        </div>
      )}
      {result !== null && (
        <>
          <AudioPreview data={result} />
          <ImagePreview data={result} />
          <JsonView data={result} />
        </>
      )}
    </div>
  )
}

function AudioPreview({ data }: { data: unknown }) {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  const b64 = typeof d.audio_base64 === 'string' ? (d.audio_base64 as string) : null
  if (!b64) return null
  const fmt = (typeof d.audio_format === 'string' ? d.audio_format : 'mp3') as string
  const src = `data:audio/${fmt};base64,${b64}`
  return (
    <div className="border border-slate-200 rounded p-3 bg-white">
      <div className="text-xs text-slate-500 mb-2">合成结果</div>
      <audio controls src={src} className="w-full" />
      <a href={src} download={`tts.${fmt}`} className="text-xs text-sky-600 hover:underline">下载</a>
    </div>
  )
}

function ImagePreview({ data }: { data: unknown }) {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  const inner = (d.data && typeof d.data === 'object' ? (d.data as Record<string, unknown>) : d)
  const urls = Array.isArray(inner.image_urls) ? (inner.image_urls as string[]) : null
  if (!urls || urls.length === 0) return null
  return (
    <div className="border border-slate-200 rounded p-3 bg-white">
      <div className="text-xs text-slate-500 mb-2">生成图像 ({urls.length})</div>
      <div className="grid grid-cols-2 gap-2">
        {urls.map((u, i) => (
          <a key={i} href={u} target="_blank" rel="noreferrer">
            <img src={u} alt="" className="w-full rounded border border-slate-200" />
          </a>
        ))}
      </div>
    </div>
  )
}
