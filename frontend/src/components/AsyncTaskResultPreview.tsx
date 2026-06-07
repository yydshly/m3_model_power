import { useState } from 'react'
import { extractAudioSource, audioSourceToSrc } from './assetResultUtils'

// ── Types ───────────────────────────────────────────────────────────────────

type NextStep = {
  capability_id: string
  label: string
  note?: string
  blocked?: boolean
  guarded?: boolean
  handoff?: Record<string, string>
}

type Props = {
  data: unknown
  nextSteps?: NextStep[]
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function extractTaskId(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  for (const field of ['task_id', 'id']) {
    if (typeof d[field] === 'string' && d[field]) return d[field] as string
  }

  const inner = d.data as Record<string, unknown> | undefined
  if (inner) {
    for (const field of ['task_id', 'id']) {
      if (typeof inner[field] === 'string' && inner[field]) return inner[field] as string
    }
  }

  const result = d.result as Record<string, unknown> | undefined
  if (result) {
    for (const field of ['task_id', 'id']) {
      if (typeof result[field] === 'string' && result[field]) return result[field] as string
    }
  }

  return null
}

function extractStatus(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  // Direct fields
  for (const field of ['status', 'state', 'task_status']) {
    if (typeof d[field] === 'string' && d[field]) return d[field] as string
  }

  // data.status / data.state
  const inner = d.data as Record<string, unknown> | undefined
  if (inner) {
    for (const field of ['status', 'state', 'task_status']) {
      if (typeof inner[field] === 'string' && inner[field]) return inner[field] as string
    }
  }

  // base_resp.status_code
  const base = d.base_resp as Record<string, unknown> | undefined
  if (base) {
    const code = base.status_code as number | undefined
    if (code !== undefined && code !== 0) {
      const msg = (base.status_msg as string) || 'unknown error'
      return `failed: ${msg}`
    }
  }

  return null
}

function extractErrorMessage(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  // base_resp.status_msg
  const base = d.base_resp as Record<string, unknown> | undefined
  if (base && typeof base.status_msg === 'string') {
    return base.status_msg
  }

  // top-level error / message
  if (typeof d.message === 'string') return d.message
  if (typeof d.error === 'string') return d.error

  const inner = d.data as Record<string, unknown> | undefined
  if (inner) {
    if (typeof inner.message === 'string') return inner.message
    if (typeof inner.error === 'string') return inner.error
  }

  return null
}

function formatStatus(status: string): { label: string; cls: string } {
  const s = status.toLowerCase()
  if (s.includes('success') || s.includes('完成') || s.includes('成功')) {
    return { label: '已完成', cls: 'bg-emerald-100 text-emerald-700' }
  }
  if (s.includes('failed') || s.includes('失败') || s.includes('error')) {
    return { label: '失败', cls: 'bg-red-100 text-red-700' }
  }
  if (s.includes('running') || s.includes('处理') || s.includes('进行')) {
    return { label: '处理中', cls: 'bg-amber-100 text-amber-700' }
  }
  if (s.includes('pending') || s.includes('等待') || s.includes('排队')) {
    return { label: '等待中', cls: 'bg-sky-100 text-sky-700' }
  }
  if (s.includes('expired') || s.includes('过期')) {
    return { label: '已过期', cls: 'bg-slate-100 text-slate-600' }
  }
  return { label: status, cls: 'bg-slate-100 text-slate-600' }
}

// ── CopyButton ───────────────────────────────────────────────────────────────

function CopyButton({ text, children }: { text: string; children: React.ReactNode }) {
  const [fb, setFb] = useState<'idle' | 'success' | 'error'>('idle')
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
    <button onClick={handleCopy} className="text-sky-600 hover:underline disabled:opacity-50 text-xs">
      {children}
      {fb === 'success' && <span className="ml-1 text-[10px] text-emerald-600">✓</span>}
      {fb === 'error' && <span className="ml-1 text-[10px] text-red-600">✗</span>}
    </button>
  )
}

// ── ChainButton ─────────────────────────────────────────────────────────────

