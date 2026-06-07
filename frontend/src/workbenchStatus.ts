/**
 * Workbench status helpers — derive UX-facing stats from registry + runner templates.
 * Consumed by Overview and Category pages.
 */

import type { Registry } from './api'

export type WorkbenchStats = {
  inScopeTotal: number
  inScopeVerified: number
  runnerSupported: number
  runnerSupportedInScope: number
  advancedTestCapabilities: string[]
  specialUICapabilities: string[]
  riskCapabilities: string[]
}

const ADVANCED_TEST = new Set([
  'chat-responses-tokens',
  'models-openai-list',
  'models-openai-retrieve',
  'models-anthropic-list',
  'models-anthropic-retrieve',
])

const SPECIAL_UI = new Set([
  'tts-ws', // WebSocket 实时语音
])

const RISK_HIGH = new Set([
  'voice-clone-upload-prompt',
  'voice-clone-do',
  'voice-design',
  'music-cover-prep',
  'video-t2v',
  'video-download',
])

export function computeWorkbenchStats(
  registry: Registry,
  runnerSupportedCaps: Set<string>,
): WorkbenchStats {
  const caps = registry.capabilities

  const inScopeTotal = caps.filter(
    (c) => c.scope_policy?.current_scope === 'in_scope',
  ).length

  const inScopeVerified = caps.filter(
    (c) =>
      c.scope_policy?.current_scope === 'in_scope' &&
      (c.billing_policy?.billing_category === 'normal_token_plan_test' ||
        c.billing_policy?.billing_category === 'quota_sensitive'),
  ).length

  const runnerSupportedInScope = caps.filter(
    (c) =>
      c.scope_policy?.current_scope === 'in_scope' &&
      runnerSupportedCaps.has(c.id),
  ).length

  const advancedTestCapabilities = [...ADVANCED_TEST].filter((id) =>
    caps.some((c) => c.id === id),
  )

  const specialUICapabilities = [...SPECIAL_UI].filter((id) =>
    caps.some((c) => c.id === id),
  )

  const riskCapabilities = [...RISK_HIGH].filter((id) =>
    caps.some((c) => c.id === id),
  )

  return {
    inScopeTotal,
    inScopeVerified,
    runnerSupported: runnerSupportedCaps.size,
    runnerSupportedInScope,
    advancedTestCapabilities,
    specialUICapabilities,
    riskCapabilities,
  }
}

export const MODULE_DESCRIPTIONS: Record<
  string,
  {
    description: string
    recommendations: string[]
    riskNotes: string[]
    nextSteps: string[]
  }
> = {
  chat: {
    description:
      '文本对话能力，支持 OpenAI Chat Completions、Anthropic Messages、OpenAI Responses 三种协议，以及 token 计数。',
    recommendations: [
      'chat-openai：通用对话，推荐首选',
      'chat-anthropic：Claude SDK 兼容验证',
      'chat-responses-create：OpenAI Responses API 接入',
      'chat-responses-tokens：仅 token 计数，不需要真实生成',
    ],
    riskNotes: ['所有 chat 能力均为 safe 级别，无需风险确认'],
    nextSteps: [
      '验证三协议对不同模型的响应格式一致性',
      '确认 chat 响应能被 ChatResultPreview 正确提取',
    ],
  },
  voice: {
    description:
      '语音合成与音色管理能力，包括同步 TTS、异步 TTS、WebSocket 实时语音、音色列表、语音克隆、语音设计。',
    recommendations: [
      'tts-sync：短文本语音合成，即时返回',
      'tts-async：长文本异步任务，支持查询和下载',
      'tts-ws：WebSocket 实时流式语音（特殊 UI）',
      'voice-list：查询可用音色列表',
    ],
    riskNotes: [
      'voice-clone-do / voice-clone-upload-prompt：HIGH_RISK，需确认授权',
      'voice-design：HIGH_RISK，需确认授权',
    ],
    nextSteps: [
      '验证 tts-ws WebSocket 连接的稳定性',
      '确认 voice-clone 生成质量的合规性',
    ],
  },
  image: {
    description:
      '图像生成能力，包括文生图（image-t2i）和图生图（image-i2i）。当前图生图仅开放 image-01。',
    recommendations: [
      'image-t2i：文生图，支持 image-01 / image-01-live',
      'image-i2i：图生图（当前仅 image-01）',
    ],
    riskNotes: [
      '⚠️ image-i2i 不是严格局部编辑，主体一致性取决于模型理解',
      '⚠️ image-01-live 是否支持图生图需单独验证',
      'video-t2v / video-download：HIGH_RISK，out_of_scope',
    ],
    nextSteps: [
      '验证 image-01-live 是否支持图生图',
      '确认 image-i2i 主体保持效果的上限',
    ],
  },
  music: {
    description: '音乐生成能力，包括歌词生成和音乐合成。',
    recommendations: [
      'lyrics-gen：歌词生成（safe，TokenPlan 正常验收）',
      'music-gen：音乐合成，生成 WAV/MP3',
    ],
    riskNotes: [
      'music-cover-prep：HIGH_RISK，需确认素材授权',
    ],
    nextSteps: [
      '验证 music-gen 输出音频质量的稳定性',
      '确认歌词与生成音乐的同步对齐效果',
    ],
  },
  file: {
    description:
      '文件资产管理能力，包括文件上传、列表、详情查询、内容读取。',
    recommendations: [
      'file-upload：上传安全小文件，获取 file_id',
      'file-list：查询已上传文件列表',
      'file-retrieve：查询文件元信息',
      'file-content：读取文件内容',
    ],
    riskNotes: [
      'file-upload 需要确认素材来源合法',
      'file-delete：破坏性操作，HIGH_RISK',
    ],
    nextSteps: [
      '验证大文件分片上传的稳定性',
      '确认 file-content 对不同文件类型的读取限制',
    ],
  },
  models: {
    description:
      '模型信息与列表查询，支持 OpenAI 和 Anthropic 模型列表/详情查询。',
    recommendations: [
      'models-openai-list / retrieve：OpenAI 兼容模型列表',
      'models-anthropic-list / retrieve：Anthropic 模型列表',
    ],
    riskNotes: [
      '模型列表查询均为 safe 级别',
      'model probe_status 状态说明：',
      '  official_current：官方主推模型',
      '  live_available：已验收实际可用',
      '  subscription_expected：需订阅确认',
    ],
    nextSteps: [
      '持续更新模型 probe_status 状态',
      '验证新上线模型的兼容性',
    ],
  },
}
