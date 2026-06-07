import { useState } from 'react'

// ── Types ────────────────────────────────────────────────────────────────────

type FileUploadItem = {
  file_id: string
  filename?: string
  bytes?: number
  size?: number
  mime_type?: string
  content_type?: string
  purpose?: string
  created_at?: string
  status?: string
}

type FileListItem = {
  file_id: string
  filename?: string
  bytes?: number
  size?: number
  mime_type?: string
  content_type?: string
  purpose?: string
  created_at?: string
}

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
  resultType: 'file_upload' | 'file_list' | 'file_detail' | 'file_content'
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
  nextSteps?: NextStep[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes?: number): string {
  if (bytes == null) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function extractFileId(data: unknown): string {
  if (data == null || typeof data !== 'object') return ''
  const d = data as Record<string, unknown>

  // Top-level fields
  const topFields = ['file_id', 'id']
  for (const f of topFields) {
    if (typeof d[f] === 'string' && d[f]) return d[f] as string
  }

  // Nested data.file_id / data.id
  const inner = d.data as Record<string, unknown> | undefined
  if (inner) {
    for (const f of topFields) {
      if (typeof inner[f] === 'string' && inner[f]) return inner[f] as string
    }
  }

  // result.file_id
  const result = d.result as Record<string, unknown> | undefined
  if (result) {
    for (const f of topFields) {
      if (typeof result[f] === 'string' && result[f]) return result[f] as string
    }
  }

  return ''
}

function extractFileList(data: unknown): FileListItem[] {
  if (data == null || typeof data !== 'object') return []
  const d = data as Record<string, unknown>

  // files array
  const files = d.files as FileListItem[] | undefined
  if (Array.isArray(files)) return files.slice(0, 50)

  // data.files array
  const inner = d.data as Record<string, unknown> | undefined
  if (inner) {
    const df = inner.files as FileListItem[] | undefined
    if (Array.isArray(df)) return df.slice(0, 50)
  }

  return []
}

function extractFileDetail(data: unknown): FileUploadItem | null {
  if (data == null || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  // Top-level has file_id
  if (typeof d.file_id === 'string') {
    return {
      file_id: d.file_id as string,
      filename: d.filename as string | undefined,
      bytes: d.bytes as number | undefined,
      size: d.size as number | undefined,
      mime_type: (d.mime_type ?? d.content_type) as string | undefined,
      purpose: d.purpose as string | undefined,
      created_at: d.created_at as string | undefined,
      status: d.status as string | undefined,
    }
  }

  // data.file_id
  const inner = d.data as Record<string, unknown> | undefined
  if (inner && typeof inner.file_id === 'string') {
    return {
      file_id: inner.file_id as string,
      filename: inner.filename as string | undefined,
      bytes: inner.bytes as number | undefined,
      size: inner.size as number | undefined,
      mime_type: (inner.mime_type ?? inner.content_type) as string | undefined,
      purpose: inner.purpose as string | undefined,
      created_at: inner.created_at as string | undefined,
      status: inner.status as string | undefined,
    }
  }

  return null
}

function extractFileContent(data: unknown): string {
  if (data == null) return ''
  const d = data as Record<string, unknown>

  // content field (plain text or base64)
  if (typeof d.content === 'string') return d.content

  // data.content
  const inner = d.data as Record<string, unknown> | undefined
  if (inner && typeof inner.content === 'string') return inner.content as string

  // text field
  if (typeof d.text === 'string') return d.text as string
  if (inner && typeof inner.text === 'string') return inner.text as string

  return ''
}

// ── CopyButton (inline) ─────────────────────────────────────────────────────

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

// ── ChainButton ──────────────────────────────────────────────────────────────

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

// ── File Upload Result ────────────────────────────────────────────────────────

function FileUploadResult({ data, nextSteps, onChain }: {
  data: unknown
  nextSteps?: NextStep[]
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
}) {
  const detail = extractFileDetail(data)
  const fileId = extractFileId(data)

  if (!detail && !fileId) {
    return (
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600">
        <strong>📄 文件上传结果</strong>
        <div className="mt-1">未识别到 file_id，请查看下方完整 JSON。</div>
      </div>
    )
  }

  const info = detail ?? { file_id: fileId }

  return (
    <div className="p-3 rounded bg-emerald-50 border border-emerald-200">
      <strong className="text-xs text-emerald-700">📄 文件上传成功</strong>
      <div className="mt-2 space-y-1 text-xs text-slate-600">
        <div>file_id: <CopyButton text={info.file_id}><span className="font-mono text-slate-800">{info.file_id}</span></CopyButton></div>
        {info.filename && <div>filename: <span className="text-slate-800">{info.filename}</span></div>}
        {(info.bytes ?? info.size) && <div>size: <span className="text-slate-800">{formatBytes(info.bytes ?? info.size)}</span></div>}
        {info.mime_type && <div>mime_type: <span className="text-slate-800">{info.mime_type}</span></div>}
        {info.purpose && <div>purpose: <span className="text-slate-800">{info.purpose}</span></div>}
        {info.created_at && <div>created_at: <span className="text-slate-800">{info.created_at}</span></div>}
        {info.status && <div>status: <span className="text-slate-800">{info.status}</span></div>}
      </div>

      {nextSteps && nextSteps.length > 0 && onChain && (
        <div className="mt-3 pt-3 border-t border-emerald-200">
          <p className="text-xs text-slate-500 mb-2">下一步：</p>
          <div className="flex flex-wrap gap-2">
            {nextSteps.map((ns) => {
              const handoffVals: Record<string, string> = {}
              if (ns.handoff) {
                for (const [k, v] of Object.entries(ns.handoff)) {
                  // v is a template like "$result.file_id" — resolve it now
                  if (v === '$result.file_id') handoffVals[k] = fileId || ''
                  else if (v.startsWith('$result.')) handoffVals[k] = ''
                  else handoffVals[k] = v
                }
              }
              return (
                <ChainButton
                  key={ns.capability_id}
                  label={ns.label}
                  onClick={() => onChain(ns.capability_id, handoffVals)}
                  disabled={!fileId}
                />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── File List Result ─────────────────────────────────────────────────────────

function FileListResult({ data, nextSteps, onChain }: {
  data: unknown
  nextSteps?: NextStep[]
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
}) {
  const files = extractFileList(data)

  if (!files.length) {
    return (
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600">
        <strong>📋 文件列表</strong>
        <div className="mt-1">未查询到文件，或列表为空。</div>
      </div>
    )
  }

  return (
    <div className="p-3 rounded bg-slate-50 border border-slate-200">
      <strong className="text-xs text-slate-700">📋 文件列表</strong>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left pb-1 pr-2 text-slate-500 font-medium">file_id</th>
              <th className="text-left pb-1 pr-2 text-slate-500 font-medium">filename</th>
              <th className="text-left pb-1 pr-2 text-slate-500 font-medium">size</th>
              <th className="text-left pb-1 pr-2 text-slate-500 font-medium">mime_type</th>
              <th className="text-left pb-1 text-slate-500 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.file_id} className="border-b border-slate-100 last:border-0">
                <td className="py-1 pr-2 font-mono text-slate-700 whitespace-nowrap">{f.file_id}</td>
                <td className="py-1 pr-2 text-slate-600 whitespace-nowrap">{f.filename ?? '—'}</td>
                <td className="py-1 pr-2 text-slate-600 whitespace-nowrap">{formatBytes(f.bytes ?? f.size)}</td>
                <td className="py-1 pr-2 text-slate-600 whitespace-nowrap">{f.mime_type ?? '—'}</td>
                <td className="py-1 whitespace-nowrap">
                  {onChain && nextSteps?.some(ns => ns.capability_id === 'file-retrieve') && (
                    <button
                      onClick={() => onChain('file-retrieve', { file_id: f.file_id })}
                      className="text-sky-600 hover:underline mr-2"
                    >
                      详情
                    </button>
                  )}
                  {onChain && nextSteps?.some(ns => ns.capability_id === 'file-content') && (
                    <button
                      onClick={() => onChain('file-content', { file_id: f.file_id })}
                      className="text-sky-600 hover:underline"
                    >
                      内容
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {files.length >= 50 && (
          <p className="mt-1 text-[10px] text-slate-400">显示前 50 条，更多请使用高级测试</p>
        )}
      </div>
    </div>
  )
}

// ── File Detail Result ────────────────────────────────────────────────────────

function FileDetailResult({ data, nextSteps, onChain }: {
  data: unknown
  nextSteps?: NextStep[]
  onChain?: (capId: string, handoffVals: Record<string, string>) => void
}) {
  const detail = extractFileDetail(data)

  if (!detail) {
    return (
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600">
        <strong>📄 文件详情</strong>
        <div className="mt-1">未识别到文件详情，请查看下方完整 JSON。</div>
      </div>
    )
  }

  return (
    <div className="p-3 rounded bg-slate-50 border border-slate-200">
      <strong className="text-xs text-slate-700">📄 文件详情</strong>
      <div className="mt-2 space-y-1 text-xs text-slate-600">
        <div>file_id: <CopyButton text={detail.file_id}><span className="font-mono text-slate-800">{detail.file_id}</span></CopyButton></div>
        {detail.filename && <div>filename: <span className="text-slate-800">{detail.filename}</span></div>}
        {(detail.bytes ?? detail.size) && <div>size: <span className="text-slate-800">{formatBytes(detail.bytes ?? detail.size)}</span></div>}
        {detail.mime_type && <div>mime_type: <span className="text-slate-800">{detail.mime_type}</span></div>}
        {detail.purpose && <div>purpose: <span className="text-slate-800">{detail.purpose}</span></div>}
        {detail.created_at && <div>created_at: <span className="text-slate-800">{detail.created_at}</span></div>}
        {detail.status && <div>status: <span className="text-slate-800">{detail.status}</span></div>}
      </div>

      {nextSteps && nextSteps.some(ns => ns.capability_id === 'file-content') && onChain && (
        <div className="mt-3 pt-3 border-t border-slate-200">
          <p className="text-xs text-slate-500 mb-2">下一步：</p>
          <div className="flex flex-wrap gap-2">
            {nextSteps.filter(ns => ns.capability_id === 'file-content').map(ns => (
              <ChainButton
                key={ns.capability_id}
                label={ns.label}
                onClick={() => onChain('file-content', { file_id: detail.file_id })}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── File Content Result ───────────────────────────────────────────────────────

const MAX_PREVIEW_CHARS = 3000

function FileContentResult({ data }: { data: unknown }) {
  const content = extractFileContent(data)

  if (!content) {
    return (
      <div className="p-3 rounded bg-slate-50 border border-slate-200 text-xs text-slate-600">
        <strong>📝 文件内容</strong>
        <div className="mt-1">未识别到可预览的文本内容。</div>
      </div>
    )
  }

  // Detect if content is JSON
  let formattedContent = content
  let isJson = false
  try {
    const parsed = JSON.parse(content)
    formattedContent = JSON.stringify(parsed, null, 2)
    isJson = true
  } catch {
    // Not JSON, use as-is
  }

  const truncated = formattedContent.length > MAX_PREVIEW_CHARS
  const display = truncated ? formattedContent.slice(0, MAX_PREVIEW_CHARS) + '\n…（已截断，仅展示前 3000 字）' : formattedContent

  return (
    <div className="p-3 rounded bg-slate-50 border border-slate-200">
      <div className="flex items-center gap-2 mb-2">
        <strong className="text-xs text-slate-700">📝 文件内容</strong>
        {isJson && <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">JSON</span>}
      </div>
      <pre className="text-xs text-slate-700 whitespace-pre-wrap break-all max-h-64 overflow-y-auto font-mono bg-white p-2 rounded border border-slate-100">
        {display}
      </pre>
      {truncated && (
        <p className="mt-1 text-[10px] text-slate-400">
          内容过长（{formattedContent.length} 字），已截断至 3000 字。查看完整内容请使用高级测试。
        </p>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function FileResultPreview({ data, resultType, onChain, nextSteps }: Props) {
  if (resultType === 'file_upload') {
    return <FileUploadResult data={data} nextSteps={nextSteps} onChain={onChain} />
  }
  if (resultType === 'file_list') {
    return <FileListResult data={data} nextSteps={nextSteps} onChain={onChain} />
  }
  if (resultType === 'file_detail') {
    return <FileDetailResult data={data} nextSteps={nextSteps} onChain={onChain} />
  }
  if (resultType === 'file_content') {
    return <FileContentResult data={data} />
  }
  return null
}
