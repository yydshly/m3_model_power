import { useEffect, useState, type ReactNode } from 'react'
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

// ── Recursive field extractors ─────────────────────────────────────────────────

const MAX_DEPTH = 5

function findStringField(data: unknown, fieldNames: string[], depth = 0): string {
  if (depth > MAX_DEPTH || data == null) return ''
  if (typeof data === 'string') return ''
  if (typeof data !== 'object') return ''

  const d = data as Record<string, unknown>

  // Check direct fields first
  for (const fn of fieldNames) {
    if (d[fn] && typeof d[fn] === 'string' && d[fn]) return d[fn] as string
  }

  // Recurse into common containers
  for (const key of ['data', 'result', 'output', 'response', 'body', 'content']) {
    if (d[key] != null && typeof d[key] === 'object') {
      const found = findStringField(d[key], fieldNames, depth + 1)
      if (found) return found
    }
  }

  // Recurse into arrays: check first element
  if (Array.isArray(d.items)) {
    const found = findStringField(d.items[0], fieldNames, depth + 1)
    if (found) return found
  }
  if (Array.isArray(d.results)) {
    const found = findStringField(d.results[0], fieldNames, depth + 1)
    if (found) return found
  }
  if (Array.isArray(d.data)) {
    const found = findStringField(d.data[0], fieldNames, depth + 1)
    if (found) return found
  }

  return ''
}

function findArrayField(data: unknown, fieldName: string, depth = 0): unknown[] {
  if (depth > MAX_DEPTH || data == null) return []
  if (typeof data !== 'object') return []

  const d = data as Record<string, unknown>

  if (Array.isArray(d[fieldName])) {
    return d[fieldName] as unknown[]
  }

  // Recurse into common containers
  for (const key of ['data', 'result', 'output', 'response', 'body']) {
    if (d[key] != null && typeof d[key] === 'object') {
      const found = findArrayField(d[key], fieldName, depth + 1)
      if (found.length) return found
    }
  }

  return []
}

function findStringArrayField(data: unknown, fieldName: string, depth = 0): string[] {
  const arr = findArrayField(data, fieldName, depth)
  return arr.filter(item => typeof item === 'string' && item) as string[]
}

function extractTextResult(data: unknown): string {
  return findStringField(data, ['lyrics', 'text', 'content', 'output', 'answer', 'message'])
}

// Fields whose value is semantically an image URL — don't require extension check
const STRONG_IMAGE_URL_FIELDS = new Set([
  'image_url', 'img_url', 'imageUrl', 'imageURL',
  'file_url', 'download_url', 'image_file',
])

