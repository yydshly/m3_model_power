export function scopeLabel(scope: string): string {
  return {
    in_scope: '范围内',
    warning_only: '只提示',
    out_of_scope: '范围外',
  }[scope] ?? scope
}

export function billingLabel(category: string): string {
  return {
    normal_token_plan_test: 'Token Plan',
    quota_sensitive: '额度敏感',
    paid_confirm_required: '需付费确认',
    high_cost_confirm_required: '高成本',
    asset_required_confirm_required: '素材/授权',
  }[category] ?? category
}

export function operationRiskLabel(risk: string): string {
  return {
    normal: '普通',
    destructive: '破坏性',
    asset_required: '需素材',
    existing_task_only: '仅已有任务',
    long_running: '长任务',
    quota_guarded: '额度保护',
  }[risk] ?? risk
}

export function modelTierLabel(tier: string): string {
  return {
    flagship: '旗舰',
    highspeed: '极速档',
    standard: '标准',
    hd: 'HD',
    turbo: 'Turbo',
    legacy: '旧版',
    deprecated: '废弃',
  }[tier] ?? tier
}

export function quotaLabel(eligible: boolean): string {
  return eligible ? '极速额度' : '标准计量'
}

export function quotaTitle(eligible: boolean): string {
  return eligible
    ? '走 TokenPlanPlus 极速档共享额度'
    : '不走极速档共享额度，按模型标准计量；不等于一定产生额外收费'
}
