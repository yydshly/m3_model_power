import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHealth, type HealthResp } from '../api'
import { useRegistry } from '../store'

const PLAN_FEATURES = [
  '支持 MiniMax 全系模型（M3 / M2.7 / 图像 / 语音 / 音乐）',
  '可同时支持 3-4 个 Agent 并发运行',
  '支持主流的编程工具，并持续扩展中',
  '1M 长上下文，适合处理长文档 / 大型代码库',
  'M3 原生多模态理解：图像 / 视频输入',
  '文本 / 图像 / 语音 / 音乐 共享同一额度',
  '月度约 12 亿+ token M3 用量（极速档）',
]

export default function Overview() {
  const { registry, error: regErr } = useRegistry()
  const [h, setH] = useState<HealthResp | null>(null)
  const [healthErr, setHealthErr] = useState<string | null>(null)

  useEffect(() => {
    getHealth().then(setH).catch((e) => setHealthErr(String(e)))
  }, [])

  const stats = registry && {
    total: registry.capabilities.length,
    implemented: registry.capabilities.filter((c) => c.status === 'implemented').length,
    planned: registry.capabilities.filter((c) => c.status === 'planned').length,
    unsupported: registry.capabilities.filter((c) => c.status === 'unsupported').length,
    models: registry.models.filter((m) => m.enabled).length,
    quota: registry.models.filter((m) => m.enabled && m.quota_eligible).length,
    // 4-layer model status
    officialCurrent: registry.models.filter((m) => m.official_current).length,
    liveAvailable: registry.models.filter((m) => m.live_available === true).length,
    legacyHidden: registry.models.filter((m) => m.enabled && !m.official_current).length,
    // full coverage stats
    liveChatModels: registry.models.filter((m) => m.family === 'chat' && m.live_available === true).length,
    localConfigured: registry.models.length,
    capabilityProbePending: registry.models.filter((m) => m.discovery_method === 'capability_probe' && m.discovery_status === 'unknown').length,
    officialCurrentNonLive: registry.models.filter((m) => m.official_current && m.live_available !== true && m.tier !== 'legacy' && m.tier !== 'deprecated').length,
    highspeedCount: registry.models.filter((m) => m.tier === 'highspeed').length,
    // billing category stats
    normalTokenPlanTest: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'normal_token_plan_test').length,
    quotaSensitive: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'quota_sensitive').length,
    paidConfirmRequired: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'paid_confirm_required').length,
    highCostConfirmRequired: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'high_cost_confirm_required').length,
    assetRequiredConfirmRequired: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'asset_required_confirm_required').length,
    mayChargeExtra: registry.capabilities.filter((c) => c.billing_policy?.may_charge_extra === true).length,
    requiresExplicitConfirm: registry.capabilities.filter((c) => c.billing_policy?.requires_explicit_confirmation === true).length,
    // operation risk stats
    opNormal: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'normal').length,
    opDestructive: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'destructive').length,
    opAssetRequired: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'asset_required').length,
    opExistingTaskOnly: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'existing_task_only').length,
    opLongRunning: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'long_running').length,
    opQuotaGuarded: registry.capabilities.filter((c) => c.operation_policy?.operation_risk === 'quota_guarded').length,
    opRequiresConfirm: registry.capabilities.filter((c) => c.operation_policy?.requires_operation_confirmation === true).length,
    // confirmation gate stats
    requiresAnyConfirm: registry.capabilities.filter((c) => {
      const bp = c.billing_policy
      const op = c.operation_policy
      if (bp.may_charge_extra) return true
      if (bp.billing_category === 'high_cost_confirm_required') return true
      if (bp.requires_explicit_confirmation) return true
      if (op.is_destructive) return true
      if (op.requires_uploaded_asset) return true
      if (op.is_long_running) return true
      if (op.requires_existing_task) return true
      if (c.id === 'tts-async') return true
      return false
    }).length,
    confirmPaid: registry.capabilities.filter((c) => c.billing_policy?.may_charge_extra === true).length,
    confirmHighCost: registry.capabilities.filter((c) => c.billing_policy?.billing_category === 'high_cost_confirm_required').length,
    confirmDestructive: registry.capabilities.filter((c) => c.operation_policy?.is_destructive === true).length,
    confirmAssetSource: registry.capabilities.filter((c) => c.operation_policy?.requires_uploaded_asset === true).length,
    confirmLongRunning: registry.capabilities.filter((c) => c.operation_policy?.is_long_running === true).length,
    confirmExistingTask: registry.capabilities.filter((c) => c.operation_policy?.requires_existing_task === true).length,
    confirmQuota: registry.capabilities.filter((c) => c.id === 'tts-async').length,
  }

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-semibold text-slate-900">MiniMax 能力聚合工作台</h1>
      <p className="text-slate-600 mt-2 text-sm">
        TokenPlanPlus 极速版年度会员 · 下次续费 2027-05-29 · 所有能力配置驱动，可在 backend/config/*.yaml 中维护
      </p>

      <section className="mt-6 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-5 col-span-2">
          <div className="text-sm text-slate-500">订阅档位</div>
          <div className="text-lg font-semibold mt-1">Plus · 极速版</div>
          <ul className="mt-3 grid grid-cols-2 gap-y-1.5 text-sm text-slate-700">
            {PLAN_FEATURES.map((f) => (
              <li key={f} className="flex gap-2">
                <span className="text-emerald-500">✓</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="text-sm text-slate-500">连通状态</div>
          {healthErr && <div className="mt-2 text-sm text-red-600">后端不可达：{healthErr}</div>}
          {h && (
            <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
              <dt className="text-slate-500">Base</dt>
              <dd className="font-mono text-xs truncate">{h.base_url}</dd>
              <dt className="text-slate-500">Key</dt>
              <dd>{h.api_key_configured ? <span className="text-emerald-600">已配置</span> : <span className="text-red-600">未配置</span>}</dd>
              <dt className="text-slate-500">Group</dt>
              <dd className="font-mono text-xs">{h.group_id_tail ? `…${h.group_id_tail}` : '—'}</dd>
              <dt className="text-slate-500">上游</dt>
              <dd>
                {h.minimax === 'ok' && <span className="text-emerald-600">可达 · {h.model_count} 模型</span>}
                {h.minimax === 'no_key' && <span className="text-amber-600">缺 Key</span>}
                {h.minimax === 'error' && <span className="text-red-600">错（{h.status}）</span>}
              </dd>
            </dl>
          )}
        </div>
      </section>

      {/* 4-layer model status */}
      {stats && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">模型状态</h2>
          <div className="grid grid-cols-4 gap-3">
            <ModelStat label="官方当前" value={stats.officialCurrent} sub="official_current" tone="emerald" />
            <ModelStat label="实际可用" value={stats.liveAvailable} sub="live=true 已验收" tone="indigo" />
            <ModelStat label="本地配置" value={stats.models} sub="含历史兼容" tone="slate" />
            <ModelStat label="历史/隐藏" value={stats.legacyHidden} sub="deprecated/legacy" tone="amber" />
          </div>
        </section>
      )}

      {/* 全量覆盖缺口统计 */}
      {stats && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">全量覆盖缺口</h2>
          <div className="grid grid-cols-6 gap-3">
            <GapStat label="官方当前" value={stats.officialCurrent} sub="official_current=true" tone="emerald" />
            <GapStat label="本地配置" value={stats.localConfigured} sub="含 legacy/deprecated" tone="slate" />
            <GapStat label="live chat" value={stats.liveChatModels} sub="/v1/models 返回" tone="indigo" />
            <GapStat label="待验收" value={stats.capabilityProbePending} sub="capability_probe=unknown" tone="amber" />
            <GapStat label="未 live 验收" value={stats.officialCurrentNonLive} sub="official_current 且 live≠true" tone="orange" />
            <GapStat label="highspeed 档" value={stats.highspeedCount} sub="独立统计" tone="purple" />
          </div>
        </section>
      )}

      {/* 收费与风险统计 */}
      {stats && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">收费与风险能力统计</h2>
          <div className="grid grid-cols-6 gap-3">
            <GapStat label="正常测试" value={stats.normalTokenPlanTest} sub="TokenPlan 正常验收" tone="emerald" />
            <GapStat label="配额敏感" value={stats.quotaSensitive} sub="额度敏感能力" tone="amber" />
            <GapStat label="需确认付费" value={stats.paidConfirmRequired} sub="voice-clone/design" tone="rose" />
            <GapStat label="高成本" value={stats.highCostConfirmRequired} sub="video 类" tone="red" />
            <GapStat label="素材型" value={stats.assetRequiredConfirmRequired} sub="music-cover" tone="orange" />
            <GapStat label="可能额外收费" value={stats.mayChargeExtra} sub="may_charge_extra=true" tone="rose" />
          </div>
        </section>
      )}

      {/* 操作风险统计 */}
      {stats && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">操作风险能力统计</h2>
          <div className="grid grid-cols-7 gap-3">
            <GapStat label="普通操作" value={stats.opNormal} sub="normal" tone="emerald" />
            <GapStat label="破坏性操作" value={stats.opDestructive} sub="file-delete/voice-delete" tone="red" />
            <GapStat label="素材型" value={stats.opAssetRequired} sub="file-upload/图生图等" tone="amber" />
            <GapStat label="仅已有任务" value={stats.opExistingTaskOnly} sub="video-query/download" tone="blue" />
            <GapStat label="长任务" value={stats.opLongRunning} sub="video 生成类" tone="purple" />
            <GapStat label="额度保护" value={stats.opQuotaGuarded} sub="tts-async" tone="orange" />
            <GapStat label="需操作确认" value={stats.opRequiresConfirm} sub="requires_operation_confirm" tone="rose" />
          </div>
        </section>
      )}

      {/* 确认门禁统计 */}
      {stats && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">执行前确认门禁统计</h2>
          <div className="grid grid-cols-8 gap-3">
            <GapStat label="需任意确认" value={stats.requiresAnyConfirm} sub="默认阻断" tone="rose" />
            <GapStat label="付费确认" value={stats.confirmPaid} sub="may_charge_extra" tone="rose" />
            <GapStat label="高成本确认" value={stats.confirmHighCost} sub="high_cost_confirm" tone="red" />
            <GapStat label="破坏性确认" value={stats.confirmDestructive} sub="is_destructive" tone="red" />
            <GapStat label="素材确认" value={stats.confirmAssetSource} sub="requires_uploaded_asset" tone="amber" />
            <GapStat label="长任务确认" value={stats.confirmLongRunning} sub="is_long_running" tone="purple" />
            <GapStat label="已有任务确认" value={stats.confirmExistingTask} sub="requires_existing_task" tone="blue" />
            <GapStat label="配额确认" value={stats.confirmQuota} sub="tts-async" tone="orange" />
          </div>
        </section>
      )}

      {regErr && <div className="mt-6 text-sm text-red-600">无法加载能力图谱：{regErr}</div>}

      {stats && (
        <section className="mt-6 grid grid-cols-5 gap-3 text-center">
          <Stat label="能力总数" value={stats.total} />
          <Stat label="已可用" value={stats.implemented} tone="emerald" />
          <Stat label="即将上线" value={stats.planned} tone="amber" />
          <Stat label="模型数" value={stats.models} tone="indigo" />
          <Stat label="走配额模型" value={stats.quota} tone="emerald" />
        </section>
      )}

      {registry && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold text-slate-900">分类导览</h2>
          <div className="mt-3 grid grid-cols-3 gap-3">
            {registry.categories.map((cat) => {
              const caps = registry.capabilities.filter((c) => c.category === cat.id)
              const ok = caps.filter((c) => c.status === 'implemented').length
              return (
                <Link
                  to={`/category/${cat.id}`}
                  key={cat.id}
                  className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400 transition"
                >
                  <div className="flex items-center gap-2">
                    <span>{cat.emoji}</span>
                    <span className="font-medium">{cat.label}</span>
                    <span className="ml-auto text-xs text-slate-500">
                      {ok}/{caps.length}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{cat.desc}</div>
                </Link>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

function Stat({ label, value, tone = 'slate' }: { label: string; value: number; tone?: string }) {
  const toneCls: Record<string, string> = {
    slate: 'text-slate-900',
    emerald: 'text-emerald-600',
    amber: 'text-amber-600',
    indigo: 'text-indigo-600',
  }
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className={`text-2xl font-semibold ${toneCls[tone]}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{label}</div>
    </div>
  )
}

function ModelStat({ label, value, sub, tone }: { label: string; value: number; sub: string; tone: string }) {
  const toneCls: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 text-center ${toneCls[tone]}`}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs font-medium mt-0.5">{label}</div>
      <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
    </div>
  )
}

function GapStat({ label, value, sub, tone }: { label: string; value: number; sub: string; tone: string }) {
  const toneCls: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
    orange: 'border-orange-200 bg-orange-50 text-orange-700',
    purple: 'border-purple-200 bg-purple-50 text-purple-700',
  }
  return (
    <div className={`rounded-lg border px-3 py-2 text-center ${toneCls[tone]}`}>
      <div className="text-xl font-semibold">{value}</div>
      <div className="text-xs font-medium mt-0.5">{label}</div>
      <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
    </div>
  )
}
