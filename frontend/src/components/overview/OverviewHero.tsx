/**
 * OverviewHero.tsx — Hero section for the workbench homepage.
 */
import { Link } from 'react-router-dom'
import type { HealthResp } from '../../api'

interface Props {
  health: HealthResp | null
  healthErr: string | null
  completionPercent: number
  inScopeCovered: number
  inScopeTotal: number
  directlyTestable: number
  cautionRequired: number
  hasRecentHistory: boolean
}

export default function OverviewHero({
  health,
  healthErr,
  completionPercent,
  inScopeCovered,
  inScopeTotal,
  directlyTestable,
  cautionRequired,
  hasRecentHistory,
}: Props) {
  return (
    <>
      {/* Hero */}
      <section className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-sky-50 p-6">
        <h1 className="text-2xl font-semibold text-slate-900">MiniMax Token Plan 工作台</h1>
        <p className="text-slate-600 mt-1 text-sm">
          能力验收进度 · 风险门禁 · 真实调用和资产结果管理
        </p>
        <div className="flex items-center gap-3 mt-4">
          <Link
            to="/capability-runner"
            className="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-700 transition"
          >
            开始能力体验 ⚡
          </Link>
          <Link
            to="/test-console"
            className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 transition"
          >
            进入高级测试 🧪
          </Link>
          <Link
            to="/capability-scenarios"
            className="px-3 py-2 text-sm text-sky-600 hover:underline"
          >
            查看场景推荐 🎯
          </Link>
          <Link
            to="/capability-workflows"
            className="px-3 py-2 text-sm text-sky-600 hover:underline"
          >
            查看流程体验 🔁
          </Link>
        </div>
      </section>

      {/* Core status cards */}
      <section className="mt-6 grid grid-cols-4 gap-4">
        <StatusCard
          label="Token Plan 验收进度"
          value={`${inScopeCovered}/${inScopeTotal}`}
          sub={`${completionPercent}% 完成`}
          tone="emerald"
        />
        <StatusCard
          label="可直接测试能力"
          value={directlyTestable}
          sub="in_scope + 正常配额"
          tone="sky"
        />
        <StatusCard
          label="需谨慎能力"
          value={cautionRequired}
          sub="高成本/额敏/破坏性"
          tone="amber"
        />
        <StatusCard
          label="最近调用记录"
          value={hasRecentHistory ? '有记录' : '暂无'}
          sub={hasRecentHistory ? '可查看执行历史' : '去能力体验执行一次'}
          tone={hasRecentHistory ? 'indigo' : 'slate'}
        />
      </section>

      {/* Connectivity card */}
      <section className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
        <div className="text-xs text-slate-500 mb-2">连通状态</div>
        {healthErr && <div className="text-sm text-red-600">后端不可达：{healthErr}</div>}
        {health && (
          <div className="flex items-center gap-6 text-xs">
            <span>
              后端：
              <span className="font-mono text-slate-700 ml-1">{health.base_url}</span>
            </span>
            <span>
              Key：
              {health.api_key_configured ? (
                <span className="text-emerald-600 ml-1">已配置</span>
              ) : (
                <span className="text-red-600 ml-1">未配置</span>
              )}
            </span>
            <span>
              Group：
              <span className="font-mono text-slate-700 ml-1">
                {health.group_id_tail ? `…${health.group_id_tail}` : '—'}
              </span>
            </span>
            <span>
              上游：
              {health.minimax === 'ok' && (
                <span className="text-emerald-600 ml-1">可达 · {health.model_count} 模型</span>
              )}
              {health.minimax === 'no_key' && (
                <span className="text-amber-600 ml-1">缺 Key</span>
              )}
              {health.minimax === 'error' && (
                <span className="text-red-600 ml-1">错（{health.status}）</span>
              )}
            </span>
          </div>
        )}
      </section>
    </>
  )
}

function StatusCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string
  value: string | number
  sub: string
  tone: 'emerald' | 'sky' | 'amber' | 'indigo' | 'slate'
}) {
  const toneCls: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    sky: 'border-sky-200 bg-sky-50 text-sky-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-600',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 ${toneCls[tone]}`}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs font-medium mt-0.5">{label}</div>
      <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
    </div>
  )
}
