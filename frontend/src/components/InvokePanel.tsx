import { useState } from 'react'
import { invoke, riskCheck, type Capability, type Model, type RiskCheckResult } from '../api'
import { JsonView } from './JsonView'

function getRequiredConfirmations(cap: Capability): string[] {
  const required: string[] = []
  const bp = cap.billing_policy
  const op = cap.operation_policy
  if (bp.may_charge_extra) required.push('confirm_paid')
  if (bp.billing_category === 'high_cost_confirm_required') required.push('confirm_high_cost')
  if (op.is_destructive) required.push('confirm_destructive')
  if (op.requires_uploaded_asset) required.push('confirm_asset_source')
  if (op.is_long_running) required.push('confirm_long_running')
  if (op.requires_existing_task) required.push('confirm_existing_task')
  if (cap.id === 'tts-async') required.push('confirm_quota')
  return required
}

function allConfirmationsSatisfied(required: string[], confirmations: Record<string, boolean>): boolean {
  return required.every((r) => confirmations[r])
}

export function InvokePanel({
  cap,
  models,
  defaultPayload,
  confirmations,
  riskCheckResult,
  setRiskCheckResult,
}: {
  cap: Capability
  models: Model[]
  defaultPayload?: Record<string, unknown>
  confirmations: Record<string, boolean>
  riskCheckResult: RiskCheckResult | null
  setRiskCheckResult: (r: RiskCheckResult | null) => void
}) {
  const required = getRequiredConfirmations(cap)
  const allConfirmed = allConfirmationsSatisfied(required, confirmations)
  const requiresExistingTask = cap.operation_policy.requires_existing_task

  const [model, setModel] = useState<string>(models[0]?.id ?? '')
  const [body, setBody] = useState<string>(JSON.stringify(defaultPayload ?? {}, null, 2))
  const [result, setResult] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [riskCheckLoading, setRiskCheckLoading] = useState(false)

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

  const canInvoke = allConfirmed && (!requiresExistingTask || hasTaskIdInPayload)
  const invokeDisabled = !canInvoke || loading
  const invokeDisabledReason = !allConfirmed
    ? '请先完成执行前确认'
    : requiresExistingTask && !hasTaskIdInPayload
    ? '该能力仅限已有任务，请填写 task_id 或 file_id'
    : ''

  const submit = async () => {
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
    setLoading(true)
    const r = await invoke(cap.id, parsed, confirmations)
    setLoading(false)
    if ('error' in r) {
      setErr(`[${r.status ?? '-'}]: ${r.message}`)
      if (r.blocked_reasons?.length) {
        setRiskCheckResult({
          allowed: false,
          blocked_reasons: r.blocked_reasons,
          required_confirmations: r.required_confirmations ?? [],
          warnings: r.warnings ?? [],
        })
      }
    } else {
      setResult(r.data)
      setRiskCheckResult({
        allowed: true,
        blocked_reasons: [],
        required_confirmations: [],
        warnings: [],
      })
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

  return (
    <div className="space-y-4">
      {models.length > 0 && (
        <div>
          <label className="block text-xs text-slate-600 mb-1">模型</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.quota_eligible ? '✓配额 ' : '$另计费 '}
                {m.label} · {m.tier}
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

      {/* RiskGate 检查结果 */}
      {riskCheckResult && (
        <div className={`rounded p-3 text-xs ${
          riskCheckResult.allowed
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          <div className="font-semibold mb-1">
            RiskGate 检查结果：{riskCheckResult.allowed ? '✅ 可以执行' : '❌ 已阻断'}
          </div>
          {riskCheckResult.allowed
            ? <div className="text-emerald-700">当前请求已满足执行前确认</div>
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
        {allConfirmed && requiresExistingTask && !hasTaskIdInPayload && (
          <span className="text-xs text-blue-600">请填写 task_id 或 file_id</span>
        )}
      </div>

      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}
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
