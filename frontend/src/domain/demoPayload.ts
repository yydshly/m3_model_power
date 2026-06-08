/**
 * buildDemoPayload — returns a safe, usable demo payload for each capability.
 *
 * Priority:
 *  1. capability.example if it has meaningful content (non-empty, not just {})
 *  2. Hard-coded safe demo per capability_id
 *  3. Minimal fallback that at least has a model field
 *
 * This prevents TestConsole from showing {} as the payload for capabilities
 * that have no example, which causes immediate API parameter errors.
 */
import type { Capability, RunnerTemplate } from '../api'

// Safe demo payloads per capability_id
const DEMO_PAYLOADS: Record<string, Record<string, unknown>> = {
  'chat-openai': {
    model: 'MiniMax-M3',
    prompt: '请用一句话介绍 MiniMax。',
    max_tokens: 256,
  },
  'chat-anthropic': {
    model: 'MiniMax-M3',
    prompt: '请用一句话介绍 MiniMax。',
    max_tokens: 256,
  },
  'chat-responses-create': {
    model: 'MiniMax-M3',
    input: '请用一句话介绍 MiniMax。',
    max_output_tokens: 256,
  },
  'chat-responses-tokens': {
    model: 'MiniMax-M3',
    input: '你好，请用一句话介绍 MiniMax。',
  },
  'tts-sync': {
    model: 'speech-02',
    text: '你好，这是 MiniMax 语音合成测试。',
    stream: false,
  },
  'voice-list': {},
  'tts-async': {
    model: 'speech-02',
    text: '你好，这是异步语音合成测试。',
    mode: 'start',
  },
  'image-t2i': {
    model: 'image-01',
    prompt: '一只橘色的猫在阳光下打盹，超写实风格',
  },
  'lyrics-gen': {
    model: 'lyrics-01',
    prompt: '关于夏天的温暖记忆',
    genre: 'pop',
    style: 'warm',
  },
  'music-gen': {
    model: 'music-01',
    lyrics: '夏日晚风吹过田野\n我在旧路口等一场落日\n蝉声慢慢落进云里\n心事也变得安静',
    instrumental: false,
  },
  'image-i2i': {
    model: 'image-01',
    img_url: 'https://example.com/reference.jpg',
    prompt: '保持原图主体，换成油画风格',
    reference_mode: 'subject',
  },
  'file-list': {
    purpose: 'retrieval',
    page: 1,
    page_size: 10,
  },
  'file-retrieve': {
    file_id: '替换为实际的 file_id',
    purpose: 'retrieval',
  },
  'file-content': {
    file_id: '替换为实际的 file_id',
    purpose: 'retrieval',
  },
  'file-upload': {
    purpose: 'retrieval',
    // file must be provided by user, cannot have a default
  },
  'models-openai-list': {},
  'models-anthropic-list': {},
}

// Capabilities that require model selection
const REQUIRES_MODEL: Record<string, boolean> = {
  'chat-openai': true,
  'chat-anthropic': true,
  'chat-responses-create': true,
  'chat-responses-tokens': true,
  'tts-sync': true,
  'tts-async': true,
  'image-t2i': true,
  'lyrics-gen': true,
  'music-gen': true,
  'image-i2i': true,
}

function _isNonEmptyExample(example: Record<string, unknown> | undefined): boolean {
  if (!example || typeof example !== 'object') return false
  const keys = Object.keys(example)
  if (keys.length === 0) return false
  // Check if all values are empty strings
  return keys.some(k => {
    const v = (example as Record<string, unknown>)[k]
    if (v === null || v === undefined) return false
    if (typeof v === 'string' && v.trim() === '') return false
    return true
  })
}

export function buildDemoPayload(
  capability: Capability,
  runnerTemplate?: RunnerTemplate
): Record<string, unknown> {
  const capId = capability.id

  // Use capability.example if it has content
  if (_isNonEmptyExample(capability.example)) {
    const payload = { ...capability.example }
    // Ensure model field is present for model-required capabilities
    if (REQUIRES_MODEL[capId] && !('model' in payload)) {
      payload.model = _defaultModel(capId)
    }
    return payload
  }

  // Use runnerTemplate payload_template + form defaults if available
  if (runnerTemplate) {
    const fromTemplate = buildFromTemplate(runnerTemplate)
    if (Object.keys(fromTemplate).length > 0) {
      return fromTemplate
    }
  }

  // Fall back to hard-coded demos
  if (DEMO_PAYLOADS[capId]) {
    return { ...DEMO_PAYLOADS[capId] }
  }

  // Ultimate fallback
  return {}
}

function _defaultModel(capId: string): string {
  const modelMap: Record<string, string> = {
    'chat-openai': 'MiniMax-M3',
    'chat-anthropic': 'MiniMax-M3',
    'chat-responses-create': 'MiniMax-M3',
    'chat-responses-tokens': 'MiniMax-M3',
    'tts-sync': 'speech-02',
    'tts-async': 'speech-02',
    'image-t2i': 'image-01',
    'lyrics-gen': 'lyrics-01',
    'music-gen': 'music-01',
    'image-i2i': 'image-01',
  }
  return modelMap[capId] ?? 'MiniMax-M3'
}

function buildFromTemplate(template: RunnerTemplate): Record<string, unknown> {
  const result: Record<string, unknown> = {}

  // Start with payload_template
  if (template.payload_template && typeof template.payload_template === 'object') {
    Object.assign(result, template.payload_template)
  }

  // Fill in form schema defaults for missing fields
  const formSchema = template.form_schema
  if (formSchema) {
    for (const [key, field] of Object.entries(formSchema)) {
      if (key in result) continue
      if (field.default && field.default !== '') {
        result[key] = field.default
      }
    }
  }

  // Ensure model field
  if (REQUIRES_MODEL[template.capability_id] && !('model' in result)) {
    result['model'] = _defaultModel(template.capability_id)
  }

  return result
}
