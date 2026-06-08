/**
 * InvocationHistoryPanel — reusable component for displaying invocation history.
 *
 * Used by TestConsole, CapabilityRunner, and Capability pages.
 * Shows: capability_id, action type, status, duration_ms, asset count.
 * Expanded view: payload preview, confirmations, result_summary, warnings.
 * Debug info (blocked_reasons, required_confirmations, raw JSON) is always
 * wrapped in a collapsible "调试信息" section — never shown in the main UI.
 */
import type { TestConsoleHistoryItem } from '../api'
import HistoryAssetPreview from './HistoryAssetPreview'

type Props = {
  items: TestConsoleHistoryItem[]
  expandedId: string | null
  onToggleExpand: (id: string | null) => void
  filterAction?: 'all' | 'risk_check' | 'invoke' | 'stream' | 'upload' | 'ws'
  onFilterChange?: (v: 'all' | 'risk_check' | 'invoke' | 'stream' | 'upload' | 'ws') => void
  filterHasAssets?: boolean
  onFilterHasAssetsChange?: (v: boolean) => void
  emptyMessage?: string
  /** Show a capability label above each item (for per-capability history views) */
  showCapabilityHeader?: boolean
}

const ACTION_LABELS: Record<string, string> = {
  risk_check: '安检',
  invoke: '调用',
  stream: '流式',
  upload: '上传',
  ws: 'WebSocket',
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTime(iso: string): { date: string; time: string } {
  try {
    const d = new Date(iso)
    return {
      date: d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }),
      time: d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }
  } catch {
    return { date: '', time: '' }
  }
}

