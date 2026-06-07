import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { invoke, riskCheck, getRunnerTemplates, type InvokeResult, type RiskCheckResult, type RunnerTemplate } from '../api'
import AssetResultPreview from '../components/AssetResultPreview'

// ── Types ────────────────────────────────────────────────────────────────────

type FormField = {
  type: 'input' | 'textarea' | 'select' | 'number' | 'slider' | 'checkbox'
  label: string
  default: string
  placeholder?: string
  max_chars?: number
  value_type?: 'string' | 'number' | 'boolean'
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: string; label: string }>
}

type FormSchema = Record<string, FormField>

// ── InvokeResult type guard ─────────────────────────────────────────────────────

function isOk(result: InvokeResult): result is { ok: true; data: unknown } {
  return 'ok' in result && result.ok === true
}

// ── Business error detection ────────────────────────────────────────────────────

function extractBusinessError(data: unknown): string | null {
  const d = data as Record<string, unknown>
  const base = d?.base_resp as Record<string, unknown> | undefined
  if (base && typeof base.status_code === 'number' && base.status_code !== 0) {
    return `${base.status_code}: ${(base.status_msg as string) ?? 'MiniMax business error'}`
  }
  return null
}

// ── Result extractors ─────────────────────────────────────────────────────────

function extractTextResult(data: unknown): string {
  const d = data as Record<string, unknown>
  if (typeof d.lyrics === 'string' && d.lyrics) return d.lyrics
  if (typeof d.text === 'string' && d.text) return d.text
  if (typeof d.content === 'string' && d.content) return d.content
  if (typeof d.output === 'string' && d.output) return d.output
  return ''
}

function extractImageUrl(data: unknown): string {
  const d = data as Record<string, unknown>
  if (typeof d.image_url === 'string' && d.image_url) return d.image_url
  if (typeof d.img_url === 'string' && d.img_url) return d.img_url
  if (typeof d.url === 'string' && d.url) {
    const u = d.url as string
    if (/\.(jpg|jpeg|png|webp|gif)$/i.test(u)) return u
  }
  if (d.data && typeof d.data === 'object') {
    const nested = (d.data as Record<string, unknown>).image_url
    if (typeof nested === 'string' && nested) return nested
  }
  if (Array.isArray(d.images)) {
    const first = d.images[0] as Record<string, unknown>
    if (first && typeof first.url === 'string') return first.url as string
  }
  return ''
}

function extractVoiceIds(data: unknown): Array<{ voice_id: string; name?: string }> {
  const d = data as Record<string, unknown>
  const voices = d.voices as Array<Record<string, unknown>> | undefined
  if (!Array.isArray(voices)) return []
  return voices
    .slice(0, 20)
    .map(v => ({
      voice_id: String(v.voice_id ?? ''),
      name: v.name ? String(v.name) : undefined,
    }))
    .filter(v => v.voice_id)
}

function extractAudioUrl(data: unknown): string {
  const d = data as Record<string, unknown>
  if (typeof d.audio_url === 'string' && d.audio_url) return d.audio_url
  if (typeof d.url === 'string' && d.url) {
    const u = d.url as string
    if (/\.(mp3|wav|ogg|m4a|aac)$/i.test(u)) return u
  }
  return ''
}

// ── Session storage handoff ─────────────────────────────────────────────────────

const HANDOFF_PREFIX = 'runner_handoff:'

function saveHandoff(capId: string, values: Record<string, string>) {
  sessionStorage.setItem(`${HANDOFF_PREFIX}${capId}`, JSON.stringify(values))
}

