/**
 * OverviewRecentHistory.tsx — Recent invocation overview for the homepage.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getTestConsoleHistory, type TestConsoleHistoryItem } from '../../api'

export default function OverviewRecentHistory() {
  const [items, setItems] = useState<TestConsoleHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    getTestConsoleHistory(5)
      .then((r) => { setItems(r.items); setLoading(false) })
      .catch((e) => { setErr(String(e)); setLoading(false) })
  }, [])

  return (
    <section className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-700">最近调用</h2>
        <Link
          to="/test-console"
          className="text-xs text-sky-600 hover:underline"
        >
          查看全部高级测试历史 →
        </Link>
      </div>

      {loading && (
        <div className="text-xs text-slate-400">加载中…</div>
      )}
      {err && (
        <div className="text-xs text-slate-400">暂时无法加载历史记录</div>
      )}
      {!loading && !err && items.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center">
          <p className="text-sm text-slate-500">还没有调用记录</p>
          <p className="text-xs text-slate-400 mt-1">
            去<Link to="/capability-runner" className="text-sky-600 hover:underline mx-1">能力体验</Link>
            执行一次
          </p>
        </div>
      )}
      {!loading && !err && items.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white divide-y divide-slate-100">
          {items.map((item) => (
            <HistoryRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  )
}

function HistoryRow({ item }: { item: TestConsoleHistoryItem }) {
  const time = new Date(item.created_at).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  const ok = item.result?.ok ?? item.result?.allowed ?? false
  const statusColor = ok ? 'text-emerald-600' : 'text-red-600'
  const statusText = item.action === 'risk_check' ? '安检' : '调用'
  const actionColor = item.action === 'risk_check' ? 'bg-amber-100 text-amber-700' : 'bg-sky-100 text-sky-700'

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 text-xs">
      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${actionColor}`}>
        {statusText}
      </span>
      <span className="font-medium text-slate-700 w-28 truncate">{item.capability_id}</span>
      <span className={`font-medium ${statusColor}`}>
        {ok ? '成功' : '失败'}
      </span>
      {item.duration_ms != null && (
        <span className="text-slate-400">{item.duration_ms}ms</span>
      )}
      {item.result_summary?.asset_count != null && item.result_summary.asset_count > 0 && (
        <span className="text-slate-400">含资产结果 {item.result_summary.asset_count}</span>
      )}
      {item.result_summary?.text_preview && (
        <span className="text-slate-400 truncate flex-1">
          {item.result_summary.text_preview}
        </span>
      )}
      <span className="text-slate-400 ml-auto shrink-0">{time}</span>
    </div>
  )
}
