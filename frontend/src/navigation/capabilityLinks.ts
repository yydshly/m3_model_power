// Unified navigation links for capability-related pages.
// All cross-page links should use these utilities instead of hardcoding URLs.

import type { Model } from '../api'

// Capabilities directly supported by the guided Runner experience (A-class).
export const RUNNER_SUPPORTED_CAPABILITIES = new Set([
  'lyrics-gen',
  'music-gen',
  'voice-list',
  'tts-sync',
  'image-t2i',
  'image-i2i',
  'chat-openai',
  // file chain (P1-1)
  'file-upload',
  'file-list',
  'file-retrieve',
  'file-content',
  // tts-async (P1-2)
  'tts-async',
])

// Capabilities that require quota confirmation before execution.
export const QUOTA_SENSITIVE_CAPABILITIES = new Set([
  'music-gen',
])

// Capabilities that require asset source confirmation.
export const ASSET_GUARDED_CAPABILITIES = new Set([
  'image-i2i',
])

// D-class capabilities: warning_only / out_of_scope / destructive — risk abilities not default-executable.
export const HIGH_RISK_CAPABILITIES = new Set([
  // video (out_of_scope)
  'video-t2v',
  'video-i2v',
  'video-s2v',
  'video-query',
  'video-download',
  // voice clone/design (warning_only)
  'voice-clone-upload-audio',
  'voice-clone-upload-prompt',
  'voice-clone-do',
  'voice-design',
  // destructive (warning_only)
  'voice-delete',
  'file-delete',
  // music (warning_only)
  'music-cover-prep',
])

// B-class capabilities: in_scope, verified, but Runner not productized — TestConsole available.
export const ADVANCED_TEST_CAPABILITIES = new Set([
  'chat-anthropic',
  'chat-responses-create',
  'chat-responses-tokens',
  'models-openai-list',
  'models-openai-retrieve',
  'models-anthropic-list',
  'models-anthropic-retrieve',
])

// C-class capabilities: in_scope, Runner not productized, require special UI (WS / async).
export const RUNNER_NOT_PRODUCTIZED_CAPABILITIES = new Set([
  'tts-ws',
])

// Map model family → default Runner capability.
const FAMILY_TO_DEFAULT_CAPABILITY: Record<string, string> = {
  chat: 'chat-openai',
  speech: 'tts-sync',
  voice: 'tts-sync',
  image: 'image-t2i',
  vision: 'image-t2i',
  music: 'music-gen',
}

// Map model family → profile family for /capability-profiles.
export const MODEL_FAMILY_TO_PROFILE_FAMILY: Record<string, string> = {
  chat: 'chat',
  speech: 'voice',
  image: 'vision',
  music: 'music',
}

// Map profile family → capability family emoji.
export const PROFILE_FAMILY_EMOJI: Record<string, string> = {
  chat: '💬',
  voice: '🎙️',
  vision: '🖼️',
  music: '🎵',
}

/** Returns true if a capability can be used in the guided Runner. */
export function isRunnerSupported(capabilityId: string): boolean {
  return RUNNER_SUPPORTED_CAPABILITIES.has(capabilityId)
}

/** Returns true if a capability requires quota confirmation. */
export function isQuotaSensitive(capabilityId: string): boolean {
  return QUOTA_SENSITIVE_CAPABILITIES.has(capabilityId)
}

/** Returns true if a capability requires asset source confirmation. */
export function isAssetGuarded(capabilityId: string): boolean {
  return ASSET_GUARDED_CAPABILITIES.has(capabilityId)
}

/** Returns true if a capability is high-risk. */
export function isHighRisk(capabilityId: string): boolean {
  return HIGH_RISK_CAPABILITIES.has(capabilityId)
}

/** Returns true if a capability is B-class: in_scope, TestConsole available, Runner not productized. */
export function isAdvancedTest(capabilityId: string): boolean {
  return ADVANCED_TEST_CAPABILITIES.has(capabilityId)
}

/** Returns true if a capability is C-class: Runner not productized, needs special UI. */
export function isRunnerNotProductized(capabilityId: string): boolean {
  return RUNNER_NOT_PRODUCTIZED_CAPABILITIES.has(capabilityId)
}

/** Link to capability detail page (/cap/:id). */
export function getCapabilityDetailLink(capabilityId: string): string {
  return `/cap/${capabilityId}`
}

