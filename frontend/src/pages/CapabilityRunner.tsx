import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { invoke, riskCheck, uploadCapability, getRunnerTemplates, getCapabilityHistory, type InvokeResult, type RiskCheckResult, type RunnerTemplate, type TestConsoleHistoryItem } from '../api'
import AssetResultPreview from '../components/AssetResultPreview'
import InvocationHistoryPanel from '../components/InvocationHistoryPanel'
import UsageCostExplainer from '../components/UsageCostExplainer'
import FileResultPreview from '../components/FileResultPreview'
import AsyncTaskResultPreview from '../components/AsyncTaskResultPreview'
import ChatResultPreview from '../components/ChatResultPreview'
import { extractAudioSource, audioSourceToSrc } from '../components/assetResultUtils'
import { saveRunnerSession, loadRunnerSession, type RunnerSession } from '../domain/runnerSession'

// ── Types ────────────────────────────────────────────────────────────────────

type FormField = {
  type: 'input' | 'textarea' | 'select' | 'number' | 'slider' | 'checkbox' | 'file'
  label: string
  default: string
  placeholder?: string
  max_chars?: number
  value_type?: 'string' | 'number' | 'boolean'
  min?: number
  max?: number
  step?: number
  options?: Array<{ value: string; label: string }>
  note?: string
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
  'image_file',
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
  if (typeof d.file_url === 'string' && d.file_url && looksLikeImageUrl(d.file_url, 'file_url')) return d.file_url
  if (typeof d.download_url === 'string' && d.download_url && looksLikeImageUrl(d.download_url, 'download_url')) return d.download_url
  if (typeof d.url === 'string' && d.url) {
    const u = d.url as string
    if (looksLikeImageUrl(u, 'url')) return u
  }
  if (typeof d.image === 'string' && d.image) {
    const u = d.image as string
    if (looksLikeImageUrl(u, 'image')) return u
  }
  // Recursive search in nested structures (only strong image URL fields — no extension check needed)
  const found = findStringField(data, ['image_url', 'img_url', 'image_file', 'imageUrl', 'imageURL'], 0)
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
        for (const urlKey of ['url', 'image_url', 'img_url']) {
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

function buildResultSummary(
  data: unknown,
  resultType: string,
): RunnerSession['resultSummary'] {
  if (!data || typeof data !== 'object') return undefined
  const d = data as Record<string, unknown>
  const base = d.base_resp as Record<string, unknown> | undefined
  const ok = !base || (base.status_code as number) === 0

  const summary: RunnerSession['resultSummary'] = { ok }

  if (resultType === 'text' || resultType === 'chat') {
    const text = extractTextResult(data)
    if (text) summary.textPreview = text.slice(0, 200)
  }
  if (resultType === 'image') {
    const url = extractImageUrl(data)
    if (url) summary.imageUrl = url
  }
  if (resultType === 'audio') {
    const audio = extractAudioSource(data)
    if (audio?.kind === 'url' && audio.src) summary.audioUrl = audio.src
    if (audio?.kind === 'data_url' && audio.src) summary.audioUrl = audio.src.slice(0, 100)
  }
  if (resultType.startsWith('file_')) {
    const fid = d.file_id
    if (typeof fid === 'string') summary.fileId = fid
    if (typeof d.filename === 'string') summary.filename = d.filename
    if (typeof d.mime_type === 'string') summary.mimeType = d.mime_type
  }

  return summary
}

function buildPayload(
  template: Record<string, unknown>,
  values: Record<string, string>,
  schema: FormSchema,
): Record<string, unknown> {
  return resolveTemplateValue(template, values, schema) as Record<string, unknown>
}

function applyI2IPromptMode(
  payload: Record<string, unknown>,
  values: Record<string, string>,
  capabilityId: string,
): Record<string, unknown> {
  if (capabilityId !== 'image-i2i') return payload

  const mode = values['reference_mode'] ?? 'subject'
  const prompt = typeof payload.prompt === 'string' ? payload.prompt : ''

  const prefixMap: Record<string, string> = {
    subject: '尽量保持参考图主体特征。',
    style: '主要参考参考图的画风、色彩和氛围，不要求保持原图主体。',
    variation: '基于参考图生成变体，允许主体、构图和细节发生较大变化。',
  }

  const prefix = prefixMap[mode] ?? prefixMap.subject
  return {
    ...payload,
    prompt: `${prefix}${prompt}`,
  }
}

// ── Form renderer ─────────────────────────────────────────────────────────────

function RunnerForm({
  schema,
  values,
  onChange,
  files,
  onFileChange,
}: {
  schema: FormSchema
  values: Record<string, string>
  onChange: (key: string, val: string) => void
  files?: Record<string, File | null>
  onFileChange?: (key: string, file: File | null) => void
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
          {field.type === 'file' && (
            <div>
              <input
                type="file"
                accept=".txt,.md,.json,.csv"
                className="text-xs text-slate-600 file:mr-3 file:mb-1 file:px-3 file:py-1 file:rounded file:border-0 file:text-xs file:bg-sky-50 file:text-sky-700 hover:file:bg-sky-100"
                onChange={(e) => {
                  const file = e.target.files?.[0] ?? null
                  onFileChange?.(key, file)
                }}
              />
              {files?.[key] && (
                <div className="mt-1 text-xs text-slate-500">
                  已选择：{files[key]!.name}（{(files[key]!.size / 1024).toFixed(1)} KB）
                </div>
              )}
              <div className="mt-1 text-[10px] text-slate-400">{field.placeholder}</div>
            </div>
          )}
          {field.max_chars && field.type !== 'checkbox' && field.type !== 'file' && (
            <div className="text-[10px] text-slate-400 mt-0.5">
              {(values[key] ?? field.default).length} / {field.max_chars}
            </div>
          )}
          {field.note && (
            <div className="text-[10px] text-slate-400 mt-1">
              {field.note}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Image i2i compare ──────────────────────────────────────────────────────────

function ImageComparePreview({ referenceUrl, generatedUrl }: { referenceUrl: string; generatedUrl: string }) {
  return (
    <div className="mb-3 p-3 rounded bg-violet-50 border border-violet-200">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-violet-700">🖼 图片结果对比</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Reference image */}
        <div className="space-y-1">
          <p className="text-[10px] text-slate-500 font-medium">参考图</p>
          <img
            src={referenceUrl}
            alt="参考图"
            className="w-full max-h-56 rounded border border-slate-200 bg-white object-contain"
            onError={e => {
              (e.target as HTMLImageElement).style.display = 'none'
            }}
          />
          <div className="flex gap-2">
            <CopyButton text={referenceUrl}>
              <span className="text-[10px] text-sky-600 hover:underline">复制 URL</span>
            </CopyButton>
            <a
              href={referenceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-sky-600 hover:underline"
            >
              打开
            </a>
          </div>
        </div>
        {/* Generated image */}
        <div className="space-y-1">
          <p className="text-[10px] text-slate-500 font-medium">生成图</p>
          <img
            src={generatedUrl}
            alt="生成图"
            className="w-full max-h-56 rounded border border-violet-200 bg-white object-contain"
            onError={e => {
              (e.target as HTMLImageElement).style.display = 'none'
            }}
          />
          <div className="flex gap-2">
            <CopyButton text={generatedUrl}>
              <span className="text-[10px] text-sky-600 hover:underline">复制 URL</span>
            </CopyButton>
            <a
              href={generatedUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-sky-600 hover:underline"
            >
              打开
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Result banner ──────────────────────────────────────────────────────────────

function AudioBanner({ data, audioSource: providedAudio }: { data: unknown; audioSource?: ReturnType<typeof extractAudioSource> | null }) {
  const audio = providedAudio ?? extractAudioSource(data)
  const audioRef = useRef<HTMLAudioElement>(null)
  const [loadError, setLoadError] = useState(false)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  // For hex sources, create a blob URL on mount
  useEffect(() => {
    if (audio?.kind === 'hex') {
      const url = audioSourceToSrc(audio)
      setBlobUrl(url)
      return () => URL.revokeObjectURL(url)
    }
    if (audio?.kind === 'base64') {
      const url = audioSourceToSrc(audio)
      setBlobUrl(url)
      return () => URL.revokeObjectURL(url)
    }
    return undefined
  }, [audio])

  if (!audio) {
    return (
      <div className="mb-3 p-3 rounded bg-sky-50 border border-sky-200 text-xs text-sky-700">
        <strong>🎧 音频结果</strong>
        <div className="mt-1 text-slate-600">未识别到可播放音频，可查看下方完整 JSON。</div>
      </div>
    )
  }

  if (audio.kind === 'task') {
    const fmtBytes = (b: number) => b < 1024 * 1024 ? `${(b / 1024).toFixed(1)} KB` : `${(b / (1024 * 1024)).toFixed(2)} MB`
    return (
      <div className="mb-3 p-3 rounded bg-orange-50 border border-orange-200 text-xs text-orange-700">
        <strong>🎵 音乐生成任务状态</strong>
        <div className="mt-1 font-medium">{audio.message}</div>
        <div className="mt-2 space-y-1 text-xs text-slate-600">
          {audio.duration_sec !== undefined && <div>时长：{audio.duration_sec.toFixed(1)} 秒</div>}
          {audio.sample_rate !== undefined && <div>采样率：{audio.sample_rate} Hz</div>}
          {audio.channel !== undefined && <div>声道：{audio.channel === 2 ? '立体声' : audio.channel === 1 ? '单声道' : audio.channel}</div>}
          {audio.file_size_bytes !== undefined && <div>文件大小：{fmtBytes(audio.file_size_bytes)}</div>}
        </div>
        <p className="text-[10px] text-slate-400 mt-2">
          当前响应未包含可直接播放的音频数据。状态 {audio.status} 表示任务已提交，请通过结果查询接口获取音频。
        </p>
      </div>
    )
  }

  const src = blobUrl ?? (audio.kind === 'url' || audio.kind === 'data_url' ? audio.src : '')

  return (
    <div className="mb-3 p-3 rounded bg-sky-50 border border-sky-200 text-xs text-sky-700">
      <strong>🎧 音频结果</strong>
      <div className="mt-2 space-y-2">
        <audio
          ref={audioRef}
          controls
          src={src}
          className="w-full mt-1"
          onLoadedMetadata={() => {
            const el = audioRef.current
            if (el && (isNaN(el.duration) || el.duration === 0)) setLoadError(true)
          }}
          onError={() => setLoadError(true)}
        />
        {loadError && (
          <p className="text-[10px] text-red-500">
            浏览器未能解析该音频。可能是编码格式不支持，或接口返回的不是最终音频文件。请查看完整 JSON。
          </p>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          <CopyButton text={src}>
            <span className="text-sky-600 hover:underline">
              {audio.kind === 'base64' || audio.kind === 'hex' ? '复制 Data URL' : '复制音频 URL'}
            </span>
          </CopyButton>
          {(audio.kind === 'url') && (
            <a href={src} target="_blank" rel="noopener noreferrer" className="text-sky-600 hover:underline">
              打开链接
            </a>
          )}
          {(audio.kind === 'base64' || audio.kind === 'hex') && (
            <span className="text-[10px] text-slate-400">已转为浏览器可播放 Data URL</span>
          )}
        </div>
      </div>
    </div>
  )
}

function ResultBanner({ resultType, data, template, values }: { resultType: string; data: unknown; template?: RunnerTemplate; values?: Record<string, string> }) {
  if (resultType === 'audio') {
    return <AudioBanner data={data} />
  }
  if (resultType === 'image') {
    // image-i2i: show reference vs generated comparison when we have the reference URL
    const generatedUrl = extractImageUrl(data)
    const isI2I = template?.capability_id === 'image-i2i'
    const refUrl = isI2I && values?.img_url ? values.img_url : null

    if (isI2I && generatedUrl && refUrl) {
      return (
        <>
          <ImageComparePreview referenceUrl={refUrl} generatedUrl={generatedUrl} />
          <div className="mt-2 p-2 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-700">
            <strong>⚠️ 图生图结果不保证完全保持主体。</strong>如果生成图主体变化较大，请尝试：
            <ol className="mt-1 ml-3 list-decimal list-inside space-y-0.5">
              <li>改写提示词，明确「保持原图主体」</li>
              <li>使用更具体的主体描述</li>
              <li>更换参考模式（主体参考 / 风格参考 / 变体）</li>
              <li>重新生成</li>
            </ol>
          </div>
        </>
      )
    }

    return (
      <div className="mb-3 p-3 rounded bg-violet-50 border border-violet-200 text-xs text-violet-700">
        <strong>🖼 图片结果</strong>
        {generatedUrl ? (
          <div className="mt-2 space-y-2">
            <img
              src={generatedUrl}
              alt="生成图片"
              className="max-h-80 rounded border border-violet-100 bg-white object-contain"
            />
            <div className="flex items-center gap-2">
              <CopyButton text={generatedUrl}>复制图片 URL</CopyButton>
              <a href={generatedUrl} target="_blank" rel="noopener noreferrer" className="text-sky-600 hover:underline">
                打开图片
              </a>
            </div>
          </div>
        ) : (
          <div className="mt-1 text-slate-600">未识别到生成图 URL，请查看完整 JSON。</div>
        )}
        {isI2I && !refUrl && generatedUrl && (
          <div className="mt-2 text-[10px] text-amber-600">未识别到参考图 URL，请检查 img_url 或完整 JSON。</div>
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
    // ChatResultPreview is rendered by InvokeResultView instead
    return null
  }
  if (resultType === 'file_upload' || resultType === 'file_list' || resultType === 'file_detail' || resultType === 'file_content') {
    // FileResultPreview handles all file result types
    return null
  }
  if (resultType === 'async_task') {
    // AsyncTaskResultPreview handles async_task in InvokeResultView
    return null
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
  values,
}: {
  result: InvokeResult
  resultType: string
  template: RunnerTemplate
  onChain: (capId: string, values: Record<string, string>) => void
  values?: Record<string, string>
}) {
  if (!isOk(result)) {
    return (
      <div className="mt-3 p-3 rounded bg-red-50 border border-red-200 text-xs text-red-700">
        <strong>调用失败：</strong> {result.message}
        <details className="mt-1 border border-red-200 rounded">
          <summary className="px-2 py-1 cursor-pointer text-[10px] text-red-600 hover:text-red-800">
            调试信息
          </summary>
          <div className="px-2 pb-2 space-y-1">
            {result.blocked_reasons && result.blocked_reasons.length > 0 && (
              <div>阻断原因：{result.blocked_reasons.join('；')}</div>
            )}
            {result.required_confirmations && result.required_confirmations.length > 0 && (
              <div>需要确认：{result.required_confirmations.join('、')}</div>
            )}
          </div>
        </details>
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

  // Extract audio once so we can pass it to both ResultBanner and AssetResultPreview
  const audioSource = resultType === 'audio' ? extractAudioSource(result.data) : null

  // Determine dedupe params for AssetResultPreview to avoid double-rendering
  const assetPreviewProps: React.ComponentProps<typeof AssetResultPreview> =
    resultType === 'audio'
      ? { data: result.data, audioSource, skipAudioTaskCard: true }
      : resultType === 'image'
      ? { data: result.data, skipPrimaryKinds: ['image'] }
      : { data: result.data }

  return (
    <div className="mt-4">
      {resultType === 'audio'
        ? <AudioBanner data={result.data} audioSource={audioSource} />
        : <ResultBanner resultType={resultType} data={result.data} template={template} values={values} />}

      {/* Chain buttons per capability */}
      {resultType === 'voice_list' && (
        <>
          <VoiceListHint
            data={result.data}
            onUseVoiceId={(vid) => onChain('tts-sync', { voice_id: vid })}
          />
          {/* Always show next step suggestion for voice_list */}
          {template.next_steps.some(ns => ns.capability_id === 'tts-sync') && (
            <div className="mt-3 pt-3 border-t border-slate-100">
              <p className="text-xs text-slate-500 mb-2">建议下一步：</p>
              <div className="flex items-center gap-2">
                <ChainButton
                  label="语音合成"
                  onClick={() => onChain('tts-sync', {})}
                  variant="secondary"
                />
                <span className="text-[10px] text-slate-400">选择上方音色可自动填入 voice_id</span>
              </div>
            </div>
          )}
        </>
      )}

      {resultType === 'text' && template.next_steps.some(ns => ns.capability_id === 'music-gen') && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <p className="text-xs text-slate-500 mb-2">下一步：使用这段歌词生成音乐</p>
          {(() => {
            const lyrics = extractTextResult(result.data)
            const ns = template.next_steps.find(n => n.capability_id === 'music-gen')
            if (!ns) return null
            return (
              <div className="flex items-center gap-2">
                <ChainButton
                  label={lyrics ? '用这段歌词生成音乐 →' : '去 music-gen'}
                  onClick={() => onChain('music-gen', lyrics ? { lyrics } : {})}
                  disabled={!lyrics}
                  variant="primary"
                />
                {!lyrics && (
                  <span className="text-[10px] text-slate-400">未识别到歌词，可从完整 JSON 中复制歌词后粘贴到 music-gen</span>
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

      {/* File chain: file-upload / file-list → file-retrieve / file-content */}
      {(resultType === 'file_upload' || resultType === 'file_list') && (
        <div className="mt-3">
          <FileResultPreview
            data={result.data}
            resultType={resultType}
            onChain={(capId, handoffVals) => onChain(capId, handoffVals)}
            nextSteps={template.next_steps}
          />
        </div>
      )}

      {/* file-retrieve / file-content: show FileResultPreview but no chain */}
      {resultType === 'file_detail' && (
        <div className="mt-3">
          <FileResultPreview
            data={result.data}
            resultType={resultType}
            onChain={(capId, handoffVals) => onChain(capId, handoffVals)}
            nextSteps={template.next_steps}
          />
        </div>
      )}
      {resultType === 'file_content' && (
        <div className="mt-3">
          <FileResultPreview
            data={result.data}
            resultType={resultType}
            onChain={() => {}}
            nextSteps={[]}
          />
        </div>
      )}

      {resultType === 'async_task' && (
        <div className="mt-3">
          <AsyncTaskResultPreview
            data={result.data}
            nextSteps={template.next_steps}
            onChain={(capId, handoffVals) => onChain(capId, handoffVals)}
          />
        </div>
      )}

      {resultType === 'chat' && (
        <div className="mt-3">
          <ChatResultPreview data={result.data} />
        </div>
      )}

      {resultType !== 'chat' && (
        <div className="mt-3">
          <AssetResultPreview {...assetPreviewProps} />
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

function getExecutionDisabled(template: RunnerTemplate, values: Record<string, string>, files: Record<string, File | null>): string | null {
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
  if (template.capability_id === 'file-upload') {
    if (!files['file']) return '请选择要上传的文件'
    const file = files['file']!
    if (file.size > 1024 * 1024) return '文件大小不得超过 1MB'
    if (values['confirm_asset_source'] !== 'true') return '请勾选「确认文件来源合法」后才能执行'
  }
  if (template.capability_id === 'tts-async') {
    if (values['mode'] === 'start' || !values['mode']) {
      // start mode validations
      if (!values['voice_id']?.trim()) return '请填写 voice_id（可从音色列表获取）'
      if (!values['text']?.trim()) return '请填写文本'
      if (values['confirm_long_task'] !== 'true') return '请勾选「确认提交异步任务」后才能执行'
    }
    if (values['mode'] === 'query') {
      if (!values['task_id']?.trim()) return '请填写 task_id'
    }
  }
  // Chat capabilities: validate prompt and model
  if (['chat-openai', 'chat-anthropic', 'chat-responses-create'].includes(template.capability_id)) {
    if (!values['prompt']?.trim()) return '请填写问题'
    if (!values['model']?.trim()) return '请选择模型'
    // Validate max_tokens / max_output_tokens range
    const maxKey = template.capability_id === 'chat-responses-create' ? 'max_output_tokens' : 'max_tokens'
    const raw = values[maxKey]
    if (raw) {
      const n = Number(raw)
      if (isNaN(n) || n < 1 || n > 4096) return `${maxKey} 必须在 1~4096 之间`
    }
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
  onDone,
  sessionDraft,
}: {
  template: RunnerTemplate
  initialValues?: Record<string, string>
  handoffKeys?: string[]
  onBack: () => void
  onChainNavigate: (capId: string) => void
  onDone?: () => void
  sessionDraft?: RunnerSession | null
}) {
  const schema = template.form_schema as FormSchema
  const defaults = getDefaultValues(schema)
  const [values, setValues] = useState<Record<string, string>>(() => ({ ...defaults, ...(initialValues ?? {}) }))
  const [files, setFiles] = useState<Record<string, File | null>>({})
  const [runState, setRunState] = useState<RunState>('idle')
  const [result, setResult] = useState<InvokeResult | null>(null)
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const resultType = template.result_type ?? 'text'
  const disabledReason = getExecutionDisabled(template, values, files)

  const handleChange = (key: string, val: string) => {
    setValues((v) => ({ ...v, [key]: val }))
  }

  // Debounced session save when values change
  const sessionSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (sessionSaveTimer.current) clearTimeout(sessionSaveTimer.current)
    sessionSaveTimer.current = setTimeout(() => {
      saveRunnerSession({
        capabilityId: template.capability_id,
        createdAt: new Date().toISOString(),
        inputValues: values,
      })
    }, 800)
    return () => { if (sessionSaveTimer.current) clearTimeout(sessionSaveTimer.current) }
  }, [values, template.capability_id])

  const handleFileChange = (key: string, file: File | null) => setFiles((f) => ({ ...f, [key]: file }))

  const handleClearHandoffField = (key: string) => {
    handleChange(key, template.form_schema[key]?.default ?? '')
    if (handoffKeys?.includes(key)) {
      clearHandoffFields(template.capability_id, [key])
    }
  }

  // Show handoff banner if any fields came from handoff
  const activeHandoffKeys = (handoffKeys ?? []).filter(k => values[k]?.trim())
  const confirmKey = template.capability_id === 'music-gen'
    ? 'confirm_quota' : template.capability_id === 'image-i2i' || template.capability_id === 'file-upload'
    ? 'confirm_asset_source' : template.capability_id === 'tts-async'
    ? 'confirm_long_task' : null
  const confirmChecked = confirmKey ? values[confirmKey] === 'true' : null

  const handleRun = async () => {
    if (disabledReason) return
    setRunState('checking')
    setResult(null)
    setRiskResult(null)
    setErrorMessage(null)

    let calledBackend = false

    try {
      // file-upload uses multipart upload path
      if (template.capability_id === 'file-upload') {
        const file = files['file']
        if (!file) { setRunState('error'); setErrorMessage('请选择文件'); return }
        if (file.size > 1024 * 1024) { setRunState('error'); setErrorMessage('文件大小不得超过 1MB'); return }
        if (values['confirm_asset_source'] !== 'true') { setRunState('error'); setErrorMessage('请勾选确认文件来源合法'); return }

        // risk-check payload without file binary
        const riskPayload = {
          filename: file.name,
          size: file.size,
          mime_type: file.type || 'application/octet-stream',
          purpose: values['purpose'] || 'retrieval',
          confirm_asset_source: true,
        }
        const risk = await riskCheck(template.capability_id, riskPayload, {})
        setRiskResult(risk)
        if (!risk.allowed) { calledBackend = true; setRunState('error'); return }

        setRunState('running')
        const res = await uploadCapability(template.capability_id, file, values['purpose'], true)
        calledBackend = true
        if (isOk(res)) {
          const bizErr = extractBusinessError(res.data)
          if (bizErr) { setErrorMessage(bizErr); setResult(res); setRunState('error'); return }
        }
        setResult(res)
        setRunState('done')
        if (isOk(res)) {
          saveRunnerSession({
            capabilityId: template.capability_id,
            createdAt: new Date().toISOString(),
            inputValues: values,
            resultSummary: buildResultSummary(res.data, template.result_type),
            handoff: {},
          })
        }
        return
      }

      // Standard JSON invoke for all other capabilities
      const basePayload = buildPayload(template.payload_template as Record<string, unknown>, values, schema)
      const payload = applyI2IPromptMode(basePayload, values, template.capability_id)
      const risk = await riskCheck(template.capability_id, payload, {})
      setRiskResult(risk)
      if (!risk.allowed) { calledBackend = true; setRunState('error'); return }
      setRunState('running')
      calledBackend = true
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
      if (isOk(res)) {
        saveRunnerSession({
          capabilityId: template.capability_id,
          createdAt: new Date().toISOString(),
          inputValues: values,
          resultSummary: buildResultSummary(res.data, template.result_type),
          handoff: {},
        })
      }
    } catch (e: any) {
      setErrorMessage(e?.message ?? String(e))
      setRunState('error')
    } finally {
      if (calledBackend) onDone?.()
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
    'tts-async': '提交/查询',
    'image-t2i': '生成图片',
    'chat-openai': '发送',
    'chat-anthropic': '发送',
    'chat-responses-create': '发送',
    'music-gen': '生成音乐',
    'image-i2i': '生成图片',
    'file-upload': '上传文件',
    'file-list': '查询列表',
    'file-retrieve': '查询详情',
    'file-content': '读取内容',
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

        <UsageCostExplainer
          billingPolicy={template.billing_policy}
          costLevel={template.cost_level}
        />

        {sessionDraft?.inputValues && Object.keys(sessionDraft.inputValues).length > 0 && (
          <div className="rounded-lg border border-sky-200 bg-sky-50 p-2 text-xs text-sky-700 flex items-start gap-2">
            <span>📝</span>
            <div className="flex-1">
              <span className="font-medium">轻量草稿保存</span>
              <span className="text-slate-500 ml-1">（{new Date(sessionDraft.createdAt).toLocaleString('zh-CN')}）</span>
              {sessionDraft.resultSummary?.textPreview && (
                <div className="mt-1 text-slate-600 truncate">
                  上次结果：{sessionDraft.resultSummary.textPreview}
                </div>
              )}
              {sessionDraft.resultSummary?.imageUrl && (
                <div className="mt-1">
                  <img src={sessionDraft.resultSummary.imageUrl} alt="上次结果" className="h-12 rounded border border-sky-200" />
                </div>
              )}
            </div>
          </div>
        )}

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

        {template.capability_id === 'file-upload' && runState !== 'done' && (
          <div className={`mb-3 p-2 rounded border text-xs ${confirmChecked ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-orange-50 border-orange-100 text-orange-600'}`}>
            {confirmChecked
              ? '✓ 已确认，文件来源合法，可执行'
              : '⚠ 上传文件请确保来源合法且不包含敏感信息，勾选确认后方可执行'}
          </div>
        )}

        {template.capability_id === 'tts-async' && runState !== 'done' && (
          <div className={`mb-3 p-2 rounded border text-xs ${
            values['mode'] === 'query'
              ? 'bg-sky-50 border-sky-200 text-sky-700'
              : values['confirm_long_task'] === 'true'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-orange-50 border-orange-100 text-orange-600'
          }`}>
            {values['mode'] === 'query'
              ? '📋 查询模式：只需填写 task_id 即可查询'
              : values['confirm_long_task'] === 'true'
                ? '✓ 已确认，可提交异步任务'
                : '⚠ 异步任务可能需要稍后手动查询结果，请勾选确认'}
          </div>
        )}

        {Object.keys(schema).length > 0 && (
          <div className="mb-4">
            {template.capability_id === 'image-i2i' && (
              <div className="mb-3 p-3 rounded bg-amber-50 border border-amber-200 text-xs text-amber-700">
                <p className="font-medium mb-1">🖼 图生图需要参考图片 URL</p>
                <p className="mb-1">没有参考图片？先去文生图生成一张，再用「用此图片做图生图」自动带入。</p>
                <button
                  type="button"
                  onClick={() => onChainNavigate('image-t2i')}
                  className="text-sky-600 hover:underline font-medium"
                >
                  去文生图 image-t2i →
                </button>
              </div>
            )}

            {/* image-i2i model and reference mode note */}
            {template.capability_id === 'image-i2i' && (
              <div className="mb-3 p-2 rounded bg-slate-50 border border-slate-200 text-[10px] text-slate-500">
                <strong>模型说明：</strong>当前图生图仅开放已验收的 <code className="bg-slate-100 px-1 rounded">image-01</code>。
                <code className="bg-slate-100 px-1 rounded">image-01-live</code> 是否支持图生图需要单独验证。
                <br />
                <strong>参考模式说明：</strong>参考模式会自动增强发送给 MiniMax 的 prompt，但底层 API 仍使用已验收的 <code className="bg-slate-100 px-1 rounded">character</code> reference。style / variation 的真实 API 映射需要后续单独验证。
              </div>
            )}

            {/* music-gen lyrics helper */}
            {template.capability_id === 'music-gen' && (
              <div className="mb-3 p-3 rounded bg-violet-50 border border-violet-200 text-xs text-violet-700 space-y-2">
                <div className="font-medium">🎵 音乐生成需要歌词</div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleChange('lyrics', '夏日晚风吹过田野\n我在旧路口等一场落日\n蝉声慢慢落进云里\n心事也变得安静')}
                    className="px-2 py-1 rounded border border-violet-300 bg-white text-violet-700 hover:bg-violet-100 text-[10px]"
                  >
                    使用示例歌词
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChange('lyrics', '')}
                    className="px-2 py-1 rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 text-[10px]"
                  >
                    清空歌词
                  </button>
                  <button
                    type="button"
                    onClick={() => onChainNavigate('lyrics-gen')}
                    className="px-2 py-1 rounded border border-sky-300 bg-white text-sky-700 hover:bg-sky-100 text-[10px]"
                  >
                    去生成歌词 →
                  </button>
                </div>
              </div>
            )}

            <RunnerForm
              schema={schema}
              values={values}
              onChange={handleChange}
              files={files}
              onFileChange={handleFileChange}
            />
          </div>
        )}

        {template.capability_id === 'voice-list' && (
          <div className="text-xs text-slate-500 mb-4">此能力无需参数，直接查询可用音色列表。</div>
        )}

        {template.capability_id === 'image-i2i' && (
          <details className="mb-3 text-xs border border-slate-200 rounded p-2 bg-slate-50">
            <summary className="cursor-pointer text-slate-500 hover:text-slate-700 font-medium">
              🔍 查看将发送给 MiniMax 的 payload
            </summary>
            <pre className="mt-2 p-2 bg-white rounded border text-[10px] text-slate-600 overflow-auto max-h-40 whitespace-pre-wrap break-all">
              {JSON.stringify(applyI2IPromptMode(buildPayload(template.payload_template as Record<string, unknown>, values, schema), values, template.capability_id), null, 2)}
            </pre>
          </details>
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
          <div className="mt-3 text-xs text-emerald-600">✓ 执行完成，可在「高级测试」历史模块刷新查看。</div>
        )}
        {runState === 'error' && (
          <div className="mt-3 text-xs text-red-600">
            ✗ {errorMessage ? `执行失败：${errorMessage}` : '执行失败（被安全检查阻断或发生错误）'}
          </div>
        )}
        {riskResult && !riskResult.allowed && (
          <div className="mt-3 p-2 rounded bg-red-50 border border-red-200 text-xs text-red-700">
            <strong>安全检查阻断：</strong>
            <details className="mt-1 border border-red-200 rounded">
              <summary className="px-2 py-1 cursor-pointer text-[10px] text-red-600 hover:text-red-800">
                调试信息
              </summary>
              <div className="px-2 pb-2 space-y-1">
                <div>阻断原因：{riskResult.blocked_reasons.join('；')}</div>
                {riskResult.required_confirmations.length > 0 && (
                  <div>需要确认：{riskResult.required_confirmations.join('、')}</div>
                )}
              </div>
            </details>
          </div>
        )}
        {result && (
          <InvokeResultView
            result={result}
            resultType={resultType}
            template={template}
            onChain={handleChain}
            values={values}
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
  'tts-async': '🎙️',
  'image-t2i': '🖼️',
  'chat-openai': '⚖️',
  'chat-anthropic': '⚖️',
  'chat-responses-create': '⚖️',
  'music-gen': '🎶',
  'image-i2i': '🖼️',
  'file-upload': '📄',
  'file-list': '📄',
  'file-retrieve': '📄',
  'file-content': '📄',
}

const CAPABILITY_FAMILY: Record<string, string> = {
  'lyrics-gen': 'music',
  'tts-sync': 'voice',
  'voice-list': 'voice',
  'tts-async': 'voice',
  'image-t2i': 'vision',
  'chat-openai': 'chat',
  'chat-anthropic': 'chat',
  'chat-responses-create': 'chat',
  'music-gen': 'music',
  'image-i2i': 'vision',
  'file-upload': 'files',
  'file-list': 'files',
  'file-retrieve': 'files',
  'file-content': 'files',
}

const CAPABILITY_LABEL: Record<string, string> = {
  'lyrics-gen': '歌词生成',
  'tts-sync': '语音合成',
  'voice-list': '音色列表',
  'tts-async': '异步语音合成',
  'image-t2i': '图片生成',
  'chat-openai': 'OpenAI 对比',
  'chat-anthropic': 'Anthropic 对比',
  'chat-responses-create': 'Responses 对比',
  'music-gen': '音乐生成',
  'image-i2i': '图生图',
  'file-upload': '文件上传',
  'file-list': '文件列表',
  'file-retrieve': '文件详情',
  'file-content': '文件内容',
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
  const fromWorkflow = searchParams.get('from_workflow')
  const fromScenario = searchParams.get('from_scenario')

  const [history, setHistory] = useState<TestConsoleHistoryItem[]>([])
  const [historyErr, setHistoryErr] = useState<string | null>(null)
  const [expandedHistoryId, setExpandedHistoryId] = useState<string | null>(null)
  const [sessionDraft, setSessionDraft] = useState<RunnerSession | null>(null)

  const refreshHistory = (capId?: string) => {
    const id = capId ?? selected
    if (!id) return
    getCapabilityHistory(id, 50)
      .then(r => { setHistory(r.items); setHistoryErr(null) })
      .catch((e: any) => setHistoryErr(e.message))
  }

  // Refresh history and load session draft when capability changes
  useEffect(() => {
    if (selected) {
      refreshHistory(selected)
      const draft = loadRunnerSession(selected)
      setSessionDraft(draft)
    }
  }, [selected])

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
    if (key !== 'capability' && key !== 'from_workflow' && key !== 'from_scenario') {
      queryInitialValues[key] = val
    }
  })

  const selectedTemplate = selected ? templates[selected] : null

  // Merge: URL params > sessionStorage handoff > session draft
  const selectedId = selected as string
  const storedHandoff = selectedTemplate ? loadHandoff(selectedId) : {}
  const initialValues = selectedTemplate
    ? { ...(sessionDraft?.inputValues ?? {}), ...storedHandoff, ...queryInitialValues }
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

      {/* Path guide banner */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 flex items-start gap-3">
        <span className="text-base">🗺</span>
        <div className="space-y-1 text-xs text-slate-600">
          <div className="font-semibold text-slate-700">能力体验有两个入口：</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex items-start gap-2">
              <span className="shrink-0 mt-0.5">⚖️</span>
              <div>
                <span className="font-medium">模型对比（chat-*）</span>
                <span className="text-slate-500 ml-1">选模型，看回答差异</span>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="shrink-0 mt-0.5">🧩</span>
              <div>
                <span className="font-medium">单项能力</span>
                <span className="text-slate-500 ml-1">生成、合成、上传、查询</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Workflow/scenario context banner */}
      {(fromWorkflow || fromScenario) && (
        <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
          {fromWorkflow && (
            <span>
              <span className="text-slate-500">当前来自流程：</span>
              <Link to={`/capability-workflows?workflow=${encodeURIComponent(fromWorkflow)}`} className="text-sky-600 hover:underline ml-1">
                {fromWorkflow}
              </Link>
            </span>
          )}
          {fromWorkflow && fromScenario && <span className="mx-2 text-slate-300">|</span>}
          {fromScenario && (
            <span>
              <span className="text-slate-500">当前来自场景：</span>
              <Link to={`/capability-scenarios?scenario=${encodeURIComponent(fromScenario)}`} className="text-sky-600 hover:underline ml-1">
                {fromScenario}
              </Link>
            </span>
          )}
        </div>
      )}

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
              onDone={refreshHistory}
              sessionDraft={sessionDraft}
            />
          ) : (
            <div className="text-sm text-slate-500">
              不支持的 Runner 能力：{selected}（支持的：{supportedCapabilities.join(' / ')}）
            </div>
          )}

          {/* Current capability history */}
          {selected && (
            <section className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-slate-800">当前能力最近调用记录</h3>
                <button
                  onClick={() => refreshHistory()}
                  className="px-3 py-1 text-xs border border-slate-300 rounded bg-white hover:bg-slate-100"
                >
                  刷新
                </button>
              </div>

              {historyErr && (
                <p className="text-xs text-red-600 mb-2">加载失败: {historyErr}</p>
              )}

              <InvocationHistoryPanel
                items={history}
                expandedId={expandedHistoryId}
                onToggleExpand={setExpandedHistoryId}
                emptyMessage="当前能力暂无调用记录"
              />
            </section>
          )}
        </div>
      )}
    </div>
  )
}
