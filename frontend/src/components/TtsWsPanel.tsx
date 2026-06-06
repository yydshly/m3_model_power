import { useEffect, useRef, useState } from 'react'
import type { Capability, Model } from '../api'

/**
 * tts-ws 专用面板。
 * 协议（参考官方文档）：
 *   连接后先发送 { event: "task_start", model, voice_setting, audio_setting }
 *   再发送 { event: "task_continue", text: "要合成的文本" }
 *   最后 { event: "task_finish" }
 * 上游每来一段音频，data.audio 字段为 hex 字符串，累计后用 Blob 播放。
 */
export function TtsWsPanel({ cap, models }: { cap: Capability; models: Model[] }) {
  const [model, setModel] = useState(models[0]?.id ?? 'speech-02-turbo')
  const [voiceId, setVoiceId] = useState('female-shaonv')
  const [text, setText] = useState('你好，欢迎使用 MiniMax 实时语音合成。')
  const [log, setLog] = useState<string[]>([])
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const chunksRef = useRef<Uint8Array[]>([])

  const append = (s: string) => setLog((prev) => [...prev.slice(-200), s])

  useEffect(() => () => { wsRef.current?.close() }, [])

  const start = () => {
    setLog([])
    setAudioUrl(null)
    chunksRef.current = []
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
      if (event === 'task_finished' || event === 'task_failed' || payload.is_final) {
        finish()
      }
    }

    ws.onerror = () => append('✗ WebSocket 错误')
    ws.onclose = () => { append('■ 连接关闭'); finish() }
  }

  const finish = () => {
    if (chunksRef.current.length > 0 && !audioUrl) {
      const blob = new Blob(chunksRef.current as BlobPart[], { type: 'audio/mpeg' })
      setAudioUrl(URL.createObjectURL(blob))
    }
    setRunning(false)
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
          <label className="block text-xs text-slate-600 mb-1">voice_id</label>
          <input value={voiceId} onChange={(e) => setVoiceId(e.target.value)} className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm bg-white" />
        </div>
      </div>
      <div>
        <label className="block text-xs text-slate-600 mb-1">文本</label>
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} className="w-full border border-slate-300 rounded p-2 text-sm" />
      </div>
      <div className="flex gap-2">
        <button onClick={start} disabled={running} className="px-4 py-1.5 bg-sky-600 text-white rounded text-sm disabled:opacity-50">
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
