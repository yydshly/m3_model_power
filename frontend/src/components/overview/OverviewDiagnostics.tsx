/**
 * OverviewDiagnostics.tsx — Advanced diagnostics collapsible section.
 * Shows internal field statistics that are not meant for regular users.
 */
import { useState } from 'react'
import type { OverviewStats } from '../../domain/overviewStats'
import type { WorkbenchStats } from '../../workbenchStatus'

interface Props {
  overviewStats: OverviewStats | null
  workbenchStats: WorkbenchStats | null
}

export default function OverviewDiagnostics({ overviewStats, workbenchStats }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <section className="mt-6">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-slate-700 hover:text-slate-900"
      >
        <span className="text-slate-400">{open ? '▼' : '▶'}</span>
        高级诊断
        <span className="text-xs font-normal text-slate-400">(供开发者排查)</span>
      </button>

      {open && overviewStats && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-4 space-y-4">
          <p className="text-xs text-slate-500">
            以下信息主要用于开发者排查问题，不代表 MiniMax 官方套餐说明。
          </p>

          {/* Scope / coverage */}
          <DiagnosticsGroup title="Token Plan 范围统计">
            <DiagRow label="范围内总计" value={overviewStats.inScopeTotal} sub="in_scope" />
            <DiagRow label="范围内已覆盖" value={overviewStats.inScopeCovered} sub="TokenPlan 范围" />
            <DiagRow label="完成率" value={`${overviewStats.completionPercent}%`} sub="已覆盖 / 范围内" />
            <DiagRow label="只提示" value={overviewStats.warningOnlyTotal} sub="warning_only" />
            <DiagRow label="范围外" value={overviewStats.outOfScopeTotal} sub="out_of_scope" />
          </DiagnosticsGroup>

          {/* Model status */}
          <DiagnosticsGroup title="模型状态">
            <DiagRow label="官方当前模型" value={overviewStats.officialCurrentModels} sub="official_current=true" />
            <DiagRow label="Live 可用模型" value={overviewStats.liveAvailableModels} sub="live_available=true" />
            <DiagRow label="前端启用模型" value={overviewStats.enabledModels} sub="enabled=true" />
            <DiagRow label="Chat live 可用" value={overviewStats.liveAvailableModels} sub="已验收" />
            <DiagRow label="历史/废弃" value={overviewStats.legacyDeprecatedModels} sub="legacy/deprecated" />
            <DiagRow label="capability_probe 待探测" value={overviewStats.capabilityProbePending} sub="capability_probe=unknown" />
          </DiagnosticsGroup>

          {/* Billing */}
          <DiagnosticsGroup title="收费与风险统计">
            <DiagRow label="正常测试" value={overviewStats.normalTokenPlan} sub="normal_token_plan_test" />
            <DiagRow label="配额敏感" value={overviewStats.quotaSensitive} sub="quota_sensitive" />
            <DiagRow label="需付费确认" value={overviewStats.paidConfirm} sub="paid_confirm_required" />
            <DiagRow label="高成本" value={overviewStats.highCost} sub="high_cost_confirm_required" />
            <DiagRow label="素材型" value={overviewStats.assetRequired} sub="asset_required_confirm_required" />
          </DiagnosticsGroup>

          {/* Operation risks */}
          <DiagnosticsGroup title="操作风险统计">
            <DiagRow label="破坏性操作" value={overviewStats.destructiveOps} sub="is_destructive=true" />
            <DiagRow label="长任务" value={overviewStats.longRunningOps} sub="is_long_running=true" />
            <DiagRow label="需确认门禁" value={overviewStats.requiresAnyConfirm} sub="任意确认项" />
          </DiagnosticsGroup>

          {/* Workbench / runner progress */}
          {workbenchStats && (
            <DiagnosticsGroup title="Runner 产品化进度">
              <DiagRow
                label="Token Plan 覆盖"
                value={`${workbenchStats.inScopeTokenPlanCovered}/${workbenchStats.inScopeTotal}`}
                sub="范围内 / 总计"
              />
              <DiagRow
                label="Runner 支持"
                value={`${workbenchStats.runnerSupportedInScope}/${workbenchStats.inScopeTotal}`}
                sub="Runner 支持 / 范围内"
              />
              <DiagRow
                label="高级测试能力"
                value={workbenchStats.advancedTestCapabilities.length}
                sub="advanced test"
              />
              <DiagRow
                label="特殊 UI 能力"
                value={workbenchStats.specialUICapabilities.length}
                sub="tts-ws 等"
              />
            </DiagnosticsGroup>
          )}

          {/* Registry summary */}
          <DiagnosticsGroup title="注册中心摘要">
            <DiagRow label="能力总数" value={overviewStats.totalCapabilities} sub="" />
            <DiagRow label="已实现" value={overviewStats.implementedCapabilities} sub="status=implemented" />
            <DiagRow label="模型总数" value={overviewStats.totalModels} sub="" />
            <DiagRow label="启用模型" value={overviewStats.enabledModels} sub="enabled=true" />
          </DiagnosticsGroup>
        </div>
      )}
    </section>
  )
}

function DiagnosticsGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-600 mb-2">{title}</div>
      <div className="grid grid-cols-4 gap-2">
        {children}
      </div>
    </div>
  )
}

function DiagRow({ label, value, sub }: { label: string; value: string | number; sub: string }) {
  return (
    <div className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-center">
      <div className="text-lg font-semibold text-slate-800">{value}</div>
      <div className="text-[10px] text-slate-600 mt-0.5">{label}</div>
      {sub && <div className="text-[9px] text-slate-400 mt-0.5">{sub}</div>}
    </div>
  )
}
