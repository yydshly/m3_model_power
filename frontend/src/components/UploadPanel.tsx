import { useState } from 'react'
import { uploadCapability, type Capability } from '../api'
import { JsonView } from './JsonView'

export function UploadPanel({
  cap,
  onDone,
}: {
  cap: Capability
  onDone?: (info?: { history_id?: string | null; capability_id?: string }) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [purpose, setPurpose] = useState<string>(
    typeof cap.example.purpose === 'string' ? (cap.example.purpose as string) : '',
  )
  const [confirmAssetSource, setConfirmAssetSource] = useState(false)
  const [result, setResult] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const needsAssetConfirm = cap.id === 'file-upload' || cap.operation_policy.requires_uploaded_asset
  const submitDisabled = loading || !file || (needsAssetConfirm && !confirmAssetSource)

  const submit = async () => {
    setErr(null)
    setResult(null)
    if (!file) {
      setErr('请选择文件')
      return
    }
    setLoading(true)
    const r = await uploadCapability(cap.id, file, purpose || undefined, confirmAssetSource)
    setLoading(false)
    if ('error' in r) {
      setErr(`[${r.status ?? '-'} ${r.message}`)
      onDone?.({ history_id: r.history_id ?? null, capability_id: cap.id })
    } else {
      setResult(r.data)
      onDone?.({ history_id: r.history_id ?? null, capability_id: cap.id })
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-slate-600 mb-1">文件</label>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm border border-slate-300 rounded p-2 bg-white"
        />
        {file && <div className="mt-1 text-xs text-slate-500">{file.name} · {(file.size / 1024).toFixed(1)} KB</div>}
      </div>
      <div>
        <label className="block text-xs text-slate-600 mb-1">purpose（用途，多数能力已预设默认值）</label>
        <input
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"
          placeholder="retrieval / voice_clone / prompt_audio / song …"
        />
      </div>

      {needsAssetConfirm && (
        <label className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          <input
            type="checkbox"
            checked={confirmAssetSource}
            onChange={(e) => setConfirmAssetSource(e.target.checked)}
          />
          <span>我确认上传/引用素材来源合法，且已获得必要授权。</span>
        </label>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={submit}
          disabled={submitDisabled}
          className="px-4 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50"
        >
          {loading ? '上传中…' : '上传'}
        </button>
        {needsAssetConfirm && !confirmAssetSource && (
          <span className="text-xs text-amber-600">请先确认素材来源合法</span>
        )}
      </div>
      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}
      {result !== null && <JsonView data={result} />}
    </div>
  )
}
