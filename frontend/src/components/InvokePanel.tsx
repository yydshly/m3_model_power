import { useState } from 'react'
import { invoke, type Capability, type Model } from '../api'
import { JsonView } from './JsonView'

/**
 * 通用调用面板：把 capability + 模型下拉 + JSON 输入凑成"提交 → 看结果"。
 * 这是 P0 通用形态；后续每个能力可以替换成专用更友好的 UI，但默认这套先保证 32 个接口都能动。
 */
export function InvokePanel({
  cap,
  models,
  defaultPayload,
}: {
  cap: Capability
  models: Model[]
  defaultPayload?: Record<string, unknown>
}) {
  const [model, setModel] = useState<string>(models[0]?.id ?? '')
  const [body, setBody] = useState<string>(JSON.stringify(defaultPayload ?? {}, null, 2))
  const [result, setResult] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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
    const r = await invoke(cap.id, parsed)
    setLoading(false)
    if ('error' in r) setErr(`[${r.status ?? '-'}] ${r.message}`)
    else setResult(r.data)
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

      <div>
        <label className="block text-xs text-slate-600 mb-1">请求体 (JSON)</label>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={10}
          className="w-full font-mono text-xs border border-slate-300 rounded p-2"
        />
      </div>

      <button
        onClick={submit}
        disabled={loading}
        className="px-4 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50"
      >
        {loading ? '调用中…' : '调用'}
      </button>

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
  // 兼容上游返回 { data: { image_urls: [] } } 或顶层 { image_urls: [] }
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
