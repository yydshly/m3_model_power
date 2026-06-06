import { useEffect, useRef, useState } from 'react'
import { invoke, type Capability, type Model } from '../api'
import { JsonView } from './JsonView'

/**
 * video-t2v / video-i2v / video-s2v 专用面板。
 * 提交后保存 task_id，每 5 秒 invoke video-query；状态进入 success 后再 invoke video-download
 * 拿到 file_id 描述（包含 file 元数据和 download_url）。
 *
 * 任务列表持久化到 localStorage，便于跨刷新跟踪。
 */
type Job = {
  id: string                 // 本地随机 id
  cap_id: string
  task_id: string
  prompt: string
  created_at: number
  status: 'queued' | 'processing' | 'preparing' | 'success' | 'fail' | 'unknown'
  file_id?: string
  download_url?: string
  raw?: unknown
  error?: string
}

const KEY = 'mmw_video_jobs_v1'

function loadJobs(): Job[] {
  try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch { return [] }
}
function saveJobs(j: Job[]) { localStorage.setItem(KEY, JSON.stringify(j.slice(0, 50))) }

export function AsyncVideoPanel({ cap, models }: { cap: Capability; models: Model[] }) {
  const [model, setModel] = useState(models[0]?.id ?? '')
  const [body, setBody] = useState(JSON.stringify(cap.example ?? {}, null, 2))
  const [jobs, setJobs] = useState<Job[]>(loadJobs)
  const [err, setErr] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const timerRef = useRef<number | null>(null)

  useEffect(() => { saveJobs(jobs) }, [jobs])

  // 周期轮询：把未终态任务的状态拉新
  useEffect(() => {
    const tick = async () => {
      const active = jobs.filter((j) => j.status !== 'success' && j.status !== 'fail')
      if (active.length === 0) return
      for (const j of active) {
        const r = await invoke('video-query', { task_id: j.task_id })
        if ('error' in r) continue
        const d = r.data as Record<string, unknown>
        const status = String((d.status ?? 'unknown')).toLowerCase()
        const fileId = (d.file_id as string) || undefined
        setJobs((prev) =>
          prev.map((x) => {
            if (x.id !== j.id) return x
            const next: Job = { ...x, raw: d }
            next.status = (status as Job['status']) || 'unknown'
            if (fileId) next.file_id = fileId
            return next
          }),
        )
        // 一旦成功，再拉一次 video-download 拿 download_url
        if (status === 'success' && fileId && !j.download_url) {
          const dl = await invoke('video-download', { file_id: fileId })
          if (!('error' in dl)) {
            const inner = (dl.data as any)?.file ?? dl.data
            const url = inner?.download_url ?? inner?.url
            if (url) {
              setJobs((prev) => prev.map((x) => (x.id === j.id ? { ...x, download_url: url } : x)))
            }
          }
        }
      }
    }
    timerRef.current = window.setInterval(tick, 5000)
    return () => { if (timerRef.current) window.clearInterval(timerRef.current) }
  }, [jobs])

  const submit = async () => {
    setErr(null)
    let parsed: Record<string, unknown>
    try { parsed = body.trim() ? JSON.parse(body) : {} } catch (e) { setErr(`JSON 解析失败：${e}`); return }
    if (model && !('model' in parsed)) parsed.model = model
    setSubmitting(true)
    const r = await invoke(cap.id, parsed)
    setSubmitting(false)
    if ('error' in r) {
      setErr(`[${r.status ?? '-'}] ${r.message}`)
      return
    }
    const d = r.data as Record<string, unknown>
    const task_id = (d.task_id as string) || (d.id as string)
    if (!task_id) {
      setErr('上游未返回 task_id，请查看 JSON 结果')
      return
    }
    const job: Job = {
      id: Math.random().toString(36).slice(2, 10),
      cap_id: cap.id,
      task_id,
      prompt: String(parsed.prompt ?? ''),
      created_at: Date.now(),
      status: 'queued',
      raw: d,
    }
    setJobs((prev) => [job, ...prev])
  }

  const remove = (id: string) => setJobs((prev) => prev.filter((j) => j.id !== id))
  const myJobs = jobs.filter((j) => j.cap_id === cap.id)

  return (
    <div className="space-y-4">
      {models.length > 0 && (
        <div>
          <label className="block text-xs text-slate-600 mb-1">模型</label>
          <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white">
            {models.map((m) => <option key={m.id} value={m.id}>{m.label} · {m.tier}</option>)}
          </select>
        </div>
      )}
      <div>
        <label className="block text-xs text-slate-600 mb-1">请求体 (JSON)</label>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={10} className="w-full font-mono text-xs border border-slate-300 rounded p-2" />
      </div>
      <button onClick={submit} disabled={submitting} className="px-4 py-1.5 bg-purple-600 text-white rounded text-sm disabled:opacity-50">
        {submitting ? '提交中…' : '提交任务'}
      </button>
      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}

      {myJobs.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="text-xs text-slate-500">任务历史（自动每 5 秒轮询）</div>
          {myJobs.map((j) => (
            <div key={j.id} className="border border-slate-200 rounded bg-white p-3">
              <div className="flex items-center gap-3 text-sm">
                <StatusPill status={j.status} />
                <span className="font-mono text-xs text-slate-600">{j.task_id}</span>
                <span className="ml-auto text-xs text-slate-400">
                  {new Date(j.created_at).toLocaleTimeString()}
                </span>
                <button onClick={() => remove(j.id)} className="text-xs text-slate-400 hover:text-red-600">删除</button>
              </div>
              {j.prompt && <div className="mt-1 text-xs text-slate-500 truncate">prompt: {j.prompt}</div>}
              {j.download_url && (
                <div className="mt-2">
                  <video controls src={j.download_url} className="w-full rounded" />
                  <a href={j.download_url} target="_blank" rel="noreferrer" className="text-xs text-sky-600 hover:underline">下载视频</a>
                </div>
              )}
              {j.error && <div className="mt-2 text-xs text-red-600">{j.error}</div>}
            </div>
          ))}
        </div>
      )}

      {myJobs.length === 0 && <div className="text-xs text-slate-400">尚无任务</div>}

      {Boolean(myJobs[0]?.raw) && (
        <details className="text-xs">
          <summary className="cursor-pointer text-slate-500">查看最新任务原始响应</summary>
          <div className="mt-2"><JsonView data={myJobs[0].raw} /></div>
        </details>
      )}
    </div>
  )
}

function StatusPill({ status }: { status: Job['status'] }) {
  const map: Record<Job['status'], string> = {
    queued: 'bg-slate-100 text-slate-700',
    processing: 'bg-sky-100 text-sky-700',
    preparing: 'bg-sky-100 text-sky-700',
    success: 'bg-emerald-100 text-emerald-700',
    fail: 'bg-red-100 text-red-700',
    unknown: 'bg-slate-100 text-slate-500',
  }
  return <span className={`px-2 py-0.5 text-xs rounded ${map[status]}`}>{status}</span>
}