const IMAGE_EXT_PATTERN = /\.(jpg|jpeg|png|webp|gif)(\?|\#|$)/i

function looksLikeImageUrl(url: string, fieldName: string): boolean {
  if (STRONG_IMAGE_URL_FIELDS.has(fieldName)) return true
  // For generic 'url'/'image' fields, require image extension
  return IMAGE_EXT_PATTERN.test(url)
}

function extractImageUrl(data: unknown): string {
  // Try top-level fields first
  const d = data as Record<string, unknown>
  if (typeof d.image_url === 'string' && d.image_url) return d.image_url
  if (typeof d.img_url === 'string' && d.img_url) return d.img_url
  if (typeof d.imageUrl === 'string' && d.imageUrl) return d.imageUrl
  if (typeof d.imageURL === 'string' && d.imageURL) return d.imageURL
  if (typeof d.file_url === 'string' && d.file_url) return d.file_url
  if (typeof d.download_url === 'string' && d.download_url) return d.download_url
  if (typeof d.url === 'string' && d.url) {
    const u = d.url as string
    if (looksLikeImageUrl(u, 'url')) return u
  }
  if (typeof d.image === 'string' && d.image) {
    const u = d.image as string
    if (looksLikeImageUrl(u, 'image')) return u
  }
  // Recursive search in nested structures (only strong image URL fields — no extension check needed)
  const found = findStringField(data, ['image_url', 'img_url', 'image_file', 'file_url', 'download_url', 'imageUrl', 'imageURL'], 0)
  if (found) return found
  // Check arrays
  const images = findStringArrayField(data, 'images', 0)
  if (images.length) return images[0]
  const urls = findStringArrayField(data, 'urls', 0)
  if (urls.length) return urls[0]
  const imageUrls = findStringArrayField(data, 'image_urls', 0)
  if (imageUrls.length) return imageUrls[0]
  // Check nested array of objects for url fields
  for (const arrKey of ['images', 'image_urls', 'outputs', 'results', 'data', 'items']) {
    const arr = findArrayField(data, arrKey, 0)
    for (const item of arr) {
      if (typeof item === 'object' && item !== null) {
        const itemObj = item as Record<string, unknown>
        for (const urlKey of ['url', 'image_url', 'img_url', 'file_url', 'download_url']) {
          if (typeof itemObj[urlKey] === 'string' && itemObj[urlKey]) {
            const u = itemObj[urlKey] as string
            if (looksLikeImageUrl(u, urlKey)) return u
          }
        }
      }
      if (typeof item === 'string' && IMAGE_EXT_PATTERN.test(item)) {
        return item
      }
    }
  }
  return found || ''
}

function extractVoiceIds(data: unknown): Array<{ voice_id: string; name?: string }> {
  // Try multiple voice array field names and container paths
  const voiceArrays = [
    findArrayField(data, 'system_voice'),
    findArrayField(data, 'voices'),
    findArrayField(data, 'voice_list'),
    findArrayField(data, 'items'),
  ]

  for (const arr of voiceArrays) {
    if (!arr.length) continue
    const parsed = arr
      .slice(0, 30)
      .map((item) => {
        if (typeof item === 'string') return { voice_id: item }
        if (typeof item === 'object' && item !== null) {
          const v = item as Record<string, unknown>
          // voice_id can be at top level or nested under voice object
          const id = v.voice_id ?? v.voiceId ?? v.id
          if (id) {
            // name preference: voice_name > name
            const rawName = v.voice_name ?? v.name
            return { voice_id: String(id), name: rawName ? String(rawName) : undefined }
          }
        }
        return null
      })
      .filter(Boolean) as Array<{ voice_id: string; name?: string }>

    if (parsed.length) return parsed
  }

  return []
}

type AudioSource = {
  src: string
  kind: 'url' | 'base64'
}

function extractAudioSource(data: unknown, depth = 0): AudioSource | null {
  if (depth > MAX_DEPTH || data == null || typeof data !== 'object') return null

  const d = data as Record<string, unknown>

  // 1. URL type
  for (const key of ['audio_url', 'audio_file', 'url', 'file_url']) {
    const val = d[key]
    if (typeof val === 'string' && val) {
      const lower = val.toLowerCase()
      if (/\.(mp3|wav|ogg|m4a|aac)$/i.test(lower) || lower.startsWith('http')) {
        return { src: val, kind: 'url' }
      }
    }
  }

  // 2. base64 type
  for (const key of ['audio_base64', 'audio']) {
    const val = d[key]
    if (typeof val === 'string' && val.length > 100) {
      if (val.startsWith('data:audio/')) {
        return { src: val, kind: 'base64' }
      }
      return { src: `data:audio/mpeg;base64,${val}`, kind: 'base64' }
    }
  }

  // 3. Recurse into common containers
  for (const key of ['data', 'result', 'output', 'response', 'body', 'content']) {
    const child = d[key]
    if (child && typeof child === 'object') {
      const found = extractAudioSource(child, depth + 1)
      if (found) return found
    }
  }

  // 4. Recurse into arrays
  for (const val of Object.values(d)) {
    if (Array.isArray(val)) {
      for (const item of val) {
        const found = extractAudioSource(item, depth + 1)
        if (found) return found
      }
    }
  }

  return null
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

function clearHandoffFields(capId: string, keys: string[]) {
  const existing = loadHandoff(capId)
  const remaining = Object.fromEntries(
    Object.entries(existing).filter(([k]) => !keys.includes(k))
  )
  if (Object.keys(remaining).length) {
    saveHandoff(capId, remaining)
  } else {
    clearHandoff(capId)
  }
}

// ── Clipboard feedback ─────────────────────────────────────────────────────────

type ClipboardFeedback = 'idle' | 'success' | 'error'

function CopyButton({ text, children }: { text: string; children: ReactNode }) {
  const [fb, setFb] = useState<ClipboardFeedback>('idle')

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setFb('success')
      setTimeout(() => setFb('idle'), 2000)
    }).catch(() => {
      setFb('error')
      setTimeout(() => setFb('idle'), 2000)
    })
  }

  return (
    <button onClick={handleCopy} className="text-sky-600 hover:underline disabled:opacity-50">
      {children}
      {fb === 'success' && <span className="ml-1 text-[10px] text-emerald-600">✓ 已复制</span>}
      {fb === 'error' && <span className="ml-1 text-[10px] text-red-600">✗ 复制失败</span>}
    </button>
  )
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

