import { useState } from 'react'
import { uploadCapability, type Capability } from '../api'
import { JsonView } from './JsonView'

export function UploadPanel({ cap }: { cap: Capability }) {
  const [file, setFile] = useState<File | null>(null)
  const [purpose, setPurpose] = useState<string>(
    typeof cap.example.purpose === 'string' ? (cap.example.purpose as string) : '',
  )
  const [result, setResult] = useState<unknown>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setErr(null)
    setResult(null)
    if (!file) {
      setErr('请选择文件')
      return
    }
    setLoading(true)
    const r = await uploadCapability(cap.id, file, purpose || undefined)
    setLoading(false)
    if ('error' in r) setErr(`[${r.status ?? '-'}] ${r.message}`)
    else setResult(r.data)
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
      <button
        onClick={submit}
        disabled={loading}
        className="px-4 py-1.5 bg-slate-900 text-white rounded text-sm disabled:opacity-50"
      >
        {loading ? '上传中…' : '上传'}
      </button>
      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}
      {result !== null && <JsonView data={result} />}
    </div>
  )
}
