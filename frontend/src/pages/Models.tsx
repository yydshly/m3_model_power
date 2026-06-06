import { useState } from 'react'
import { TierBadge, QuotaBadge } from '../components/StatusBadge'
import { type Model } from '../api'
import { useRegistry } from '../store'

/** 模型清单总览，分组展示官方当前模型 / 历史兼容模型，并提供全量模式。 */
export default function ModelsPage() {
  const { registry } = useRegistry()
  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>

  const [fullMode, setFullMode] = useState(true)
  const [filters, setFilters] = useState({
    official_current: false,
    live_available: false,
    not_verified: false,
    legacy_deprecated: false,
    capability_probe_pending: false,
  })

  function toggleFilter(key: keyof typeof filters) {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  // All models
  const allModels = registry.models

  // Apply filters when in filtered mode
  const filteredModels = allModels.filter((m) => {
    if (!fullMode) return false
    if (filters.official_current && !m.official_current) return false
    if (filters.live_available && m.live_available !== true) return false
    if (filters.not_verified && (m.discovery_status === 'available' || m.official_current && m.live_available)) return false
    if (filters.legacy_deprecated && m.tier !== 'legacy' && m.tier !== 'deprecated') return false
    if (filters.capability_probe_pending && (m.discovery_method !== 'capability_probe' || m.discovery_status !== 'unknown')) return false
    return true
  })

  const currentModels = registry.models.filter((m) => m.enabled && m.official_current)
  const legacyModels = registry.models.filter((m) => m.enabled && !m.official_current)

  const byFamily = (models: Model[]) =>
    models.reduce<Record<string, Model[]>>((acc, m) => {
      ;(acc[m.family] = acc[m.family] ?? []).push(m)
      return acc
    }, {})

  const currentByFamily = byFamily(currentModels)
  const legacyByFamily = byFamily(legacyModels)

  const FAMILY_LABEL: Record<string, string> = {
    chat: '对话 / LLM',
    speech: '语音合成',
    image: '图像',
    video: '视频',
    music: '音乐',
  }

  function DiscoveryBadge({ m }: { m: Model }) {
    const method = m.discovery_method
    const status = m.discovery_status
    if (method === 'models_api' && status === 'available') {
      return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 text-emerald-700">models_api ✓</span>
    }
    if (method === 'capability_probe') {
      if (status === 'available') return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-indigo-100 text-indigo-700">capability_probe ✓</span>
      if (status === 'unknown') return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-amber-100 text-amber-700">capability_probe 待验收</span>
      if (status === 'unavailable') return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-red-100 text-red-700">capability_probe ✗</span>
    }
    if (method === 'manual_official') {
      return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-slate-100 text-slate-600">官方文档</span>
    }
    return <span className="inline-block px-1.5 py-0.5 text-[10px] rounded bg-slate-100 text-slate-400">—</span>
  }

  function ModelRow({ m }: { m: Model }) {
    return (
      <tr key={m.id} className="border-t border-slate-100">
        <td className="px-3 py-2 font-mono text-xs">{m.id}</td>
        <td className="px-3 py-2 text-sm">{m.label}</td>
        <td className="px-3 py-2"><TierBadge tier={m.tier} /></td>
        <td className="px-3 py-2"><QuotaBadge eligible={m.quota_eligible} /></td>
        <td className="px-3 py-2 text-xs text-slate-600">
          {m.context && <span className="mr-1">{(m.context / 1000).toFixed(0)}k</span>}
          {m.input_modalities?.map((mod) => (
            <span key={mod} className="inline-block px-1 mr-1 bg-indigo-50 text-indigo-600 rounded text-[10px]">{mod}</span>
          ))}
        </td>
        <td className="px-3 py-2 text-xs text-slate-500">
          {m.protocols?.map((p) => (
            <span key={p} className="inline-block px-1 mr-1 bg-slate-100 rounded text-[10px]">{p}</span>
          ))}
        </td>
        <td className="px-3 py-2"><DiscoveryBadge m={m} /></td>
        <td className="px-3 py-2 text-xs text-slate-500 max-w-[200px] truncate" title={m.note}>{m.note}</td>
      </tr>
    )
  }

  function FamilySection({ family, models }: { family: string; models: Model[] }) {
    const label = FAMILY_LABEL[family] ?? family
    return (
      <section key={family} className="mt-6">
        <h2 className="text-base font-semibold text-slate-800 mb-2">{label}</h2>
        <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>
                <th className="text-left px-3 py-2">ID</th>
                <th className="text-left px-3 py-2">名称</th>
                <th className="text-left px-3 py-2">档位</th>
                <th className="text-left px-3 py-2">计费</th>
                <th className="text-left px-3 py-2">上下文/模态</th>
                <th className="text-left px-3 py-2">协议</th>
                <th className="text-left px-3 py-2">验证方式</th>
                <th className="text-left px-3 py-2">说明</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <ModelRow key={m.id} m={m} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    )
  }

  const stats = {
    total: registry.models.filter((m) => m.enabled).length,
    modelsApiAvailable: registry.models.filter((m) => m.discovery_method === 'models_api' && m.discovery_status === 'available').length,
    capabilityProbeAvailable: registry.models.filter((m) => m.discovery_method === 'capability_probe' && m.discovery_status === 'available').length,
    capabilityProbePending: registry.models.filter((m) => m.discovery_method === 'capability_probe' && m.discovery_status === 'unknown').length,
    manualOfficial: registry.models.filter((m) => m.discovery_method === 'manual_official').length,
    officialCurrent: registry.models.filter((m) => m.official_current).length,
    liveChat: registry.models.filter((m) => m.family === 'chat' && m.live_available === true).length,
    highspeedModels: registry.models.filter((m) => m.tier === 'highspeed').length,
  }

  function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
    return (
      <button
        onClick={onClick}
        className={`px-3 py-1 rounded-full text-xs font-medium border transition ${
          active
            ? 'bg-indigo-600 text-white border-indigo-600'
            : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'
        }`}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-semibold text-slate-900">模型清单</h1>
      <p className="text-sm text-slate-600 mt-1">
        配置来源 <code className="font-mono">backend/config/models.yaml</code>。
        discovery_method / discovery_status 说明验证方式与结果。
      </p>

      {/* 验证方式统计 */}
      <section className="mt-4 grid grid-cols-5 gap-3">
        <StatBox label="models_api 已验证" value={stats.modelsApiAvailable} tone="emerald" sub="通过 /v1/models 确认" />
        <StatBox label="capability_probe 可用" value={stats.capabilityProbeAvailable} tone="indigo" sub="能力端点实测可用" />
        <StatBox label="capability_probe 待验收" value={stats.capabilityProbePending} tone="amber" sub="需通过能力端点验证" />
        <StatBox label="官方文档" value={stats.manualOfficial} tone="slate" sub="仅官方文档列出" />
        <StatBox label="总计" value={stats.total} tone="slate" sub="含历史兼容" />
      </section>

      {/* 关键指标 */}
      <section className="mt-4 grid grid-cols-4 gap-3">
        <StatBox label="官方当前" value={stats.officialCurrent} tone="emerald" sub="official_current=true" />
        <StatBox label="live 可用 chat" value={stats.liveChat} tone="indigo" sub="live_available=true" />
        <StatBox label="极速档(highspeed)" value={stats.highspeedModels} tone="purple" sub="MiniMax-M2.7-highspeed 等" />
        <StatBox label="全量配置" value={stats.total} tone="slate" sub="含 legacy/deprecated" />
      </section>

      {/* 全量模式切换 */}
      <section className="mt-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setFullMode((v) => !v)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              fullMode
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {fullMode ? '✓ 全量模式已开启' : '开启全量模式'}
          </button>
          <span className="text-xs text-slate-500">
            全量模式展示所有模型，支持筛选；逐项列出，无聚合替代。
          </span>
        </div>

        {fullMode && (
          <>
            {/* 筛选器 */}
            <div className="mt-3 flex flex-wrap gap-2">
              <FilterChip
                label="official_current"
                active={filters.official_current}
                onClick={() => toggleFilter('official_current')}
              />
              <FilterChip
                label="live_available"
                active={filters.live_available}
                onClick={() => toggleFilter('live_available')}
              />
              <FilterChip
                label="not_verified"
                active={filters.not_verified}
                onClick={() => toggleFilter('not_verified')}
              />
              <FilterChip
                label="legacy/deprecated"
                active={filters.legacy_deprecated}
                onClick={() => toggleFilter('legacy_deprecated')}
              />
              <FilterChip
                label="capability_probe_pending"
                active={filters.capability_probe_pending}
                onClick={() => toggleFilter('capability_probe_pending')}
              />
              <span className="text-xs text-slate-500 self-center ml-2">
                筛选结果：{filteredModels.length} 个模型
              </span>
            </div>

            {/* 全量模型表 */}
            <div className="mt-4 rounded-lg border border-slate-200 bg-white overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-xs text-slate-500">
                  <tr>
                    <th className="text-left px-3 py-2">ID</th>
                    <th className="text-left px-3 py-2">名称</th>
                    <th className="text-left px-3 py-2">family</th>
                    <th className="text-left px-3 py-2">tier</th>
                    <th className="text-left px-3 py-2">official_current</th>
                    <th className="text-left px-3 py-2">live</th>
                    <th className="text-left px-3 py-2">context</th>
                    <th className="text-left px-3 py-2">input</th>
                    <th className="text-left px-3 py-2">protocols</th>
                    <th className="text-left px-3 py-2">验证方式</th>
                    <th className="text-left px-3 py-2">说明</th>
                  </tr>
                </thead>
                <tbody>
                  {(filters.official_current || filters.live_available || filters.not_verified || filters.legacy_deprecated || filters.capability_probe_pending
                    ? filteredModels
                    : allModels).map((m) => {
                    const live = m.live_available
                    const liveStr = live === true ? '✓' : live === false ? '✗' : '—'
                    const officialStr = m.official_current ? '✓' : '✗'
                    const ctx = m.context ? `${(m.context / 1000).toFixed(0)}k` : '—'
                    const inputMods = m.input_modalities?.join(',') || '—'
                    const protocols = m.protocols?.join(',') || '—'
                    return (
                      <tr key={m.id} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-mono text-xs">{m.id}</td>
                        <td className="px-3 py-2 text-sm">{m.label}</td>
                        <td className="px-3 py-2 text-xs text-slate-500">{m.family}</td>
                        <td className="px-3 py-2"><TierBadge tier={m.tier} /></td>
                        <td className="px-3 py-2 text-center">
                          <span className={officialStr === '✓' ? 'text-emerald-600' : 'text-slate-400'}>{officialStr}</span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className={liveStr === '✓' ? 'text-emerald-600' : liveStr === '✗' ? 'text-red-600' : 'text-slate-400'}>{liveStr}</span>
                        </td>
                        <td className="px-3 py-2 text-xs text-slate-600">{ctx}</td>
                        <td className="px-3 py-2 text-xs text-slate-500">{inputMods}</td>
                        <td className="px-3 py-2 text-xs text-slate-500">{protocols}</td>
                        <td className="px-3 py-2"><DiscoveryBadge m={m} /></td>
                        <td className="px-3 py-2 text-xs text-slate-500 max-w-[160px] truncate" title={m.note}>{m.note}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {/* 官方当前模型 */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
          官方当前模型
        </h2>
        <p className="text-xs text-slate-500 mt-1">official_current: true，官方文档中列出的当前可用模型。</p>
        {Object.entries(currentByFamily).map(([fam, ms]) => (
          <FamilySection key={fam} family={fam} models={ms} />
        ))}
      </section>

      {/* 历史兼容模型 */}
      {legacyModels.length > 0 && (
        <section className="mt-8">
          <details className="group">
            <summary className="cursor-pointer text-lg font-semibold text-slate-900 flex items-center gap-2 list-none">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
              历史兼容模型
              <span className="text-xs text-slate-500 font-normal group-open:hidden">
                （点击展开 {legacyModels.length} 个）▲
              </span>
              <span className="text-xs text-slate-500 font-normal hidden group-open:block">▼</span>
            </summary>
            <p className="text-xs text-slate-500 mt-1 mb-2">official_current: false 或 tier 为 legacy/deprecated，默认隐藏。</p>
            {Object.entries(legacyByFamily).map(([fam, ms]) => (
              <FamilySection key={fam} family={fam} models={ms} />
            ))}
          </details>
        </section>
      )}
    </div>
  )
}

function StatBox({ label, value, tone, sub }: { label: string; value: number; tone: string; sub: string }) {
  const toneCls: Record<string, string> = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    indigo: 'border-indigo-200 bg-indigo-50 text-indigo-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
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
