/**
 * Payload validation — shared module for blocking real API calls
 * when required business fields are missing.
 *
 * Used by InvokePanel, TestConsole, and CapabilityRunner to give
 * early feedback before hitting the MiniMax API.
 */

export type PayloadValidationIssue = {
  field: string
  message: string
  severity: 'error' | 'warning'
}

export type PayloadValidationResult = {
  valid: boolean
  issues: PayloadValidationIssue[]
}

function getPathValue(obj: unknown, path: string): unknown {
  return path.split('.').reduce((cur: any, key) => {
    if (cur == null) return undefined
    return cur[key]
  }, obj as any)
}

function isBlank(value: unknown): boolean {
  return value == null || (typeof value === 'string' && value.trim() === '')
}

export function validatePayloadForCapability(
  capabilityId: string,
  payload: unknown,
): PayloadValidationResult {
  const issues: PayloadValidationIssue[] = []
  const p = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {}

  const requireField = (path: string, message: string) => {
    if (isBlank(getPathValue(p, path))) {
      issues.push({ field: path, message, severity: 'error' })
    }
  }

  switch (capabilityId) {
    case 'tts-sync':
      requireField('model', '请选择语音模型')
      requireField('text', '请填写要合成的文本')
      requireField('voice_setting.voice_id', '请填写 voice_id，可先通过 voice-list 查询可用音色')
      break

    case 'chat-openai':
    case 'chat-anthropic':
      requireField('model', '请选择模型')
      if (!Array.isArray((p as any).messages) || (p as any).messages.length === 0) {
        issues.push({ field: 'messages', message: '请填写至少一条 user message', severity: 'error' })
      }
      break

    case 'chat-responses-create':
    case 'chat-responses-tokens':
      requireField('model', '请选择模型')
      requireField('input', '请填写 input')
      break

    case 'image-t2i':
      requireField('model', '请选择图片模型')
      requireField('prompt', '请填写图片 prompt')
      break

    case 'image-i2i':
      requireField('model', '请选择图片模型')
      requireField('img_url', '请填写真实可访问的参考图片 URL')
      requireField('prompt', '请填写图生图 prompt')
      break

    case 'lyrics-gen':
      requireField('prompt', '请填写歌词主题或提示词')
      break

    case 'music-gen':
      requireField('model', '请选择音乐模型')
      requireField('lyrics', '请填写歌词')
      requireField('prompt', '请填写音乐风格 prompt')
      break

    case 'file-retrieve':
    case 'file-content':
    case 'file-delete':
      requireField('file_id', '请填写真实 file_id')
      break

    case 'models-openai-retrieve':
    case 'models-anthropic-retrieve':
      requireField('model', '请填写 model')
      break
  }

  return { valid: issues.every(i => i.severity !== 'error'), issues }
}