/** Link to Runner experience page. Returns null if not runner-supported. */
export function getRunnerLink(
  capabilityId: string,
  params?: Record<string, string>
): string | null {
  if (!isRunnerSupported(capabilityId)) return null
  const url = `/capability-runner?capability=${encodeURIComponent(capabilityId)}`
  if (!params) return url
  const qs = new URLSearchParams(params).toString()
  return `${url}&${qs}`
}

/** Link to test console for a capability. */
export function getTestConsoleLink(capabilityId: string): string {
  return `/test-console?capability=${encodeURIComponent(capabilityId)}`
}

/** Link to workflow detail page. */
export function getWorkflowLink(workflowId: string, fromScenario?: string): string {
  const base = `/capability-workflows?workflow=${encodeURIComponent(workflowId)}`
  if (fromScenario) return `${base}&from_scenario=${encodeURIComponent(fromScenario)}`
  return base
}

/** Link to scenario list or specific scenario. */
export function getScenarioLink(scenarioId?: string): string {
  if (scenarioId) return `/capability-scenarios?scenario=${encodeURIComponent(scenarioId)}`
  return '/capability-scenarios'
}

/** Link to capability profiles page, optionally filtered by family. */
export function getProfileLink(family?: string): string {
  if (family) return `/capability-profiles?family=${encodeURIComponent(family)}`
  return '/capability-profiles'
}

/**
 * Get the primary runner capability for a model.
 * Returns null if the model family has no direct Runner experience.
 */
export function getRunnerLinkForModel(model: Model): string | null {
  const cap = FAMILY_TO_DEFAULT_CAPABILITY[model.family]
  if (!cap) return null
  // High-risk model families (video, etc.) have no Runner support
  if (model.family === 'video') return null
  return getRunnerLink(cap, { model: model.id })
}

/**
 * From a list of scenario capabilities, pick the first one that is
 * runner-supported and has acceptable risk (not high-risk).
 * Returns null if no suitable capability found.
 */
export function getPrimaryRunnerCapabilityForScenario(capabilities: string[]): string | null {
  for (const cap of capabilities) {
    if (!isRunnerSupported(cap)) continue
    if (isHighRisk(cap)) continue
    return cap
  }
  return null
}

/**
 * From a list of scenario capabilities, pick the first guarded (requires confirmation)
 * runner capability. Used to show which capabilities in the chain need user confirmation.
 */
export function getFirstGuardedRunnerCapability(capabilities: string[]): string | null {
  for (const cap of capabilities) {
    if (!isRunnerSupported(cap)) continue
    if (isQuotaSensitive(cap) || isAssetGuarded(cap)) return cap
  }
  return null
}

/**
 * Get a human-readable status label for a capability's testability.
 *
 * A 类 (Runner-supported): 可直接体验 / 需额度确认 / 需图片来源确认
 * B 类 (ADVANCED_TEST):    高级测试可用
 * C 类 (RUNNER_NOT_PRODUCTIZED): Runner 未产品化
 * D 类 (HIGH_RISK):        风险能力
 * Default:                 仅详情说明
 */
export function getCapabilityTestabilityLabel(
  capabilityId: string
): { text: string; cls: string } {
  if (isRunnerSupported(capabilityId)) {
    if (isQuotaSensitive(capabilityId)) {
      return { text: '需额度确认', cls: 'bg-orange-100 text-orange-700' }
    }
    if (isAssetGuarded(capabilityId)) {
      return { text: '需图片来源确认', cls: 'bg-orange-100 text-orange-700' }
    }
    return { text: '可直接体验', cls: 'bg-emerald-100 text-emerald-700' }
  }

  if (isHighRisk(capabilityId)) {
    return { text: '风险能力', cls: 'bg-red-100 text-red-700' }
  }

  if (isAdvancedTest(capabilityId)) {
    return { text: '高级测试可用', cls: 'bg-sky-100 text-sky-700' }
  }

  if (isRunnerNotProductized(capabilityId)) {
    return { text: 'Runner 未产品化', cls: 'bg-amber-100 text-amber-700' }
  }

  return { text: '仅详情说明', cls: 'bg-slate-100 text-slate-500' }
}

/**
 * Describe the chain of capabilities in a scenario with testability indicators.
 */
export interface ChainStep {
  capabilityId: string
  label: string
  testability: ReturnType<typeof getCapabilityTestabilityLabel>
}

export function getScenarioChainSteps(capabilities: string[]): ChainStep[] {
  return capabilities.map(cap => ({
    capabilityId: cap,
    label: cap,
    testability: getCapabilityTestabilityLabel(cap),
  }))
}
