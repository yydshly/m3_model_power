import type { Capability } from '../api'

const STYLE = {
  none: { label: '免费', cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  quota: { label: '走配额', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  low: { label: '少量计费', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  medium: { label: '单独计费', cls: 'bg-orange-50 text-orange-700 border-orange-200' },
  high: { label: '高费用 ⚠', cls: 'bg-rose-50 text-rose-700 border-rose-200' },
} as const

export function CostBadge({ level }: { level: Capability['cost_level'] }) {
  const s = STYLE[level]
  return <span className={`inline-block px-2 py-0.5 text-xs rounded border ${s.cls}`}>{s.label}</span>
}

export function CostNotice({ cap }: { cap: Capability }) {
  if (cap.cost_level === 'none' || cap.cost_level === 'quota') return null
  return (
    <div className="rounded border border-rose-200 bg-rose-50 text-rose-800 text-sm p-3 mb-4">
      <div className="font-medium flex items-center gap-2">
        <span>💸</span>
        <span>
          费用提示 · {STYLE[cap.cost_level].label}
        </span>
      </div>
      {cap.cost_note && <div className="mt-1 text-xs text-rose-700">{cap.cost_note}</div>}
    </div>
  )
}
