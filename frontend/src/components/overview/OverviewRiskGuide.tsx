/**
 * OverviewRiskGuide.tsx — Risk explanation card for the workbench homepage.
 */
import { Link } from 'react-router-dom'

export default function OverviewRiskGuide() {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-semibold text-slate-700 mb-3">风险说明</h2>
      <div className="grid grid-cols-5 gap-3">
        <RiskCard
          tone="emerald"
          label="绿色"
          desc="可以低成本测试"
          detail="TokenPlan 正常配额，无额外费用"
        />
        <RiskCard
          tone="amber"
          label="黄色"
          desc="配额敏感能力"
          detail="需要少量测试，确认额度消耗"
        />
        <RiskCard
          tone="red"
          label="红色"
          desc="高成本或额外收费"
          detail="不要随便执行，先确认费用"
        />
        <RiskCard
          tone="purple"
          label="紫色"
          desc="素材型能力"
          detail="需要确认素材来源合法"
        />
        <RiskCard
          tone="slate"
          label="灰色"
          desc="范围外能力"
          detail="当前不做默认验收"
        />
      </div>
      <div className="mt-2 text-xs text-slate-500">
        所有能力执行前都会经过{' '}
        <span className="font-medium text-sky-600">RiskGate 安检</span>
        {' '}确认，风险能力需要额外确认才能执行。
        {' '}详情见<Link to="/test-console" className="text-sky-600 hover:underline">高级测试</Link>。
      </div>
    </section>
  )
}

function RiskCard({
  tone,
  label,
  desc,
  detail,
}: {
  tone: 'emerald' | 'amber' | 'red' | 'purple' | 'slate'
  label: string
  desc: string
  detail: string
}) {
  const toneCls: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    red: 'border-red-200 bg-red-50 text-red-700',
    purple: 'border-purple-200 bg-purple-50 text-purple-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-600',
  }

  return (
    <div className={`rounded-lg border px-3 py-2 ${toneCls[tone]}`}>
      <div className="text-xs font-semibold">{label}</div>
      <div className="text-[11px] font-medium mt-0.5">{desc}</div>
      <div className="text-[10px] opacity-70 mt-0.5 leading-relaxed">{detail}</div>
    </div>
  )
}
