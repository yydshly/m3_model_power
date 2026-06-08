import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Capability, Model } from '../api'

/**
 * tts-ws 专用面板。
 * 协议（参考官方文档）：
 *   连接后先发送 { event: "task_start", model, voice_setting, audio_setting }
 *   再发送 { event: "task_continue", text: "要合成的文本" }
 *   最后 { event: "task_finish" }
 * 上游每来一段音频，data.audio 字段为 hex 字符串，累计后用 Blob 播放。
 */
export function TtsWsPanel({
  cap,
  models,
  onDone,
}: {
  cap: Capability
  models: Model[]
  onDone?: (info?: { capability_id?: string }) => void
}) {
  const [searchParams] = useSearchParams()
  const [model, setModel] = useState(models[0]?.id ?? 'speech-02-turbo')
  const [voiceId, setVoiceId] = useState(searchParams.get('voice_id') || '')
  const [text, setText] = useState('')
  const [log, setLog] = useState<string[]>([])
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const chunksRef = useRef<Uint8Array[]>([])
  const finishedRef = useRef(false)
  const terminalSeenRef = useRef(false)
  const audioUrlRef = useRef<string | null>(null)

  const append = (s: string) => setLog((prev) => [...prev.slice(-200), s])

  function replaceAudioUrl(url: string | null) {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
    }
    audioUrlRef.current = url
    setAudioUrl(url)
  }

  // Close WebSocket and revoke Blob URL on unmount
  useEffect(() => () => {
    wsRef.current?.close()
    if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current)
  }, [])

  // Derive validation
  const validationIssues: string[] = []
  if (!model) validationIssues.push('请选择模型')
  if (!voiceId.trim()) validationIssues.push('请填写 voice_id，可先通过 voice-list 查询可用音色')
  if (!text.trim()) validationIssues.push('请填写要合成的文本')
  const canStart = !running && validationIssues.length === 0

  const finish = () => {
    if (finishedRef.current) return
    finishedRef.current = true
    if (chunksRef.current.length > 0 && !audioUrl) {
      const blob = new Blob(chunksRef.current as BlobPart[], { type: 'audio/mpeg' })
      replaceAudioUrl(URL.createObjectURL(blob))
    }
    setRunning(false)
    // Delay onDone to avoid racing with backend append_history in finally
    window.setTimeout(() => {
      onDone?.({ capability_id: cap.id })
    }, 300)
  }

  const start = () => {
    if (validationIssues.length > 0) {
      append(`✗ 参数检查未通过：${validationIssues.join('；')}`)
      return
    }
    setLog([])
    replaceAudioUrl(null)
    chunksRef.current = []
    finishedRef.current = false
    terminalSeenRef.current = false
    setRunning(true)
    const ws = new WebSocket(`${location.origin.replace('http', 'ws')}/api/ws/${cap.id}`)
    wsRef.current = ws

    ws.onopen = () => {
      append('▶ 已连接代理')
      ws.send(JSON.stringify({
        event: 'task_start',
        model,
        voice_setting: { voice_id: voiceId, speed: 1.0, vol: 1.0, pitch: 0 },
        audio_setting: { sample_rate: 32000, bitrate: 128000, format: 'mp3', channel: 1 },
      }))
    }

    ws.onmessage = (ev) => {
      let payload: any
      try { payload = JSON.parse(ev.data) } catch { append(`raw: ${String(ev.data).slice(0, 80)}`); return }
      if (payload.error) { append(`✗ ${payload.error}: ${payload.message ?? ''}`); return }
      const event = payload.event ?? payload.data?.event
      const audioHex = payload.data?.audio
      if (audioHex) {
        const bytes = hexToBytes(audioHex)
        chunksRef.current.push(bytes)
        append(`♪ +${bytes.length} bytes`)
      }
      if (event === 'connected_success' || event === 'task_started') {
        append('✓ task_start 已确认，发送文本')
        ws.send(JSON.stringify({ event: 'task_continue', text }))
        ws.send(JSON.stringify({ event: 'task_finish' }))
      }
      if ((event === 'task_finished' || event === 'task_failed' || payload.is_final) && !terminalSeenRef.current) {
        terminalSeenRef.current = true
        append(`✓ 收到终态事件：${event ?? 'is_final'}`)
        try {
          wsRef.current?.close()
        } catch {
          // ignore
        }
      }
    }

    ws.onerror = () => append('✗ WebSocket 错误')
    ws.onclose = () => { append('■ 连接关闭'); finish() }
  }

  const stop = () => { wsRef.current?.close(); setRunning(false) }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-600 mb-1">模型</label>
          <select value={model} onChange={(e) => setModel(e.target.value)} className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white">
            {models.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-600 mb-1">
            voice_id
            <span className="ml-1 text-amber-600 font-normal">（必填）</span>
          </label>
          <input
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            placeholder="请先通过 voice-list 获取"
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs text-slate-600 mb-1">文本</label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="请填写要合成的文本"
          className="w-full border border-slate-300 rounded p-2 text-sm"
        />
      </div>

      {validationIssues.length > 0 && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
          <div className="font-semibold mb-1">参数检查未通过：</div>
          <ul className="list-disc list-inside">
            {validationIssues.map((x) => <li key={x}>{x}</li>)}
          </ul>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={start}
          disabled={!canStart}
          className="px-4 py-1.5 bg-sky-600 text-white rounded text-sm disabled:opacity-50"
        >
          {running ? '合成中…' : '开始合成'}
        </button>
        {running && <button onClick={stop} className="px-4 py-1.5 bg-slate-200 rounded text-sm">中断</button>}
      </div>
      {audioUrl && (
        <div className="border border-slate-200 rounded p-3 bg-white">
          <audio controls src={audioUrl} className="w-full" />
          <a href={audioUrl} download="tts-ws.mp3" className="text-xs text-sky-600 hover:underline">下载</a>
        </div>
      )}
      {log.length > 0 && (
        <pre className="text-[11px] bg-slate-900 text-slate-200 rounded p-2 max-h-40 overflow-auto">{log.join('\n')}</pre>
      )}
    </div>
  )
}

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2)
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16)
  return out
}