function loadHandoff(capId: string): Record<string, string> {
  try {
    const raw = sessionStorage.getItem(`${HANDOFF_PREFIX}${capId}`)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

function clearHandoff(capId: string) {
  sessionStorage.removeItem(`${HANDOFF_PREFIX}${capId}`)
}

// ── Risk level badge ───────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, { text: string; cls: string }> = {
  safe: { text: '低风险', cls: 'bg-emerald-100 text-emerald-700' },
  low: { text: '低风险', cls: 'bg-emerald-100 text-emerald-700' },
  medium: { text: '中等风险', cls: 'bg-amber-100 text-amber-700' },
  guarded: { text: '需确认', cls: 'bg-amber-100 text-amber-700' },
  quota_sensitive: { text: '额度敏感', cls: 'bg-orange-100 text-orange-700' },
}

function RiskBadge({ level }: { level: string }) {
  const { text, cls } = RISK_BADGE[level] ?? { text: level, cls: 'bg-slate-100 text-slate-600' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${cls}`}>{text}</span>
}

// ── Status indicators ──────────────────────────────────────────────────────────

type RunState = 'idle' | 'checking' | 'running' | 'done' | 'error'

function RunButton({ state, label, onClick, disabled }: { state: RunState; label: string; onClick?: () => void; disabled?: boolean }) {
  if (state === 'checking' || state === 'running') {
    return (
      <button disabled className="px-4 py-2 rounded-lg bg-slate-400 text-white cursor-not-allowed text-sm">
        {state === 'checking' ? '安全检查中…' : '执行中…'}
      </button>
    )
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-lg text-white transition text-sm ${
        disabled
          ? 'bg-slate-300 cursor-not-allowed'
          : 'bg-slate-900 hover:bg-slate-700'
      }`}
    >
      {label}
    </button>
  )
}

// ── Type-aware value extraction ────────────────────────────────────────────────

function getFieldValue(key: string, schema: FormSchema, values: Record<string, string>): unknown {
  const field = schema[key]
  const raw = values[key] ?? field?.default ?? ''

  if (field?.value_type === 'number' || field?.type === 'number' || field?.type === 'slider') {
    const n = Number(raw)
    return Number.isFinite(n) ? n : raw
  }
  if (field?.value_type === 'boolean' || field?.type === 'checkbox') {
    return raw === 'true'
  }
  return raw
}

// ── Type-aware payload builder ─────────────────────────────────────────────────

function buildPayload(
  template: Record<string, unknown>,
  values: Record<string, string>,
  schema: FormSchema,
): Record<string, unknown> {
  const result: Record<string, unknown> = {}

  for (const [key, val] of Object.entries(template)) {
    if (typeof val === 'string') {
      const exact = val.match(/^\{(\w+)\}$/)
      if (exact) {
        result[key] = getFieldValue(exact[1], schema, values)
      } else {
        result[key] = val.replace(/\{(\w+)\}/g, (_, k) => {
          const v = getFieldValue(k, schema, values)
          return typeof v === 'string' ? v : String(v)
        })
      }
    } else if (Array.isArray(val)) {
      result[key] = val.map((item) => {
        if (typeof item === 'string') {
          const exact = item.match(/^\{(\w+)\}$/)
          if (exact) return getFieldValue(exact[1], schema, values)
          return item.replace(/\{(\w+)\}/g, (_, k) => {
            const v = getFieldValue(k, schema, values)
            return typeof v === 'string' ? v : String(v)
          })
        }
        if (typeof item === 'object' && item !== null) {
          const copy: Record<string, unknown> = {}
          for (const [mk, mv] of Object.entries(item as Record<string, unknown>)) {
            if (typeof mv === 'string') {
              const exact = mv.match(/^\{(\w+)\}$/)
              if (exact) copy[mk] = getFieldValue(exact[1], schema, values)
              else copy[mk] = mv.replace(/\{(\w+)\}/g, (_, k) => {
                const v = getFieldValue(k, schema, values)
                return typeof v === 'string' ? v : String(v)
              })
            } else {
              copy[mk] = mv
            }
          }
          return copy
        }
        return item
      })
    } else if (typeof val === 'object' && val !== null) {
      const copy: Record<string, unknown> = {}
      for (const [mk, mv] of Object.entries(val as Record<string, unknown>)) {
        if (typeof mv === 'string') {
          const exact = mv.match(/^\{(\w+)\}$/)
          if (exact) copy[mk] = getFieldValue(exact[1], schema, values)
          else copy[mk] = mv.replace(/\{(\w+)\}/g, (_, k) => {
            const v = getFieldValue(k, schema, values)
            return typeof v === 'string' ? v : String(v)
          })
        } else {
          copy[mk] = mv
        }
      }
      result[key] = copy
    } else {
      result[key] = val
    }
  }
  return result
}

