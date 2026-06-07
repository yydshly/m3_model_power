import type { Capability } from '../api'

export const CONFIRM_KEYS = {
  paid: 'confirm_paid',
  highCost: 'confirm_high_cost',
  destructive: 'confirm_destructive',
  assetSource: 'confirm_asset_source',
  longRunning: 'confirm_long_running',
  existingTask: 'confirm_existing_task',
  quota: 'confirm_quota',
  veryLargeQuota: 'confirm_very_large_quota',
} as const

export function getRequiredConfirmations(cap: Capability): string[] {
  const required: string[] = []
  const bp = cap.billing_policy
  const op = cap.operation_policy

  if (bp?.may_charge_extra) required.push(CONFIRM_KEYS.paid)

  if (bp?.billing_category === 'high_cost_confirm_required') {
    required.push(CONFIRM_KEYS.highCost)
  }

  if (
    bp?.billing_category === 'quota_sensitive' &&
    bp?.requires_explicit_confirmation
  ) {
    required.push(CONFIRM_KEYS.quota)
  }

  if (op?.is_destructive) required.push(CONFIRM_KEYS.destructive)
  if (op?.requires_uploaded_asset) required.push(CONFIRM_KEYS.assetSource)
  if (op?.is_long_running) required.push(CONFIRM_KEYS.longRunning)
  if (op?.requires_existing_task) required.push(CONFIRM_KEYS.existingTask)

  if (cap.id === 'tts-async') {
    // tts-async 仍保留字符数保护说明，但 confirm_quota 不能只属于 tts-async
    if (!required.includes(CONFIRM_KEYS.quota)) required.push(CONFIRM_KEYS.quota)
  }

  return Array.from(new Set(required))
}

export function allConfirmationsSatisfied(
  required: string[],
  confirmations: Record<string, boolean>,
): boolean {
  return required.every((key) => confirmations[key])
}

export const CONFIRM_LABELS: Record<string, string> = {
  confirm_paid: '我确认该能力可能产生额外费用',
  confirm_high_cost: '我确认这是高成本能力',
  confirm_destructive: '我确认这是破坏性操作，删除后可能无法恢复',
  confirm_asset_source: '我确认上传/引用素材来源合法，且已获得必要授权',
  confirm_long_running: '我确认这是长任务，可能需要等待并消耗较多额度',
  confirm_existing_task: '我确认已提供已有 task_id / file_id',
  confirm_quota: '我确认该能力会消耗 Token Plan / 额度，允许本次执行',
  confirm_very_large_quota: '我确认这是超大额度请求，本轮默认仍不建议执行',
}
