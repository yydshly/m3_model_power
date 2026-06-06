import { Link, useParams } from 'react-router-dom'
import { CostBadge } from '../components/CostBadge'
import { StatusBadge } from '../components/StatusBadge'
import { useRegistry } from '../store'

export default function Category() {
  const { id } = useParams<{ id: string }>()
  const { registry } = useRegistry()
  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  const cat = registry.categories.find((c) => c.id === id)
  if (!cat) return <div className="p-8 text-sm text-red-600">分类不存在：{id}</div>
  const caps = registry.capabilities.filter((c) => c.category === id)

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center gap-2 text-2xl font-semibold text-slate-900">
        <span>{cat.emoji}</span>
        <span>{cat.label}</span>
      </div>
      <p className="text-sm text-slate-600 mt-1">{cat.desc}</p>

      <ul className="mt-6 space-y-2">
        {caps.map((c) => (
          <li key={c.id} className="rounded-lg border border-slate-200 bg-white hover:border-slate-400 transition">
            <Link to={`/cap/${c.id}`} className="block px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="font-medium text-slate-900">{c.label}</div>
                <StatusBadge status={c.status} />
                <CostBadge level={c.cost_level} />
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