export default function InvocationHistoryPanel({
  items,
  expandedId,
  onToggleExpand,
  filterAction = 'all',
  onFilterChange,
  filterHasAssets = false,
  onFilterHasAssetsChange,
  emptyMessage,
  showCapabilityHeader = false,
}: Props) {
  const filtered = items.filter((item) => {
    if (filterAction !== 'all' && item.action !== filterAction) return false
    if (filterHasAssets && !item.result_summary?.asset_count) return false
    return true
  })

  if (filtered.length === 0) {
    return (
      <div className="text-xs text-slate-500 space-y-1">
        <p className="text-sm text-slate-400">{emptyMessage ?? '暂无调用记录'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {(onFilterChange || onFilterHasAssetsChange) && (
        <div className="flex items-center gap-3 flex-wrap mb-2">
          {onFilterChange && (
            <select
              value={filterAction}
              onChange={(e) => onFilterChange(e.target.value as typeof filterAction)}
              className="border border-slate-300 rounded px-2 py-1 text-xs"
            >
              <option value="all">全部动作</option>
              <option value="risk_check">安全检查</option>
              <option value="invoke">调用</option>
              <option value="stream">流式</option>
              <option value="upload">上传</option>
              <option value="ws">WebSocket</option>
            </select>
          )}
          {onFilterHasAssetsChange && (
            <label className="flex items-center gap-1 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={filterHasAssets}
                onChange={(e) => onFilterHasAssetsChange(e.target.checked)}
                className="rounded"
              />
              有资产
            </label>
          )}
        </div>
      )}

      {filtered.map((item) => {
        const ok = item.result?.ok ?? item.result?.allowed ?? false
        const { date, time } = formatTime(item.created_at)
        const isExpanded = expandedId === item.id

        return (
          <div key={item.id} className="border border-slate-100 rounded-lg bg-white overflow-hidden">
            {/* Summary row — always visible */}
            <button
              className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-slate-50 text-left"
              onClick={() => onToggleExpand(isExpanded ? null : item.id)}
            >
              <span className="text-slate-400 shrink-0 w-14">{date}</span>
              <span className="text-slate-400 shrink-0 w-16">{time}</span>
              <span
                className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-medium ${
                  item.action === 'risk_check'
                    ? 'bg-sky-100 text-sky-700'
                    : item.action === 'stream'
                    ? 'bg-cyan-100 text-cyan-700'
                    : item.action === 'upload'
                    ? 'bg-rose-100 text-rose-700'
                    : item.action === 'ws'
                    ? 'bg-violet-100 text-violet-700'
                    : 'bg-indigo-100 text-indigo-700'
                }`}
              >
                {ACTION_LABELS[item.action] ?? item.action}
              </span>
              {showCapabilityHeader && (
                <>
                  {item.capability_id === 'history-smoke-test' ? (
                    <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-slate-200 text-slate-500">
                      测试记录
                    </span>
                  ) : (
                    <span className="font-mono text-slate-700">{item.capability_id}</span>
                  )}
                </>
              )}
              {item.result_summary?.output_type && item.result_summary.output_type !== 'unknown' && (
                <span className="shrink-0 px-1 py-0.5 rounded bg-violet-100 text-violet-700 text-[10px]">
                  {item.result_summary.output_type}
                </span>
              )}
              {item.result_summary?.asset_count ? (
                <span className="shrink-0 text-[10px] text-slate-400">
                  {item.result_summary.asset_count} asset{item.result_summary.asset_count !== 1 ? 's' : ''}
                </span>
              ) : null}
              {item.duration_ms != null && (
                <span className="shrink-0 text-[10px] text-slate-400">{formatDuration(item.duration_ms)}</span>
              )}
              <span className={`ml-auto shrink-0 ${ok ? 'text-green-600' : 'text-red-600'}`}>
                {ok ? '✓' : '✗'}
              </span>
              <span className="shrink-0 text-slate-300">{isExpanded ? '▲' : '▼'}</span>
            </button>

            {/* Expanded details */}
            {isExpanded && (
              <div className="px-4 pb-3 pt-1 border-t border-slate-100 space-y-3 text-xs">
                {/* Status row */}
                {!ok && item.result?.error && (
                  <div className="bg-red-50 border border-red-200 rounded p-2 text-red-700">
                    <strong>错误：</strong>{item.result.error}
                  </div>
                )}

                {/* Debug section — collapsed by default, shows raw/internal details */}
                <details className="border border-slate-200 rounded">
                  <summary className="px-2 py-1.5 cursor-pointer text-slate-500 hover:text-slate-700 text-[10px]">
                    调试信息
                  </summary>
                  <div className="px-2 pb-2 space-y-2">
                    {/* Blocked reasons — only in debug */}
                    {!ok && item.result?.blocked_reasons?.length ? (
                      <div className="text-red-600">
                        <span className="font-medium">阻断原因：</span>
                        {item.result.blocked_reasons.join('；')}
                      </div>
                    ) : null}

                    {/* Required confirmations — only in debug */}
                    {!ok && item.result?.required_confirmations?.length ? (
                      <div className="text-orange-600">
                        <span className="font-medium">需要确认：</span>
                        {item.result.required_confirmations.join('、')}
                      </div>
                    ) : null}

                    {/* Payload preview */}
                    <div>
                      <p className="font-medium text-slate-600 mb-0.5">Payload</p>
                      <div className="bg-slate-100 rounded p-2 space-y-1">
                        <div>keys: {item.payload_summary.payload_keys.join(', ') || '(无)'}</div>
                        {item.payload_summary.payload_preview && (
                          <div className="text-slate-600 font-mono whitespace-pre-wrap break-all">
                            {item.payload_summary.payload_preview}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Confirmations */}
                    {item.confirmations && Object.keys(item.confirmations).length > 0 && (
                      <div>
                        <p className="font-medium text-slate-600 mb-0.5">确认项</p>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(item.confirmations).map(([k, v]) => (
                            <span
                              key={k}
                              className={`px-1.5 py-0.5 rounded text-[10px] ${
                                v ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                              }`}
                            >
                              {k}: {String(v)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Warnings — only in debug */}
                    {item.result?.warnings?.length ? (
                      <div className="text-yellow-600">
                        warnings: {item.result.warnings.join('；')}
                      </div>
                    ) : null}
                  </div>
                </details>

                {/* Result summary — shown outside debug for quick visibility */}
                {item.result_summary && (
                  <div>
                    <p className="font-medium text-slate-700 mb-1">结果摘要</p>
                    <div className="bg-slate-50 rounded p-2">
                      {item.result_summary.output_type && (
                        <div className="mb-1">
                          类型: <span className="text-slate-700">{item.result_summary.output_type}</span>
                        </div>
                      )}
                      {item.result_summary.text_preview && (
                        <div className="mb-1 text-slate-600 italic truncate">
                          文本：{item.result_summary.text_preview}
                        </div>
                      )}
                      {item.result_summary.usage && (
                        <div className="mt-1 text-xs text-slate-500">
                          Token：
                          {item.result_summary.usage.input_tokens != null && (
                            <span>输入 {item.result_summary.usage.input_tokens}</span>
                          )}
                          {item.result_summary.usage.output_tokens != null && (
                            <span className="ml-2">输出 {item.result_summary.usage.output_tokens}</span>
                          )}
                          {item.result_summary.usage.total_tokens != null && (
                            <span className="ml-2">总计 {item.result_summary.usage.total_tokens}</span>
                          )}
                        </div>
                      )}
                      <HistoryAssetPreview
                        result_summary={item.result_summary}
                        rawResult={item.result ?? undefined}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
