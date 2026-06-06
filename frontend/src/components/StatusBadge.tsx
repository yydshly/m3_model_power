import type { CapabilityStatus } from '../api'

const STYLES: Record<CapabilityStatus, { label: string; cls: string }> = {
  implemented: { label: '可用', cls: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  planned: { label: '即将上线', cls: 'bg-amber-100 text-amber-700 border-amber-200' },
  unsupported: { label: '当前档位不支持', cls: 'bg-slate-200 text-slate-600 border-slate-300' },
}

export function StatusBadge({ status }: { status: CapabilityStatus }) {
  const s = STYLES[status]
  return <span className={`inline-block px-2 py-0.5 text-xs rounded border ${s.cls}`}>{s.label}</span>
}

export function TierBadge({ tier }: { tier: 'flagship' | 'highspeed' | 'standard' | 'legacy' }) {
  const map = {
    flagship: { label: '旗舰', cls: 'bg-indigo-100 text-indigo-700' },
    highspeed: { label: '极速档', cls: 'bg-emerald-100 text-emerald-700' },
    standard: { label: '标准', cls: 'bg-sky-100 text-sky-700' },
    legacy: { label: '旧版', cls: 'bg-slate-100 text-slate-600' },
  }
  const s = map[tier]
  return <span className={`inline-block px-1.5 py-0.5 text-[10px] rounded ${s.cls}`}>{s.label}</span>
}

export function QuotaBadge({ eligible }: { eligible: boolean }) {
  return (
    <span
      className={`inline-block px-1.5 py-0.5 text-[10px] rounded ${
        eligible ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
      }`}
      title={eligible ? '走 TokenPlanPlus 共享配额' : '按 token 单独计费，不走极速档配额'}
    >
      {eligible ? '走配额' : '另计费'}
    </span>
  )
}
