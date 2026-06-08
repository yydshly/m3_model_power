import { useRef, useState } from 'react'
import { streamInvoke, type Capability, type Model } from '../api'
import { quotaLabel } from '../domain/workbenchLabels'
import { useSyncedModelSelection } from '../domain/useSyncedModelSelection'

/**
 * 通用流式调用面板。
 * 上游 SSE/chunked 协议由后端 /api/stream/<id> 透传，前端拿到 chunks 直接追加到文本框。
 * 不解析 JSON token，目的是"看到流动"——具体 UI 后续可分协议特化。
 */
export function StreamPanel({ cap, models }: { cap: Capability; models: Model[] }) {
  const { model, setModel } = useSyncedModelSelection(models)
  const [body, setBody] = useState<string>(JSON.stringify(cap.example ?? {}, null, 2))
  const [out, setOut] = useState<string>('')
  const [err, setErr] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const start = async () => {
    if (!model) {
      setErr('当前能力没有可用模型，请检查模型配置或协议过滤结果。')
      return
    }
    if (running) return
    setErr(null)
    setOut('')
    let parsed: Record<string, unknown>
    try {
      parsed = body.trim() ? JSON.parse(body) : {}
    } catch (e) {
      setErr(`JSON 解析失败：${e}`)
      return
    }
    if (model && !('model' in parsed)) parsed.model = model
    setRunning(true)
    const ctl = new AbortController()
    abortRef.current = ctl
    try {
      const r = await streamInvoke(cap.id, parsed)
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
    }
  }

  const stop = () => abortRef.current?.abort()

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
      <div className="flex gap-2">
        <button
          onClick={start}
          disabled={running}
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
      {out && (
        <pre className="text-xs bg-slate-900 text-emerald-200 rounded p-3 overflow-auto max-h-[480px] whitespace-pre-wrap">
          {out}
        </pre>
      )}
    </div>
  )
}
