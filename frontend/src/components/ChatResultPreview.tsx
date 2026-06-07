import { useState } from 'react'
import { JsonView } from './JsonView'

// ── Protocol detection & text extraction ──────────────────────────────────────

type ChatProtocol = 'openai' | 'anthropic' | 'responses' | 'unknown'

function getTextBlockText(block: { type?: string; text?: string } | null | undefined): string | null {
  if (!block?.text) return null
  // 'thinking' / 'reasoning_text' are MiniMax internal reasoning blocks — still user-facing text
  if (!block.type || block.type === 'text' || block.type === 'output_text' || block.type === 'thinking' || block.type === 'reasoning_text') {
    return block.text
  }
  return null
}

function detectProtocol(data: unknown): ChatProtocol {
  if (!data || typeof data !== 'object') return 'unknown'
  const d = data as Record<string, unknown>

  // Anthropic Messages: content array with a text-like block (text, thinking, etc.)
  if (Array.isArray(d.content)) {
    const first = (d as { content?: Array<{ type?: string; text?: string }> }).content?.[0]
    // Accept text, bare block, or internal reasoning blocks (thinking) as anthropic
    if (first?.text && (!first.type || first.type === 'text' || first.type === 'thinking')) return 'anthropic'
  }

  // Also check nested data.content (proxy wrapper)
  const nested = (d as { data?: { content?: Array<{ type?: string; text?: string }> } }).data
  if (nested?.content?.[0]?.text) return 'anthropic'

  // Responses API: has output_text or output array
  if ('output_text' in d) return 'responses'
  if (Array.isArray(d.output)) return 'responses'

  // OpenAI Chat: has choices array
  if (Array.isArray(d.choices)) return 'openai'

  return 'unknown'
}

function extractChatText(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>

  // OpenAI Chat Completions
  if (Array.isArray(d.choices)) {
    const choices = d.choices as Array<{ message?: { content?: string } }>
    for (const c of choices) {
      if (c.message?.content) return c.message.content
    }
  }

  // Anthropic Messages
  if (Array.isArray(d.content)) {
    const content = d.content as Array<{ type?: string; text?: string }>
    for (const c of content) {
      const text = getTextBlockText(c)
      if (text) return text
    }
  }
  // Also check nested data.content (some proxy wrappers)
  const nested = (d as { data?: { content?: Array<{ type?: string; text?: string }> } }).data
  if (nested?.content?.[0]?.text) {
    return nested.content[0].text ?? null
  }

  // Responses API
  if ('output_text' in d && typeof d.output_text === 'string') {
    return d.output_text
  }
  if (Array.isArray(d.output)) {
    const output = d.output as Array<{ content?: Array<{ type?: string; text?: string }>; text?: string; type?: string }>
    for (const o of output) {
      // output_text type block
      if (o.text && (!o.type || o.type === 'output_text')) return o.text
      if (Array.isArray(o.content)) {
        for (const c of o.content) {
          const text = getTextBlockText(c)
          if (text) return text
        }
      }
    }
  }

  return null
}

interface UsageInfo {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  input_tokens?: number
  output_tokens?: number
}

function extractUsage(data: unknown): UsageInfo | null {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  const u = (d.usage ?? (d as { data?: { usage?: UsageInfo } }).data?.usage) as UsageInfo | undefined
  if (!u) return null
  return {
    prompt_tokens: u.prompt_tokens ?? u.input_tokens,
    completion_tokens: u.completion_tokens ?? u.output_tokens,
    total_tokens: u.total_tokens,
    input_tokens: u.input_tokens,
    output_tokens: u.output_tokens,
  }
}

function extractFinishReason(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  return (d.finish_reason ?? d.stop_reason ?? d.status ?? null) as string | null
}

function protocolLabel(p: ChatProtocol): string {
  switch (p) {
    case 'openai': return 'OpenAI Chat Completions'
    case 'anthropic': return 'Anthropic Messages'
    case 'responses': return 'OpenAI Responses'
    default: return '未知协议'
  }
}

function CopyButton({ text, children }: { text: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false)
  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <button
      onClick={handleCopy}
      className={`text-xs px-2 py-0.5 rounded border transition-colors ${copied ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'}`}
    >
      {copied ? '✓ 复制' : children}
    </button>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

interface ChatResultPreviewProps {
  data: unknown
}

export default function ChatResultPreview({ data }: ChatResultPreviewProps) {
  const protocol = detectProtocol(data)
  const text = extractChatText(data)
  const usage = extractUsage(data)
  const finishReason = extractFinishReason(data)
  const model = (data as Record<string, unknown>).model as string | undefined

  const hasUsage = usage && (usage.total_tokens != null || usage.prompt_tokens != null || usage.input_tokens != null)

  return (
    <div className="space-y-3">
      {/* Protocol badge + model */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
          {protocolLabel(protocol)}
        </span>
        {model && (
          <span className="text-xs text-slate-500">模型：<span className="font-mono">{model}</span></span>
        )}
        {finishReason && (
          <span className="text-xs text-slate-400">结束原因：{finishReason}</span>
        )}
      </div>

      {/* Main answer card */}
      {text ? (
        <div className="border border-blue-200 rounded-lg p-4 bg-blue-50/30">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-800 whitespace-pre-wrap break-words leading-relaxed">
                {text}
              </p>
            </div>
            <div className="flex-shrink-0">
              <CopyButton text={text}>
                复制回答
              </CopyButton>
            </div>
          </div>
        </div>
      ) : (
        <div className="border border-amber-200 rounded-lg p-3 bg-amber-50 text-xs text-amber-700">
          未识别到回答文本，请查看下方完整 JSON。
        </div>
      )}

      {/* Usage info */}
      {hasUsage && (
        <div className="flex flex-wrap gap-3 text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded p-2">
          {usage.input_tokens != null && (
            <span>输入 Token：{usage.input_tokens}</span>
          )}
          {usage.output_tokens != null && (
            <span>输出 Token：{usage.output_tokens}</span>
          )}
          {usage.total_tokens != null && (
            <span>总 Token：{usage.total_tokens}</span>
          )}
          {usage.prompt_tokens != null && usage.input_tokens == null && (
            <span>输入 Token：{usage.prompt_tokens}</span>
          )}
          {usage.completion_tokens != null && usage.output_tokens == null && (
            <span>输出 Token：{usage.completion_tokens}</span>
          )}
        </div>
      )}

      {/* Full JSON (collapsed by default) */}
      <details className="text-xs">
        <summary className="cursor-pointer text-slate-500 hover:text-slate-700 px-1">
          展开完整 JSON
        </summary>
        <div className="mt-2 rounded border border-slate-200 overflow-auto max-h-64">
          <JsonView data={data} />
        </div>
      </details>
    </div>
  )
}