// ── Recursive template value resolver ───────────────────────────────────────────

function resolveTemplateValue(
  val: unknown,
  values: Record<string, string>,
  schema: FormSchema,
): unknown {
  if (typeof val === 'string') {
    const exact = val.match(/^\{(\w+)\}$/)
    if (exact) return getFieldValue(exact[1], schema, values)
    return val.replace(/\{(\w+)\}/g, (_, k) => {
      const v = getFieldValue(k, schema, values)
      return typeof v === 'string' ? v : String(v)
    })
  }

  if (Array.isArray(val)) {
    return val.map(item => resolveTemplateValue(item, values, schema))
  }

  if (val && typeof val === 'object') {
    return Object.fromEntries(
      Object.entries(val as Record<string, unknown>).map(([k, v]) => [
        k,
        resolveTemplateValue(v, values, schema),
      ])
    )
  }

  return val
}

function buildPayload(
  template: Record<string, unknown>,
  values: Record<string, string>,
  schema: FormSchema,
): Record<string, unknown> {
  return resolveTemplateValue(template, values, schema) as Record<string, unknown>
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
    const audio = extractAudioSource(data)
    return (
      <div className="mb-3 p-3 rounded bg-sky-50 border border-sky-200 text-xs text-sky-700">
        <strong>🎧 音频结果</strong>
        {audio ? (
          <div className="mt-2 space-y-2">
            <audio controls src={audio.src} className="w-full mt-1" />
            <div className="flex items-center gap-2">
              <CopyButton text={audio.src}>
                <span className="text-sky-600 hover:underline">
                  {audio.kind === 'base64' ? '复制音频 Data URL' : '复制音频 URL'}
                </span>
              </CopyButton>
              {audio.kind === 'url' && (
                <a
                  href={audio.src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sky-600 hover:underline"
                >
                  打开链接
                </a>
              )}
              {audio.kind === 'base64' && (
                <span className="text-[10px] text-slate-400">
                  base64 音频已转为浏览器可播放 Data URL
                </span>
              )}
            </div>
          </div>
        ) : (
          <div className="mt-1 text-slate-600">未识别到可播放音频，可查看下方完整 JSON。</div>
        )}
      </div>
    )
  }
  if (resultType === 'image') {
    const imgUrl = extractImageUrl(data)
    return (
      <div className="mb-3 p-3 rounded bg-violet-50 border border-violet-200 text-xs text-violet-700">
        <strong>🖼 图片结果</strong>
        {imgUrl ? (
          <div className="mt-2 space-y-2">
            <img
              src={imgUrl}
              alt="生成图片"
              className="max-h-80 rounded border border-violet-100 bg-white object-contain"
            />
            <div className="flex items-center gap-2">
              <CopyButton text={imgUrl}>复制图片 URL</CopyButton>
              <a
                href={imgUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-600 hover:underline"
              >
                打开图片
              </a>
            </div>
          </div>
        ) : (
          <div className="mt-1 text-slate-600">未识别到图片 URL，可查看下方完整 JSON。</div>
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

  // Fallback: no voice_id could be identified
  if (!voices.length) {
    return (
      <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-xs text-amber-700">
          未识别到 voice_id，请从下方完整 JSON 中手动复制。
        </p>
      </div>
    )
  }

  return (
    <div className="mt-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-slate-600 font-medium">可用音色</span>
        <span className="text-[10px] text-slate-400">点击 voice_id 复制，点击「合成」跳转</span>
      </div>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {voices.map((v, i) => (
          <div key={i} className="flex items-center gap-2 bg-slate-50 rounded px-3 py-2">
            {v.name && (
              <span className="text-xs text-slate-700 truncate flex-[2] min-w-0" title={v.name}>
                {v.name}
              </span>
            )}
            <CopyButton text={v.voice_id}>
              <span className={`text-xs font-mono ${v.name ? 'text-slate-500' : 'text-slate-700'}`}>
                {v.voice_id}
              </span>
            </CopyButton>
            <button
              onClick={() => onUseVoiceId(v.voice_id)}
              className="text-[10px] text-emerald-600 hover:text-emerald-800 whitespace-nowrap ml-auto"
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

  // Business error: hide results, show only error
  if (bizErr) {
    return (
      <div className="mt-3 p-3 rounded bg-red-50 border border-red-200 text-xs text-red-700">
        <strong>业务错误：</strong>{bizErr}
        <details className="mt-2 text-[10px] text-slate-500">
          <summary>完整响应 JSON</summary>
          <pre className="mt-1 text-[10px] overflow-auto max-h-40 whitespace-pre-wrap">
            {JSON.stringify(result.data, null, 2)}
          </pre>
        </details>
      </div>
    )
  }

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
  handoffKeys,
  onBack,
  onChainNavigate,
}: {
  template: RunnerTemplate
  initialValues?: Record<string, string>
  handoffKeys?: string[]
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

  const handleClearHandoffField = (key: string) => {
    handleChange(key, template.form_schema[key]?.default ?? '')
    if (handoffKeys?.includes(key)) {
      clearHandoffFields(template.capability_id, [key])
    }
  }

  // Show handoff banner if any fields came from handoff
  const activeHandoffKeys = (handoffKeys ?? []).filter(k => values[k]?.trim())
  const confirmKey = template.capability_id === 'music-gen'
    ? 'confirm_quota' : template.capability_id === 'image-i2i'
    ? 'confirm_asset_source' : null
  const confirmChecked = confirmKey ? values[confirmKey] === 'true' : null

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
        {/* Handoff visibility bar */}
        {activeHandoffKeys.length > 0 && (
          <div className="mb-3 p-2 rounded bg-sky-50 border border-sky-200 text-xs text-sky-700">
            <strong>已从上一步带入：</strong>{' '}
            {activeHandoffKeys.join('、')}
            <button
              onClick={() => activeHandoffKeys.forEach(k => handleClearHandoffField(k))}
              className="ml-2 text-sky-600 hover:underline"
            >
              清除带入内容
            </button>
          </div>
        )}

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

        {template.capability_id === 'music-gen' && runState !== 'done' && (
          <div className={`mb-3 p-2 rounded border text-xs ${confirmChecked ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-orange-50 border-orange-100 text-orange-600'}`}>
            {confirmChecked
              ? '✓ 已确认，音乐生成会消耗 Token Plan 额度，可执行'
              : '⚠ 该能力会消耗 Token Plan 额度，请勾选确认后再执行'}
          </div>
        )}

        {template.capability_id === 'image-i2i' && runState !== 'done' && (
          <div className={`mb-3 p-2 rounded border text-xs ${confirmChecked ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-orange-50 border-orange-100 text-orange-600'}`}>
            {confirmChecked
              ? '✓ 已确认，参考图片来源合法，可执行'
              : '⚠ 该能力会使用参考图片，请确认图片来源合法后勾选确认'}
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

// ── Main page (loads templates only, all hooks before any returns) ─────────────

export default function CapabilityRunnerPage() {
  const [templates, setTemplates] = useState<Record<string, RunnerTemplate> | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    getRunnerTemplates()
      .then((data) => { setTemplates(data.templates); setLoading(false) })
      .catch((e: any) => { setLoadError(e?.message ?? String(e)); setLoading(false) })
  }, [])

  if (loading) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  if (loadError) return <div className="p-8 text-sm text-red-600">加载失败：{loadError}</div>
  if (!templates) return <div className="p-8 text-sm text-slate-500">无数据</div>

  return <CapabilityRunnerLoaded templates={templates} />
}

// ── Inner page (handles selection, handoff, UI — no loading hooks here) ─────────

function CapabilityRunnerLoaded({ templates }: { templates: Record<string, RunnerTemplate> }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const selected = searchParams.get('capability')

  const handleSelect = (id: string) => {
    setSearchParams({ capability: id })
  }

  const handleBack = () => {
    setSearchParams({})
  }

  const supportedCapabilities = Object.keys(templates)

  // Parse URL query params for handoff pre-fill (e.g. ?capability=tts-sync&voice_id=xxx)
  const queryInitialValues: Record<string, string> = {}
  searchParams.forEach((val, key) => {
    if (key !== 'capability') queryInitialValues[key] = val
  })

  const selectedTemplate = selected ? templates[selected] : null

  // Merge: URL params > sessionStorage handoff
  const selectedId = selected as string
  const storedHandoff = selectedTemplate ? loadHandoff(selectedId) : {}
  const initialValues = selectedTemplate
    ? { ...storedHandoff, ...queryInitialValues }
    : {}

  // handoffKeys: which fields came from sessionStorage handoff (not URL params)
  const handoffKeys = Object.keys(storedHandoff)

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
              handoffKeys={handoffKeys}
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
