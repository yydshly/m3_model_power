import { TierBadge, QuotaBadge } from '../components/StatusBadge'
import { type Model } from '../api'
import { useRegistry } from '../store'

/** 模型清单总览，分组展示官方当前模型 / 历史兼容模型。 */
export default function ModelsPage() {
  const { registry } = useRegistry()
  if (!registry) return <div className="p-8 text-sm text-slate-500">加载中…</div>

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

  function ModelRow({ m }: { m: Model }) {
    const liveLabel =
      m.live_available === true ? (
        <span className="text-emerald-600">✓ 已验收</span>
      ) : m.live_available === false ? (
        <span className="text-red-600">✗ 不通</span>
      ) : (
        <span className="text-slate-400">— 未验收</span>
      )

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
        <td className="px-3 py-2 text-xs">{liveLabel}</td>
        <td className="px-3 py-2 text-xs text-slate-500">{m.note}</td>
      </tr>
    )
  }

  function FamilySection({ family, models, liveAvailable }: { family: string; models: Model[]; liveAvailable: boolean }) {
    const label = FAMILY_LABEL[family] ?? family
    const rows = models
    const shown = liveAvailable ? rows.filter((m) => m.enabled) : rows.filter((m) => m.enabled && !m.official_current)
    if (!shown.length) return null
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
                <th className="text-left px-3 py-2">Live</th>
                <th className="text-left px-3 py-2">说明</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((m) => (
                <ModelRow key={m.id} m={m} />
              ))}
            </tbody>
          </table>
        </div>
      </section>
    )
  }

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-semibold text-slate-900">模型清单</h1>
      <p className="text-sm text-slate-600 mt-1">
        配置来源 <code className="font-mono">backend/config/models.yaml</code>。
        official_current / live_available / subscription_expected 三态独立维护。
      </p>

      {/* 统计概览 */}
      <section className="mt-4 grid grid-cols-4 gap-3">
        <StatBox
          label="官方当前"
          value={currentModels.length}
          tone="emerald"
          sub={`共 ${currentModels.length} 个官方主模型`}
        />
        <StatBox
          label="实际可用"
          value={registry.models.filter((m) => m.live_available === true).length}
          tone="indigo"
          sub="已验收（live=true）"
        />
        <StatBox
          label="本地配置"
          value={registry.models.filter((m) => m.enabled).length}
          tone="slate"
          sub="含历史兼容"
        />
        <StatBox
          label="历史兼容"
          value={legacyModels.length}
          tone="amber"
          sub="已废弃或过期"
        />
      </section>

      {/* 官方当前模型 */}
      <section className="mt-8">
        <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
          官方当前模型
        </h2>
        <p className="text-xs text-slate-500 mt-1">official_current: true，官方文档中列出的当前可用模型。</p>
        {Object.entries(currentByFamily).map(([fam, models]) => (
          <FamilySection key={fam} family={fam} models={models} liveAvailable={true} />
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
              <span className="text-xs text-slate-500 font-normal hidden group-open:block">
                ▼
              </span>
            </summary>
            <p className="text-xs text-slate-500 mt-1 mb-2">official_current: false 或 tier 为 legacy/deprecated，默认隐藏。</p>
            {Object.entries(legacyByFamily).map(([fam, models]) => (
              <FamilySection key={fam} family={fam} models={models} liveAvailable={false} />
            ))}
          </details>
        </section>
      )}
    </div>
  )
}

function StatBox({ label, value, tone, sub }: { label: string; value: number; tone: string; sub: string }) {
  const toneCls: Record<string, string> = {
    emerald: 'text-emerald-600 border-emerald-200 bg-emerald-50',
    indigo: 'text-indigo-600 border-indigo-200 bg-indigo-50',
    amber: 'text-amber-600 border-amber-200 bg-amber-50',
    slate: 'text-slate-700 border-slate-200 bg-slate-50',
  }
  return (
    <div className={`rounded-lg border px-4 py-3 ${toneCls[tone]}`}>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs font-medium mt-0.5">{label}</div>
      <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>
    </div>
  )
}
