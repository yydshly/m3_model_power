import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CostBadge } from '../components/CostBadge'
import { StatusBadge } from '../components/StatusBadge'
import { useRegistry } from '../store'
import type { ScopeLevel } from '../api'
import { MODULE_DESCRIPTIONS } from '../workbenchStatus'

type FilterScope = 'all' | ScopeLevel

export default function Category() {
  const { id } = useParams<{ id: string }>()
  const { registry } = useRegistry()
  const [filterScope, setFilterScope] = useState<FilterScope>('all')
  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  const cat = registry.categories.find((c) => c.id === id)
  if (!cat) return <div className="p-8 text-sm text-red-600">分类不存在：{id}</div>
  const allCaps = registry.capabilities.filter((c) => c.category === id)
  const caps = filterScope === 'all' ? allCaps : allCaps.filter((c) => c.scope_policy?.current_scope === filterScope)

  const inScopeCount = allCaps.filter((c) => c.scope_policy?.current_scope === 'in_scope').length
  const warningCount = allCaps.filter((c) => c.scope_policy?.current_scope === 'warning_only').length
  const outCount = allCaps.filter((c) => c.scope_policy?.current_scope === 'out_of_scope').length
  const moduleInfo = MODULE_DESCRIPTIONS[id ?? '']

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center gap-2 text-2xl font-semibold text-slate-900">
        <span>{cat.emoji}</span>
        <span>{cat.label}</span>
      </div>
      <p className="text-sm text-slate-600 mt-1">{cat.desc}</p>

      {/* Scope filter */}
      <div className="mt-4 flex items-center gap-2 flex-wrap text-xs">
        <span className="text-slate-500">范围筛选：</span>
        <button
          className={`px-2 py-1 rounded border ${filterScope === 'all' ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}
          onClick={() => setFilterScope('all')}
        >
          全部 ({allCaps.length})
        </button>
        <button
          className={`px-2 py-1 rounded border ${filterScope === 'in_scope' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}
          onClick={() => setFilterScope('in_scope')}
        >
          范围内 ({inScopeCount})
        </button>
        <button
          className={`px-2 py-1 rounded border ${filterScope === 'warning_only' ? 'bg-amber-600 text-white border-amber-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}
          onClick={() => setFilterScope('warning_only')}
        >
          只提示 ({warningCount})
        </button>
        <button
          className={`px-2 py-1 rounded border ${filterScope === 'out_of_scope' ? 'bg-slate-600 text-white border-slate-600' : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'}`}
          onClick={() => setFilterScope('out_of_scope')}
        >
          范围外 ({outCount})
        </button>
      </div>

      {/* Module-specific guidance */}
      {moduleInfo && (
        <div className="mt-4 p-4 rounded-lg border border-slate-200 bg-slate-50 space-y-2">
          {moduleInfo.description && (
            <p className="text-xs text-slate-600">{moduleInfo.description}</p>
          )}
          {moduleInfo.recommendations.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-slate-500 mb-1">推荐入口</p>
              <ul className="space-y-0.5">
                {moduleInfo.recommendations.map((r) => (
                  <li key={r} className="text-xs text-slate-600 flex gap-1">
                    <span className="text-emerald-500">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {moduleInfo.riskNotes.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-red-500 mb-1">风险提示</p>
              <ul className="space-y-0.5">
                {moduleInfo.riskNotes.map((r) => (
                  <li key={r} className="text-[10px] text-amber-600 flex gap-1">
                    <span>⚠️</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {moduleInfo.nextSteps.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-slate-500 mb-1">下一步</p>
              <ul className="space-y-0.5">
                {moduleInfo.nextSteps.map((s) => (
                  <li key={s} className="text-[10px] text-slate-500 flex gap-1">
                    <span className="text-sky-500">→</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <ul className="mt-4 space-y-2">
        {caps.map((c) => (
          <li key={c.id} className="rounded-lg border border-slate-200 bg-white hover:border-slate-400 transition">
            <Link to={`/cap/${c.id}`} className="block px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="font-medium text-slate-900">{c.label}</div>
                <StatusBadge status={c.status} />
                <CostBadge level={c.cost_level} />
                {c.scope_policy?.current_scope === 'in_scope' && <span className="text-[10px] px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded">范围内</span>}
                {c.scope_policy?.current_scope === 'warning_only' && <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">只提示</span>}
                {c.scope_policy?.current_scope === 'out_of_scope' && <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">范围外</span>}
                <span className="text-[10px] font-mono text-slate-500">{c.method} {c.mm_path}</span>
                {c.streaming && <span className="text-[10px] text-sky-600">流式</span>}
                {c.async_job && <span className="text-[10px] text-purple-600">异步任务</span>}
                <span className="ml-auto text-slate-400 text-xs">→</span>
              </div>
              <div className="text-xs text-slate-500 mt-1">{c.desc}</div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
