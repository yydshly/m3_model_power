import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProfiles, type CapabilityProfile } from '../api'

const FAMILY_EMOJI: Record<string, string> = {
  chat: '💬',
  voice: '🎙️',
  vision: '🖼️',
  music: '🎵',
  assets: '📁',
  models: '🧠',
}

const TOKEN_PLAN_STATUS_LABEL: Record<string, { text: string; className: string }> = {
  available_direct: { text: '可直接体验', className: 'bg-emerald-100 text-emerald-700' },
  available_guarded: { text: '需确认', className: 'bg-amber-100 text-amber-700' },
  supported_not_default: { text: '不默认执行', className: 'bg-orange-100 text-orange-700' },
  api_only: { text: '仅 API 说明', className: 'bg-slate-100 text-slate-600' },
  unavailable_or_unknown: { text: '不可用/未知', className: 'bg-red-100 text-red-700' },
}

const SOURCE_BADGE: Record<string, { text: string; className: string }> = {
  official_docs: { text: '官方文档', className: 'bg-violet-100 text-violet-700' },
  token_plan_verified: { text: '已验收', className: 'bg-emerald-100 text-emerald-700' },
  local_config: { text: '本地配置', className: 'bg-slate-100 text-slate-600' },
  historical_compat: { text: '历史兼容', className: 'bg-gray-100 text-gray-600' },
  risk_warning: { text: '风险提示', className: 'bg-orange-100 text-orange-700' },
}

const RECOMMENDATION_BADGE: Record<string, { text: string; className: string }> = {
  official_primary: { text: '官方主推', className: 'bg-violet-600 text-white' },
  official_current: { text: '官方当前', className: 'bg-indigo-500 text-white' },
  verified_stable: { text: '已验收稳定', className: 'bg-emerald-600 text-white' },
  low_latency: { text: '低延迟', className: 'bg-cyan-600 text-white' },
  high_quality: { text: '高质量', className: 'bg-blue-600 text-white' },
  quota_friendly: { text: 'Token Plan 高频', className: 'bg-teal-600 text-white' },
  compatible: { text: '兼容', className: 'bg-slate-500 text-white' },
  guarded: { text: '需确认', className: 'bg-amber-500 text-white' },
  free_tier: { text: '免费档', className: 'bg-gray-400 text-white' },
  not_default: { text: '不默认执行', className: 'bg-orange-500 text-white' },
  not_applicable: { text: '不适用', className: 'bg-gray-300 text-gray-700' },
}

const VERIFIED_STATUS_BADGE: Record<string, { text: string; className: string }> = {
  verified_in_this_project: { text: '已验收', className: 'bg-emerald-100 text-emerald-700' },
  not_verified_in_this_project: { text: '未验收', className: 'bg-amber-100 text-amber-700' },
}

