import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getScenarios, type CapabilityScenario } from '../api'
import {
  getPrimaryRunnerCapabilityForScenario,
  getScenarioChainSteps,
  getWorkflowLink,
  isRunnerSupported,
  getCapabilityDetailLink,
  getCapabilityTestabilityLabel,
  getTestConsoleLink,
  type ChainStep,
} from '../navigation/capabilityLinks'

const FAMILY_EMOJI: Record<string, string> = {
  chat: '💬',
  voice: '🎙️',
  vision: '🖼️',
  music: '🎵',
  assets: '📁',
  models: '🧠',
}

const RISK_LABEL: Record<string, { text: string; className: string }> = {
  safe: { text: '低风险', className: 'bg-emerald-100 text-emerald-700' },
  low: { text: '低风险', className: 'bg-emerald-100 text-emerald-700' },
  medium: { text: '中等风险', className: 'bg-amber-100 text-amber-700' },
  guarded: { text: '需确认', className: 'bg-amber-100 text-amber-700' },
  high: { text: '高风险', className: 'bg-red-100 text-red-700' },
  blocked: { text: '阻断', className: 'bg-red-100 text-red-700' },
}

function RiskBadge({ level }: { level: string }) {
  const entry = RISK_LABEL[level] ?? { text: level, className: 'bg-slate-100 text-slate-600' }
  return <span className={`text-[10px] px-1.5 py-0.5 rounded ${entry.className}`}>{entry.text}</span>
}

export default function CapabilityScenariosPage() {
  const [scenarios, setScenarios] = useState<Record<string, CapabilityScenario> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getScenarios()
      .then((data) => { setScenarios(data.scenarios); setLoading(false) })
      .catch((e) => { setError(String(e)); setLoading(false) })
  }, [])

  if (loading) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  if (error) return <div className="p-8 text-sm text-red-600">加载失败：{error}</div>
  if (!scenarios) return <div className="p-8 text-sm text-slate-500">无数据</div>

  const scenarioList = Object.values(scenarios)

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">场景推荐</h1>
        <p className="text-sm text-slate-600 mt-1">
          从你的目标出发，找到推荐的能力链路和测试入口。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {scenarioList.map((s) => (
          <div key={s.id} className="rounded-xl border border-slate-200 bg-white shadow-sm">
            {/* Header */}
            <div className="px-5 py-4 border-b border-slate-100">
              <div className="flex items-start gap-3">
                <span className="text-2xl mt-0.5">{FAMILY_EMOJI[s.capability_family] ?? '📦'}</span>
                <div className="flex-1 min-w-0">
                  <h2 className="text-base font-semibold text-slate-900">{s.label}</h2>
                  <p className="text-xs text-slate-500 mt-0.5">{s.capability_family}</p>
                </div>
                <RiskBadge level={s.risk_level} />
              </div>
            </div>

            {/* Body */}
            <div className="px-5 py-4 space-y-3">
              <p className="text-sm text-slate-600">{s.summary}</p>

              {/* Recommended For */}
              {s.recommended_for.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-slate-500 mb-1">适合</h3>
                  <div className="flex flex-wrap gap-1">
                    {s.recommended_for.map((r) => (
                      <span key={r} className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{r}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Capabilities */}
              <div>
                <h3 className="text-xs font-medium text-slate-500 mb-1">涉及能力</h3>
                <div className="flex flex-wrap gap-1">
                  {s.capabilities.map((cap) => {
                    const testability = getCapabilityTestabilityLabel(cap)
                    const runnerSupported = isRunnerSupported(cap)
                    return runnerSupported ? (
                      <Link
                        key={cap}
                        to={`/capability-runner?capability=${cap}&from_scenario=${s.id}`}
                        className="inline-flex items-center gap-1 text-[10px] bg-sky-50 text-sky-700 px-1.5 py-0.5 rounded hover:bg-sky-100"
                      >
                        {cap}
                        <span className={`text-[9px] px-1 rounded ${testability.cls}`}>{testability.text}</span>
                      </Link>
                    ) : (
                      <Link
                        key={cap}
                        to={getCapabilityDetailLink(cap)}
                        className="inline-flex items-center gap-1 text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded hover:bg-slate-200"
                      >
                        {cap}
                        <span className={`text-[9px] px-1 rounded ${testability.cls}`}>{testability.text}</span>
                      </Link>
                    )
                  })}
                </div>
              </div>

              {/* Recommended Models */}
              {s.recommended_models.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-slate-500 mb-1">模型建议</h3>
                  <div className="space-y-1">
                    {s.recommended_models.map((m) => (
                      <div key={m.model} className="text-xs bg-slate-50 px-2 py-1 rounded">
                        <span className="font-mono text-slate-700">{m.model}</span>
                        <span className="text-slate-400 ml-1">— {m.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expected Output */}
              <div>
                <h3 className="text-xs font-medium text-slate-500 mb-1">预期输出</h3>
                <p className="text-xs text-slate-600">{s.expected_output}</p>
              </div>

              {/* Mock chain display */}
              <div className="pt-1">
                <h3 className="text-xs font-medium text-slate-500 mb-1">体验链路</h3>
                <div className="flex flex-wrap items-center gap-1">
                  {getScenarioChainSteps(s.capabilities).map((step: ChainStep, i: number) => (
                    <span key={step.capabilityId} className="flex items-center gap-1">
                      {i > 0 && <span className="text-slate-300">→</span>}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${step.testability.cls}`}>
                        {step.capabilityId}
                      </span>
                    </span>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <div className="pt-2 flex items-center gap-3 flex-wrap">
                {(() => {
                  const primary = getPrimaryRunnerCapabilityForScenario(s.capabilities)
                  if (primary) {
                    return (
                      <Link
                        to={`/capability-runner?capability=${primary}&from_scenario=${s.id}`}
                        className="inline-flex items-center gap-1.5 text-sm bg-slate-900 text-white px-4 py-2 rounded-lg hover:bg-slate-700 transition"
                      >
                        开始体验 →
                      </Link>
                    )
                  }
                  // No Runner capability — check if TestConsole is available
                  const firstCap = s.capabilities[0]
                  return (
                    <Link
                      to={getTestConsoleLink(firstCap)}
                      className="inline-flex items-center gap-1.5 text-sm bg-slate-800 text-white px-4 py-2 rounded-lg hover:bg-slate-700 transition"
                    >
                      高级测试 {firstCap} →
                    </Link>
                  )
                })()}
                <Link
                  to={getWorkflowLink(s.workflow_id, s.id)}
                  className="inline-flex items-center gap-1.5 text-sm bg-slate-100 text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-200 transition"
                >
                  查看流程 →
                </Link>
              </div>
              {/* Note for scenarios without Runner */}
              {!getPrimaryRunnerCapabilityForScenario(s.capabilities) && (
                <p className="text-[10px] text-slate-400 mt-1">
                  该场景能力当前未产品化为 Runner 流程，可通过「高级测试」先行体验。
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