// ── Form renderer ─────────────────────────────────────────────────────────────

function RunnerForm({
  schema,
  values,
  onChange,
}: {
  schema: FormSchema
  values: Record<string, string>
  onChange: (key: string, val: string) => void
}) {
  return (
    <div className="space-y-3">
      {Object.entries(schema).map(([key, field]) => (
        <div key={key}>
          <label className="block text-xs font-medium text-slate-600 mb-1">{field.label}</label>
          {field.type === 'textarea' && (
            <textarea
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-y"
              rows={4}
              value={values[key] ?? field.default}
              placeholder={field.placeholder}
              maxLength={field.max_chars}
              onChange={(e) => onChange(key, e.target.value)}
            />
          )}
          {field.type === 'select' && (
            <select
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 bg-white"
              value={values[key] ?? field.default}
              onChange={(e) => onChange(key, e.target.value)}
            >
              {(field.options ?? []).map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          )}
          {field.type === 'number' && (
            <input
              type="number"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={values[key] ?? field.default}
              placeholder={field.placeholder}
              min={field.min}
              max={field.max}
              step={field.step}
              onChange={(e) => onChange(key, e.target.value)}
            />
          )}
          {field.type === 'slider' && (
            <div className="flex items-center gap-2">
              <input
                type="range"
                className="flex-1"
                value={values[key] ?? field.default}
                min={field.min}
                max={field.max}
                step={field.step}
                onChange={(e) => onChange(key, e.target.value)}
              />
              <span className="text-xs text-slate-500 w-10 text-right">{values[key] ?? field.default}</span>
            </div>
          )}
          {field.type === 'checkbox' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={values[key] === 'true'}
                onChange={(e) => onChange(key, String(e.target.checked))}
                className="w-4 h-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
              />
              <span className="text-xs text-slate-600">{field.placeholder ?? '是'}</span>
            </label>
          )}
          {field.type === 'input' && (
            <input
              type="text"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              value={values[key] ?? field.default}
              placeholder={field.placeholder}
              onChange={(e) => onChange(key, e.target.value)}
            />
          )}
          {field.max_chars && field.type !== 'checkbox' && (
            <div className="text-[10px] text-slate-400 mt-0.5">
              {(values[key] ?? field.default).length} / {field.max_chars}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Result banner ──────────────────────────────────────────────────────────────

function ResultBanner({ resultType, data }: { resultType: string; data: unknown }) {
  if (resultType === 'audio') {
    return (
      <div className="mb-3 p-3 rounded bg-sky-50 border border-sky-200 text-xs text-sky-700">
        <strong>🎧 音频结果</strong>
        {extractAudioUrl(data) && <div className="mt-1 text-slate-600">可直接播放，或右键另存为下载。</div>}
      </div>
    )
  }
  if (resultType === 'image') {
    return (
      <div className="mb-3 p-3 rounded bg-violet-50 border border-violet-200 text-xs text-violet-700">
        <strong>🖼 图片结果</strong>
        {extractImageUrl(data) && (
          <div className="mt-1">
            <button
              onClick={() => navigator.clipboard.writeText(extractImageUrl(data))}
              className="text-sky-600 hover:underline"
            >
              复制图片 URL
            </button>
          </div>
        )}
      </div>
    )
  }
  if (resultType === 'voice_list') {
    return (
      <div className="mb-3 p-3 rounded bg-amber-50 border border-amber-200 text-xs text-amber-700">
        <strong>🎙 音色列表</strong>
        <div className="mt-1">点击 voice_id 可直接复制，或使用「用此音色合成」跳转到语音合成。</div>
      </div>
    )
  }
  if (resultType === 'text') {
    return (
      <div className="mb-3 p-3 rounded bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">
        <strong>📝 文本结果</strong>
      </div>
    )
  }
  if (resultType === 'chat') {
    return (
      <div className="mb-3 p-3 rounded bg-blue-50 border border-blue-200 text-xs text-blue-700">
        <strong>💬 模型回复</strong>
      </div>
    )
  }
  return null
}

// ── Voice list hint with copy ───────────────────────────────────────────────────

function VoiceListHint({ data, onUseVoiceId }: { data: unknown; onUseVoiceId: (vid: string) => void }) {
  const voices = extractVoiceIds(data)
  if (!voices.length) return null

  return (
    <div className="mt-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-slate-600 font-medium">voice_id 复制</span>
        <span className="text-[10px] text-slate-400">点击 voice_id 复制，点击「合成」跳转</span>
      </div>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {voices.map((v, i) => (
          <div key={i} className="flex items-center gap-2 bg-slate-50 rounded px-2 py-1.5">
            <button
              onClick={() => navigator.clipboard.writeText(v.voice_id)}
              className="text-xs font-mono text-sky-600 hover:text-sky-800 hover:underline"
            >
              {v.voice_id}
            </button>
            {v.name && <span className="text-[10px] text-slate-400 truncate flex-1">{v.name}</span>}
            <button
              onClick={() => onUseVoiceId(v.voice_id)}
              className="text-[10px] text-emerald-600 hover:text-emerald-800 whitespace-nowrap"
            >
              用此音色合成 →
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Chain handoff button ───────────────────────────────────────────────────────

function ChainButton({
  label,
  onClick,
  disabled,
  variant = 'primary',
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg transition ${
        disabled
          ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
          : variant === 'primary'
            ? 'bg-slate-900 text-white hover:bg-slate-700'
            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
      }`}
    >
      {label}
    </button>
  )
}

// ── Result renderer ───────────────────────────────────────────────────────────

function InvokeResultView({
  result,
  resultType,
  template,
  onChain,
}: {
  result: InvokeResult
  resultType: string
  template: RunnerTemplate
  onChain: (capId: string, values: Record<string, string>) => void
}) {
  if (!isOk(result)) {
    return (
      <div className="mt-3 p-3 rounded bg-red-50 border border-red-200 text-xs text-red-700">
        <strong>调用失败：</strong> {result.message}
        {result.blocked_reasons && result.blocked_reasons.length > 0 && (
          <div className="mt-1">阻断原因：{result.blocked_reasons.join('；')}</div>
        )}
        {result.required_confirmations && result.required_confirmations.length > 0 && (
          <div className="mt-1">需要确认：{result.required_confirmations.join('、')}</div>
        )}
      </div>
    )
  }

  const bizErr = extractBusinessError(result.data)

  return (
    <div className="mt-4">
      <ResultBanner resultType={resultType} data={result.data} />

      {/* Chain buttons per capability */}
      {resultType === 'voice_list' && (
        <VoiceListHint
          data={result.data}
          onUseVoiceId={(vid) => onChain('tts-sync', { voice_id: vid })}
        />
      )}

      {resultType === 'text' && template.next_steps.some(ns => ns.capability_id === 'music-gen') && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-2">下一步：</p>
          {(() => {
            const lyrics = extractTextResult(result.data)
            const ns = template.next_steps.find(n => n.capability_id === 'music-gen')
            if (!ns) return null
            return (
              <div className="flex items-center gap-2">
                <ChainButton
                  label={ns.label}
                  onClick={() => onChain('music-gen', lyrics ? { lyrics } : {})}
                  disabled={!lyrics}
                  variant="primary"
                />
                {!lyrics && (
                  <span className="text-[10px] text-slate-400">未识别到歌词，请手动复制后粘贴</span>
                )}
              </div>
            )
          })()}
        </div>
      )}

      {resultType === 'image' && template.next_steps.some(ns => ns.capability_id === 'image-i2i') && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-2">下一步：</p>
          {(() => {
            const imgUrl = extractImageUrl(result.data)
            const ns = template.next_steps.find(n => n.capability_id === 'image-i2i')
            if (!ns) return null
            return (
              <div className="flex items-center gap-2">
                <ChainButton
                  label={ns.label}
                  onClick={() => onChain('image-i2i', imgUrl ? { img_url: imgUrl } : {})}
                  disabled={!imgUrl}
                  variant="primary"
                />
                {!imgUrl && (
                  <span className="text-[10px] text-slate-400">未识别到图片 URL，请手动复制后粘贴</span>
                )}
              </div>
            )
          })()}
        </div>
      )}

      <div className="mt-3">
        <AssetResultPreview data={result.data} />
      </div>

      {bizErr && (
        <div className="mt-2 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
          <strong>业务错误：</strong>{bizErr}
        </div>
      )}
    </div>
  )
}

// ── Helper: get default values from schema ───────────────────────────────────

function getDefaultValues(schema: FormSchema): Record<string, string> {
  return Object.fromEntries(
    Object.entries(schema).map(([key, field]) => [key, field.default ?? ''])
  )
}

// ── Execution guard logic ─────────────────────────────────────────────────────

function getExecutionDisabled(template: RunnerTemplate, values: Record<string, string>): string | null {
  if (template.capability_id === 'tts-sync' && !values['voice_id']?.trim()) {
    return '请先填写 voice_id（可从音色列表获取）'
  }
  if (template.capability_id === 'music-gen') {
    if (!values['lyrics']?.trim()) return '请填写歌词'
    if (values['confirm_quota'] !== 'true') return '请勾选「确认额度消耗」后才能执行'
  }
  if (template.capability_id === 'image-i2i') {
    if (!values['img_url']?.trim()) return '请填写参考图片 URL'
    if (values['confirm_asset_source'] !== 'true') return '请勾选「确认图片来源合法」后才能执行'
  }
  return null
}

// ── Capability card ───────────────────────────────────────────────────────────

function CapabilityCard({
  template,
  initialValues,
  onBack,
  onChainNavigate,
}: {
  template: RunnerTemplate
  initialValues?: Record<string, string>
  onBack: () => void
  onChainNavigate: (capId: string) => void
}) {
  const schema = template.form_schema as FormSchema
  const defaults = getDefaultValues(schema)
  const [values, setValues] = useState<Record<string, string>>(() => ({ ...defaults, ...(initialValues ?? {}) }))
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const resultType = template.result_type ?? 'text'
  const disabledReason = getExecutionDisabled(template, values)

  const handleChange = (key: string, val: string) => setValues((v) => ({ ...v, [key]: val }))

  const handleRun = async () => {
    if (disabledReason) return
    const payload = buildPayload(template.payload_template as Record<string, unknown>, values, schema)
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    setErrorMessage(null)
    try {
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { setRunState('error'); return }
      setRunState('running')
      const res = await invoke(template.capability_id, payload, {})

      if (isOk(res)) {
        const bizErr = extractBusinessError(res.data)
        if (bizErr) {
          setErrorMessage(bizErr)
          setResult(res)
          setRunState('error')
          return
        }
      }

      setResult(res)
      setRunState('done')
    } catch (e: any) {
      setErrorMessage(e?.message ?? String(e))
      setRunState('error')
    }
  }

  const handleChain = (capId: string, handoffValues: Record<string, string>) => {
    // Save handoff for the target capability
    const existing = loadHandoff(capId)
    saveHandoff(capId, { ...existing, ...handoffValues })
    onChainNavigate(capId)
  }

  const RUN_LABELS: Record<string, string> = {
    'lyrics-gen': '生成歌词',
    'tts-sync': '生成语音',
    'voice-list': '查询音色',
    'image-t2i': '生成图片',
    'chat-openai': '发送',
    'music-gen': '生成音乐',
    'image-i2i': '生成图片',
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h2 className="text-base font-semibold text-slate-900">{template.label}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{template.description}</p>
          </div>
          <RiskBadge level={template.risk_level} />
        </div>
        {template.suitable_for.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {template.suitable_for.map((s) => (
              <span key={s} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{s}</span>
            ))}
          </div>
        )}
      </div>
      <div className="px-5 py-4">
        {/* Guard warnings */}
        {template.capability_id === 'tts-sync' && !values['voice_id']?.trim() && (
          <div className="mb-3 p-3 rounded bg-amber-50 border border-amber-200 text-xs text-amber-700">
            <strong>请先查询音色：</strong>voice_id 为空无法合成语音。
            <br />
            <Link
              to="/capability-runner?capability=voice-list"
              className="text-sky-600 hover:underline mt-1 inline-block"
            >
              → 去查询音色
            </Link>
          </div>
        )}

        {resultType === 'image' && runState !== 'done' && (
          <div className="mb-3 p-2 rounded bg-violet-50 border border-violet-100 text-xs text-violet-600">
            💡 此能力会消耗 Token Plan 额度，请确认后再执行。
          </div>
        )}

        {template.capability_id === 'music-gen' && runState !== 'done' && (
          <div className="mb-3 p-2 rounded bg-orange-50 border border-orange-100 text-xs text-orange-600">
            💡 音乐生成会消耗 Token Plan 额度，请勾选确认后再执行。
          </div>
        )}

        {Object.keys(schema).length > 0 && (
          <div className="mb-4">
            <RunnerForm schema={schema} values={values} onChange={handleChange} />
          </div>
        )}

        {template.capability_id === 'voice-list' && (
          <div className="text-xs text-slate-500 mb-4">此能力无需参数，直接查询可用音色列表。</div>
        )}

        <div className="flex items-center gap-3">
          <RunButton
            state={runState}
            label={RUN_LABELS[template.capability_id] ?? '执行'}
            onClick={handleRun}
            disabled={!!disabledReason}
          />
          <span className="text-xs text-slate-400">执行前会先进行安全检查</span>
        </div>

        {disabledReason && runState === 'idle' && (
          <div className="mt-2 text-[10px] text-slate-400">{disabledReason}</div>
        )}

        {runState === 'done' && (
          <div className="mt-3 text-xs text-emerald-600">✓ 执行完成</div>
        )}
        {runState === 'error' && (
          <div className="mt-3 text-xs text-red-600">
            ✗ {errorMessage ? `执行失败：${errorMessage}` : '执行失败（被安全检查阻断或发生错误）'}
          </div>
        )}
        {riskResult && !riskResult.allowed && (
          <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
            <strong>安全检查阻断：</strong> {riskResult.blocked_reasons.join('；')}
            {riskResult.required_confirmations.length > 0 && (
              <div className="mt-1">需要确认：{riskResult.required_confirmations.join('、')}</div>
            )}
          </div>
        )}
        {result && (
          <InvokeResultView
            result={result}
            resultType={resultType}
            template={template}
            onChain={handleChain}
          />
        )}

        <div className="mt-3 pt-3 border-t border-slate-100">
          <button onClick={onBack} className="text-[10px] text-slate-400 hover:text-slate-600">
            ← 重新选择
          </button>
          <span className="mx-2 text-slate-200">|</span>
          <Link
            to={`/test-console?capability=${template.capability_id}`}
            className="text-[10px] text-slate-400 hover:text-slate-600"
          >
            高级测试 →
          </Link>
        </div>
      </div>
    </div>
  )
}

// ── Capability selector ────────────────────────────────────────────────────────

const CAPABILITY_EMOJI: Record<string, string> = {
  'lyrics-gen': '🎵',
  'tts-sync': '🎙️',
  'voice-list': '🎙️',
  'image-t2i': '🖼️',
  'chat-openai': '💬',
  'music-gen': '🎶',
  'image-i2i': '🖼️',
}

const CAPABILITY_FAMILY: Record<string, string> = {
  'lyrics-gen': 'music',
  'tts-sync': 'voice',
  'voice-list': 'voice',
  'image-t2i': 'vision',
  'chat-openai': 'chat',
  'music-gen': 'music',
  'image-i2i': 'vision',
}

const CAPABILITY_LABEL: Record<string, string> = {
  'lyrics-gen': '歌词生成',
  'tts-sync': '语音合成',
  'voice-list': '音色列表',
  'image-t2i': '图片生成',
  'chat-openai': '文本对话',
  'music-gen': '音乐生成',
  'image-i2i': '图生图',
}

function CapabilitySelector({ onSelect, capabilities }: { onSelect: (id: string) => void; capabilities: string[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {capabilities.map((cap) => (
        <button
          key={cap}
          onClick={() => onSelect(cap)}
          className="rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm p-4 text-left transition"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{CAPABILITY_EMOJI[cap] ?? '📦'}</span>
            <span className="font-semibold text-slate-900 text-sm">{CAPABILITY_LABEL[cap] ?? cap}</span>
          </div>
          <div className="text-xs text-slate-500">{CAPABILITY_FAMILY[cap] ?? 'unknown'}</div>
        </button>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CapabilityRunnerPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selected = searchParams.get('capability')

  const [templates, setTemplates] = useState<Record<string, RunnerTemplate> | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    getRunnerTemplates()
      .then((data) => { setTemplates(data.templates); setLoading(false) })
      .catch((e: any) => { setLoadError(e?.message ?? String(e)); setLoading(false) })
  }, [])

  const handleSelect = (id: string) => {
    setSearchParams({ capability: id })
  }

  const handleBack = () => {
    setSearchParams({})
  }

  if (loading) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  if (loadError) return <div className="p-8 text-sm text-red-600">加载失败：{loadError}</div>
  if (!templates) return <div className="p-8 text-sm text-slate-500">无数据</div>

  const supportedCapabilities = Object.keys(templates)

  // Parse URL query params for handoff pre-fill (e.g. ?capability=tts-sync&voice_id=xxx)
  const queryInitialValues: Record<string, string> = {}
  searchParams.forEach((val, key) => {
    if (key !== 'capability') queryInitialValues[key] = val
  })

  const selectedTemplate = selected ? templates[selected] : null

  // Merge: URL params > sessionStorage handoff
  const selectedId = selected as string
  const initialValues = selectedTemplate
    ? { ...loadHandoff(selectedId), ...queryInitialValues }
    : {}

  // Clear handoff after loading to prevent stale reuse
  useEffect(() => {
    if (selected) clearHandoff(selectedId)
  }, [selectedId])

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">能力体验</h1>
        <p className="text-sm text-slate-600 mt-1">
          选择一个能力，使用默认输入体验 MiniMax Token Plan 的实际效果；部分能力结果可以继续带入下一步流程。
        </p>
      </div>

      {!selected ? (
        <CapabilitySelector onSelect={handleSelect} capabilities={supportedCapabilities} />
      ) : (
        <div className="space-y-6">
          {selectedTemplate ? (
            <CapabilityCard
              key={selected}
              template={selectedTemplate}
              initialValues={initialValues}
              onBack={handleBack}
              onChainNavigate={handleSelect}
            />
          ) : (
            <div className="text-sm text-slate-500">
              不支持的 Runner 能力：{selected}（支持的：{supportedCapabilities.join(' / ')}）
            </div>
          )}
        </div>
      )}
    </div>
  )
}