function StatusBadge({ value, map }: { value: string; map: Record<string, { text: string; className: string }> }) {
  const entry = map[value] ?? { text: value, className: 'bg-slate-100 text-slate-600' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${entry.className}`}>{entry.text}</span>
}

export default function CapabilityProfilesPage() {
  const [profiles, setProfiles] = useState<Record<string, CapabilityProfile> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getProfiles()
      .then((data) => { setProfiles(data.profiles); setLoading(false) })
      .catch((e) => { setError(String(e)); setLoading(false) })
  }, [])

  if (loading) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  if (error) return <div className="p-8 text-sm text-red-600">加载失败：{error}</div>
  if (!profiles) return <div className="p-8 text-sm text-slate-500">无数据</div>

  const families = Object.keys(profiles)

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">能力画像</h1>
        <p className="text-sm text-slate-600 mt-1">
          从用户视角理解每个能力族能做什么、支持哪些模型、有什么风险、如何使用。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {families.map((family) => {
          const p = profiles[family]
          return (
            <div key={family} className="rounded-xl border border-slate-200 bg-white shadow-sm">
              {/* Header */}
              <div className="px-5 py-4 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{FAMILY_EMOJI[family] ?? '📦'}</span>
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">{p.label}</h2>
                    <p className="text-xs text-slate-500 mt-0.5">{family}</p>
                  </div>
                  <div className="ml-auto flex gap-2">
                    <StatusBadge value={p.token_plan_status} map={TOKEN_PLAN_STATUS_LABEL} />
                  </div>
                </div>
                <p className="text-sm text-slate-600 mt-3">{p.user_summary}</p>
              </div>

              {/* Body */}
              <div className="px-5 py-4 space-y-4">
                {/* Capabilities */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">已验收能力</h3>
                    <div className="space-y-1">
                      {p.verified_capabilities.map((id) => (
                        <div key={id} className="text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                          {id}
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">风险提示</h3>
                    <div className="space-y-1">
                      {p.not_default_executable.map((id) => (
                        <div key={id} className="text-xs text-orange-700 bg-orange-50 px-2 py-0.5 rounded">
                          {id} 不默认执行
                        </div>
                      ))}
                      {p.guarded_capabilities.map((id) => (
                        <div key={id} className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
                          {id} 需确认
                        </div>
                      ))}
                      {p.not_default_executable.length === 0 && p.guarded_capabilities.length === 0 && (
                        <div className="text-xs text-slate-400">无特殊风险</div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Models */}
                {p.model_notes.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-2">模型与推荐依据</h3>
                    <div className="space-y-3">
                      {p.model_notes.map((m) => (
                        <div key={m.model} className="bg-slate-50 rounded-lg px-3 py-2.5">
                          {/* model + label */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-slate-800 font-semibold text-sm">{m.model}</span>
                            <span className="text-slate-600 text-sm">{m.label}</span>
                          </div>
                          {/* badges row */}
                          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                            <StatusBadge value={m.source} map={SOURCE_BADGE} />
                            <StatusBadge value={m.recommendation_level} map={RECOMMENDATION_BADGE} />
                            {m.verified_status && (
                              <StatusBadge value={m.verified_status} map={VERIFIED_STATUS_BADGE} />
                            )}
                          </div>
                          {/* best_for */}
                          {m.best_for && m.best_for.length > 0 && (
                            <div className="mt-2">
                              <span className="text-[10px] text-emerald-600 font-medium">适合：</span>
                              <span className="text-[10px] text-slate-600">
                                {m.best_for.join(' / ')}
                              </span>
                            </div>
                          )}
                          {/* not_best_for */}
                          {m.not_best_for && m.not_best_for.length > 0 && (
                            <div className="mt-0.5">
                              <span className="text-[10px] text-orange-600 font-medium">不适合：</span>
                              <span className="text-[10px] text-slate-500">
                                {m.not_best_for.join(' / ')}
                              </span>
                            </div>
                          )}
                          {/* notes */}
                          {m.notes && (
                            <div className="mt-1 text-[10px] text-slate-400 italic">{m.notes}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Parameters */}
                {p.key_parameters.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">关键参数</h3>
                    <div className="flex flex-wrap gap-1">
                      {p.key_parameters.map((param) => (
                        <span key={param.name} className="text-[10px] bg-sky-50 text-sky-700 px-1.5 py-0.5 rounded">
                          {param.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Outputs */}
                {p.outputs.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">输出类型</h3>
                    <div className="flex flex-wrap gap-1">
                      {p.outputs.map((o) => (
                        <span key={o} className="text-[10px] bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded">{o}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Risk Notes */}
                {p.risk_notes.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">风险说明</h3>
                    <ul className="space-y-0.5">
                      {p.risk_notes.map((note, i) => (
                        <li key={i} className="text-xs text-amber-700">⚠️ {note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Product Usage */}
                {p.product_usage.length > 0 && (
                  <div>
                    <h3 className="text-xs font-medium text-slate-500 mb-1.5">产品用途</h3>
                    <ul className="space-y-0.5">
                      {p.product_usage.map((u, i) => (
                        <li key={i} className="text-xs text-slate-600">• {u}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Recommended workflows */}
                {p.recommended_workflows.length > 0 && (
                  <div className="flex gap-2 items-center pt-1">
                    <span className="text-xs text-slate-500">推荐流程:</span>
                    {p.recommended_workflows.map((wf) => (
                      <Link
                        key={wf}
                        to={`/capability-workflows?workflow=${wf}`}
                        className="text-xs text-sky-600 hover:underline bg-sky-50 px-2 py-0.5 rounded"
                      >
                        {wf}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
