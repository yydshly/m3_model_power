/**
 * overviewStats.ts — Compute UX-facing overview statistics from registry.
 */

import type { Registry } from '../api'
import type { WorkbenchStats } from '../workbenchStatus'

export type OverviewStats = {
  // Scope counts
  inScopeTotal: number
  inScopeCovered: number
  warningOnlyTotal: number
  outOfScopeTotal: number
  completionPercent: number
  // Testability
  directlyTestable: number
  cautionRequired: number
  // Model layer
  officialCurrentModels: number
  liveAvailableModels: number
  enabledModels: number
  legacyDeprecatedModels: number
  capabilityProbePending: number
  // Billing
  normalTokenPlan: number
  quotaSensitive: number
  paidConfirm: number
  highCost: number
  assetRequired: number
  // Operation risks
  destructiveOps: number
  longRunningOps: number
  // Confirmation gates
  requiresAnyConfirm: number
  // Registry summary
  totalCapabilities: number
  implementedCapabilities: number
  totalModels: number
}

export function buildOverviewStats(registry: Registry): OverviewStats {
  const caps = registry.capabilities
  const models = registry.models

  const inScopeTotal = caps.filter((c) => c.scope_policy?.current_scope === 'in_scope').length
  const inScopeCovered = caps.filter(
    (c) =>
      c.scope_policy?.current_scope === 'in_scope' &&
      (c.billing_policy?.billing_category === 'normal_token_plan_test' ||
        c.billing_policy?.billing_category === 'quota_sensitive'),
  ).length
  const warningOnlyTotal = caps.filter((c) => c.scope_policy?.current_scope === 'warning_only').length
  const outOfScopeTotal = caps.filter((c) => c.scope_policy?.current_scope === 'out_of_scope').length

  // Directly testable: in_scope + implemented + normal billing
  const directlyTestable = caps.filter(
    (c) =>
      c.scope_policy?.current_scope === 'in_scope' &&
      c.status === 'implemented' &&
      c.billing_policy?.billing_category === 'normal_token_plan_test',
  ).length

  // Caution required: anything that needs confirmation or is high cost
  const cautionRequired = caps.filter((c) => {
    if (c.scope_policy?.current_scope !== 'in_scope') return true
    const bp = c.billing_policy
    const op = c.operation_policy
    if (bp?.billing_category === 'quota_sensitive') return true
    if (bp?.billing_category === 'paid_confirm_required') return true
    if (bp?.billing_category === 'high_cost_confirm_required') return true
    if (bp?.billing_category === 'asset_required_confirm_required') return true
    if (bp?.requires_explicit_confirmation) return true
    if (bp?.may_charge_extra) return true
    if (op?.is_destructive) return true
    if (op?.is_long_running) return true
    if (op?.requires_uploaded_asset) return true
    if (op?.operation_risk === 'quota_guarded') return true
    return false
  }).length

  const completionPercent = inScopeTotal > 0 ? Math.round((inScopeCovered / inScopeTotal) * 100) : 0

  return {
    inScopeTotal,
    inScopeCovered,
    warningOnlyTotal,
    outOfScopeTotal,
    completionPercent,
    directlyTestable,
    cautionRequired,
    officialCurrentModels: models.filter((m) => m.official_current).length,
    liveAvailableModels: models.filter((m) => m.live_available === true).length,
    enabledModels: models.filter((m) => m.enabled).length,
    legacyDeprecatedModels: models.filter((m) => m.tier === 'legacy' || m.tier === 'deprecated').length,
    capabilityProbePending: models.filter((m) => m.discovery_method === 'capability_probe' && m.discovery_status === 'unknown').length,
    normalTokenPlan: caps.filter((c) => c.billing_policy?.billing_category === 'normal_token_plan_test').length,
    quotaSensitive: caps.filter((c) => c.billing_policy?.billing_category === 'quota_sensitive').length,
    paidConfirm: caps.filter((c) => c.billing_policy?.billing_category === 'paid_confirm_required').length,
    highCost: caps.filter((c) => c.billing_policy?.billing_category === 'high_cost_confirm_required').length,
    assetRequired: caps.filter((c) => c.billing_policy?.billing_category === 'asset_required_confirm_required').length,
    destructiveOps: caps.filter((c) => c.operation_policy?.is_destructive === true).length,
    longRunningOps: caps.filter((c) => c.operation_policy?.is_long_running === true).length,
    requiresAnyConfirm: caps.filter((c) => {
      const bp = c.billing_policy
      const op = c.operation_policy
      if (bp?.may_charge_extra) return true
      if (bp?.billing_category === 'high_cost_confirm_required') return true
      if (bp?.requires_explicit_confirmation) return true
      if (op?.is_destructive) return true
      if (op?.requires_uploaded_asset) return true
      if (op?.is_long_running) return true
      if (op?.requires_existing_task) return true
      return false
    }).length,
    totalCapabilities: caps.length,
    implementedCapabilities: caps.filter((c) => c.status === 'implemented').length,
    totalModels: models.length,
  }
}

export function buildWorkbenchStats(registry: Registry, runnerSupported: Set<string>): WorkbenchStats {
  const caps = registry.capabilities

  const inScopeTotal = caps.filter((c) => c.scope_policy?.current_scope === 'in_scope').length
  const inScopeTokenPlanCovered = caps.filter(
    (c) =>
      c.scope_policy?.current_scope === 'in_scope' &&
      (c.billing_policy?.billing_category === 'normal_token_plan_test' ||
        c.billing_policy?.billing_category === 'quota_sensitive'),
  ).length
  const runnerSupportedInScope = caps.filter(
    (c) => c.scope_policy?.current_scope === 'in_scope' && runnerSupported.has(c.id),
  ).length

  return {
    inScopeTotal,
    inScopeTokenPlanCovered,
    runnerSupported: runnerSupported.size,
    runnerSupportedInScope,
    advancedTestCapabilities: [],
    specialUICapabilities: [],
    riskCapabilities: [],
  }
}