function ChainButton({
  label,
  onClick,
  disabled,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg transition ${
        disabled
          ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
          : 'bg-slate-900 text-white hover:bg-slate-700'
      }`}
    >
      {label}
    </button>
  )
}

// ── AudioPlayer (inline) ─────────────────────────────────────────────────────

function AudioPlayerInline({ data }: { data: unknown }) {
  const audio = extractAudioSource(data)
  const [loadError, setLoadError] = useState(false)

  if (!audio) return null

  const src = audioSourceToSrc(audio)
  if (!src) return null

  return (
    <div className="mt-2">
      <audio
        controls
        src={src}
        className="w-full mt-1"
        onError={() => setLoadError(true)}
        onLoadedMetadata={(e) => {
          const el = e.target as HTMLAudioElement
          if (isNaN(el.duration) || el.duration === 0) setLoadError(true)
        }}
      />
      {loadError && (
        <p className="text-[10px] text-red-500 mt-1">
          浏览器无法解析该音频，请查看完整 JSON 或下载。
        </p>
      )}
    </div>
  )
}

// ── Start result ─────────────────────────────────────────────────────────────

function StartResult({
  data,
  nextSteps,
  onChain,
}: {
  data: unknown
  nextSteps?: NextStep[]
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
}) {
  const taskId = extractTaskId(data)
  const error = extractErrorMessage(data)

  if (error && !taskId) {
    return (
      <div className="p-3 rounded bg-red-50 border border-red-200 text-xs">
        <strong className="text-red-700">❌ 任务提交失败</strong>
        <div className="mt-1 text-red-600">{error}</div>
      </div>
    )
  }

  return (
    <div className="p-3 rounded bg-emerald-50 border border-emerald-200">
      <strong className="text-xs text-emerald-700">✅ 任务已提交</strong>
      {taskId && (
        <div className="mt-2 space-y-1 text-xs text-slate-600">
          <div>task_id: <CopyButton text={taskId}><span className="font-mono text-slate-800">{taskId}</span></CopyButton></div>
        </div>
      )}

      {nextSteps && nextSteps.length > 0 && onChain && taskId && (
        <div className="mt-3 pt-3 border-t border-emerald-200">
          <p className="text-xs text-slate-500 mb-2">下一步：</p>
          <div className="flex flex-wrap gap-2">
            {nextSteps.map((ns) => {
              const handoffVals: Record<string, string> = {}
              if (ns.handoff) {
                for (const [k, v] of Object.entries(ns.handoff)) {
                  if (v === '$result.task_id') handoffVals[k] = taskId
                  else if (v.startsWith('$result.')) handoffVals[k] = ''
                  else handoffVals[k] = v
                }
              }
              return (
                <ChainButton
                  key={ns.capability_id}
                  label={ns.label}
                  onClick={() => onChain(ns.capability_id, handoffVals)}
                  disabled={!taskId}
                />
              )
            })}
          </div>
        </div>
      )}

      {!taskId && !error && (
        <div className="mt-1 text-xs text-slate-500">未识别到 task_id，请查看完整 JSON。</div>
      )}
    </div>
  )
}

// ── Query result ─────────────────────────────────────────────────────────────

function QueryResult({ data }: { data: unknown }) {
  const status = extractStatus(data)
  const taskId = extractTaskId(data)
  const error = extractErrorMessage(data)
  const audio = extractAudioSource(data)

  if (error && !status) {
    return (
      <div className="p-3 rounded bg-red-50 border border-red-200 text-xs">
        <strong className="text-red-700">❌ 查询失败</strong>
        <div className="mt-1 text-red-600">{error}</div>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs">
        <strong className="text-slate-700">📋 任务状态</strong>
        <div className="mt-1 text-slate-600">未识别到状态，请查看完整 JSON。</div>
        {taskId && (
          <div className="mt-1 text-slate-500">task_id: <span className="font-mono">{taskId}</span></div>
        )}
      </div>
    )
  }

  const { label, cls } = formatStatus(status)
  const isSuccess = label === '已完成'
  const isFailed = label === '失败'

  return (
    <div className="p-3 rounded bg-slate-50 border border-slate-200">
      <strong className="text-xs text-slate-700">📋 任务状态</strong>
      <div className="mt-2 space-y-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded font-medium ${cls}`}>{label}</span>
          {taskId && <span className="text-[10px] text-slate-400">task_id: <span className="font-mono">{taskId}</span></span>}
        </div>

        {isFailed && error && (
          <div className="text-xs text-red-600">错误：{error}</div>
        )}

        {isSuccess && audio && (
          <div className="mt-2">
            <p className="text-xs text-emerald-600 font-medium mb-1">🎧 音频已就绪</p>
            <AudioPlayerInline data={data} />
          </div>
        )}

        {isSuccess && !audio && (
          <div className="text-xs text-slate-500 mt-1">
            任务已完成，但未识别到可播放音频文件，请查看完整 JSON。
          </div>
        )}

        {!isSuccess && !isFailed && (
          <div className="text-xs text-slate-500 mt-1">
            任务尚未完成，请稍后再次查询。
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function AsyncTaskResultPreview({ data, nextSteps, onChain }: Props) {
  // Determine if this is a start result or query result by looking for task_id
  // and whether the data indicates a query response (has status/state)
  const hasStatus = extractStatus(data) !== null
  const hasTaskIdOnly = extractTaskId(data) !== null && !hasStatus

  if (hasTaskIdOnly || (!hasStatus && extractErrorMessage(data) === null)) {
    // Likely a start result (has task_id but no status fields)
    return <StartResult data={data} nextSteps={nextSteps} onChain={onChain} />
  }

  // Likely a query result (has status/state)
  return <QueryResult data={data} />
}
