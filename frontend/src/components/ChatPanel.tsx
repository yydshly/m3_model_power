import { useEffect, useRef, useState } from 'react'
import { streamInvoke, type Capability, type Model } from '../api'
import { quotaLabel } from '../domain/workbenchLabels'

type Msg = { role: 'system' | 'user' | 'assistant'; content: string }

const KEY = (capId: string) => `mmw_chat_${capId}_v1`

function loadHistory(capId: string): Msg[] {
  try { return JSON.parse(localStorage.getItem(KEY(capId)) || '[]') } catch { return [] }
}

/** 把 OpenAI / Anthropic / Responses 的 SSE 行流抽取成纯文本增量。 */
function extractDelta(line: string, protocol: 'openai' | 'anthropic' | 'responses'): string {
  if (!line.startsWith('data:')) return ''
  const body = line.slice(5).trim()
  if (!body || body === '[DONE]') return ''
  try {
    const o = JSON.parse(body)
    if (protocol === 'openai') {
      return o?.choices?.[0]?.delta?.content ?? ''
    }
    if (protocol === 'anthropic') {
      // content_block_delta 事件
      return o?.delta?.text ?? o?.delta?.partial_json ?? ''
    }
    if (protocol === 'responses') {
      return o?.delta ?? o?.output_text ?? ''
    }
  } catch {
    return ''
  }
  return ''
}

function protocolOf(capId: string): 'openai' | 'anthropic' | 'responses' {
  if (capId === 'chat-anthropic') return 'anthropic'
  if (capId === 'chat-responses-create') return 'responses'
  return 'openai'
}

function buildBody(capId: string, model: string, messages: Msg[]): Record<string, unknown> {
  const protocol = protocolOf(capId)
  if (protocol === 'anthropic') {
    const system = messages.find((m) => m.role === 'system')?.content
    const turns = messages.filter((m) => m.role !== 'system').map((m) => ({ role: m.role, content: m.content }))
    return { model, max_tokens: 2048, messages: turns, ...(system ? { system } : {}) }
  }
  if (protocol === 'responses') {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    return { model, input: lastUser?.content ?? '' }
  }
  return { model, messages }
}

export function ChatPanel({ cap, models }: { cap: Capability; models: Model[] }) {
  const [model, setModel] = useState(models[0]?.id ?? 'MiniMax-M3')
  const [messages, setMessages] = useState<Msg[]>(() => {
    const h = loadHistory(cap.id)
    if (h.length > 0) return h
    return [{ role: 'system', content: '你是一个有帮助的助手。' }]
  })
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { localStorage.setItem(KEY(cap.id), JSON.stringify(messages)) }, [messages, cap.id])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, streaming])

  const send = async () => {
    if (!input.trim() || streaming) return
    setErr(null)
    const next: Msg[] = [...messages, { role: 'user', content: input.trim() }, { role: 'assistant', content: '' }]
    setMessages(next)
    setInput('')
    setStreaming(true)
    const ctl = new AbortController()
    abortRef.current = ctl
    try {
      const r = await streamInvoke(cap.id, buildBody(cap.id, model, next.slice(0, -1)))
      if (!r.ok || !r.body) {
        const txt = await r.text().catch(() => '')
        setErr(`[${r.status}] ${txt}`)
        setStreaming(false)
        return
      }
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      let buf = ''
      const protocol = protocolOf(cap.id)
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''
        for (const line of lines) {
          const delta = extractDelta(line.trim(), protocol)
          if (delta) {
            setMessages((prev) => {
              const copy = [...prev]
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: copy[copy.length - 1].content + delta }
              return copy
            })
          }
        }
      }
    } catch (e) {
      setErr(String(e))
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  const stop = () => abortRef.current?.abort()
  const reset = () => setMessages([{ role: 'system', content: '你是一个有帮助的助手。' }])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <label className="text-xs text-slate-500">模型</label>
        <select value={model} onChange={(e) => setModel(e.target.value)} className="border border-slate-300 rounded px-2 py-1 text-sm bg-white">
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {quotaLabel(m.quota_eligible)} {m.label}
            </option>
          ))}
        </select>
        <button onClick={reset} className="ml-auto text-xs text-slate-500 hover:text-red-600">清空对话</button>
      </div>

      <div className="border border-slate-200 rounded bg-white p-3 max-h-[520px] overflow-auto space-y-3">
        {messages.length === 0 && <div className="text-xs text-slate-400">尚无消息</div>}
        {messages.map((m, i) => (
          <Bubble key={i} msg={m} onChange={(c) => setMessages((prev) => prev.map((x, j) => j === i ? { ...x, content: c } : x))} onDelete={() => setMessages((prev) => prev.filter((_, j) => j !== i))} />
        ))}
        <div ref={bottomRef} />
      </div>

      {err && <div className="text-sm text-red-600 whitespace-pre-wrap">{err}</div>}

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send() }}
          placeholder="输入消息，Ctrl/⌘+Enter 发送"
          rows={3}
          className="flex-1 border border-slate-300 rounded p-2 text-sm"
        />
        <div className="flex flex-col gap-2">
          <button onClick={send} disabled={streaming || !input.trim()} className="px-4 py-1.5 bg-sky-600 text-white rounded text-sm disabled:opacity-50">
            {streaming ? '生成中…' : '发送'}
          </button>
          {streaming && <button onClick={stop} className="px-4 py-1.5 bg-slate-200 text-slate-800 rounded text-sm">中断</button>}
        </div>
      </div>
    </div>
  )
}

function Bubble({ msg, onChange, onDelete }: { msg: Msg; onChange: (c: string) => void; onDelete: () => void }) {
  const isUser = msg.role === 'user'
  const isSys = msg.role === 'system'
  const isAsst = msg.role === 'assistant'
  const cls = isUser
    ? 'bg-sky-50 border-sky-100'
    : isSys
    ? 'bg-slate-50 border-slate-200 text-slate-600 text-xs'
    : 'bg-emerald-50 border-emerald-100'
  return (
    <div className={`border rounded p-2 ${cls}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{msg.role}</span>
        <button onClick={onDelete} className="ml-auto text-[10px] text-slate-400 hover:text-red-600">删除</button>
      </div>
      {isAsst ? (
        <div className="text-sm whitespace-pre-wrap">{msg.content || <span className="text-slate-400">…</span>}</div>
      ) : (
        <textarea
          value={msg.content}
          onChange={(e) => onChange(e.target.value)}
          rows={isSys ? 2 : 3}
          className="w-full bg-transparent text-sm focus:outline-none resize-y"
        />
      )}
    </div>
  )
}
