import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getWorkflows, getWorkflow, type CapabilityWorkflow } from '../api'
import { getCapabilityDetailLink, getTestConsoleLink, isRunnerSupported, getCapabilityTestabilityLabel, isHighRisk, isAdvancedTest, isRunnerNotProductized } from '../navigation/capabilityLinks'

const FAMILY_EMOJI: Record<string, string> = {
  chat: '💬',
  voice: '🎙️',
  vision: '🖼️',
  music: '🎵',
  assets: '📁',
  models: '🧠',
}

const STEP_TYPE_LABEL: Record<string, string> = {
  capability: '能力调用',
  parameter: '参数选择',
  result: '结果展示',
  loop: '循环测试',
}

const STEP_TYPE_BG: Record<string, string> = {
  capability: 'bg-sky-50 border-sky-200',
  parameter: 'bg-violet-50 border-violet-200',
  result: 'bg-emerald-50 border-emerald-200',
  loop: 'bg-amber-50 border-amber-200',
}

const RISK_LABEL: Record<string, { text: string; className: string }> = {
  safe: { text: '安全', className: 'text-emerald-600' },
  low: { text: '安全', className: 'text-emerald-600' },
  guarded: { text: '需确认', className: 'text-amber-600' },
  medium: { text: '需确认', className: 'text-amber-600' },
  blocked: { text: '阻断', className: 'text-red-600' },
  high: { text: '高风险', className: 'text-red-600' },
}

function RiskLabel({ level }: { level: string }) {
  const entry = RISK_LABEL[level] ?? { text: level, className: 'text-slate-500' }
  return <span className={`text-xs font-medium ${entry.className}`}>{entry.text}</span>
}

function WorkflowCard({ workflow }: { workflow: CapabilityWorkflow }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{FAMILY_EMOJI[workflow.family] ?? '📦'}</span>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{workflow.label}</h2>
            <p className="text-xs text-slate-500 mt-0.5">{workflow.family} · {workflow.id}</p>
          </div>
        </div>
        <p className="text-sm text-slate-600 mt-3">{workflow.summary}</p>
      </div>

      {/* Steps */}
      <div className="px-5 py-4">
        <h3 className="text-xs font-medium text-slate-500 mb-3">执行步骤</h3>
        <div className="relative">
          {workflow.steps.map((step, index) => (
            <div key={step.step_id} className="flex gap-4 mb-4 last:mb-0">
              {/* Step number + connector */}
              <div className="flex flex-col items-center">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 ${STEP_TYPE_BG[step.type]?.replace('bg-', 'bg-').replace('-50', '-600') ?? 'bg-slate-500'}`}>
                  {index + 1}
                </div>
                {index < workflow.steps.length - 1 && (
                  <div className="w-0.5 flex-1 bg-slate-200 my-1" />
                )}
              </div>

              {/* Step content */}
              <div className={`flex-1 rounded-lg border px-4 py-3 ${STEP_TYPE_BG[step.type] ?? 'bg-slate-50 border-slate-200'}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-slate-800">{step.label}</span>
                  <span className="text-[10px] bg-white bg-opacity-60 px-1.5 py-0.5 rounded text-slate-500">
                    {STEP_TYPE_LABEL[step.type] ?? step.type}
                  </span>
                  <span className="text-[10px] bg-white bg-opacity-60 px-1.5 py-0.5 rounded text-slate-500">
                    <RiskLabel level={step.risk_level} />
                  </span>
                </div>

                {step.capability_id && (
                  <div className="mt-1">
                    <Link
                      to={`/test-console?capability=${step.capability_id}`}
                      className="text-xs font-mono text-sky-600 hover:underline"
                    >
                      {step.capability_id}
                    </Link>
                  </div>
                )}

                {step.input && (
                  <div className="mt-1 text-xs text-slate-500">
                    <span className="text-slate-400">输入:</span> {step.input}
                  </div>
                )}
                {step.output && (
                  <div className="mt-0.5 text-xs text-slate-500">
                    <span className="text-slate-400">输出:</span> {step.output}
                  </div>
                )}
                {step.next_usage && (
                  <div className="mt-0.5 text-xs text-slate-500">
                    <span className="text-slate-400">下一步:</span> {step.next_usage}
                  </div>
                )}

                {step.type === 'capability' && step.capability_id && (
                  <div className="mt-2 flex items-center gap-3 flex-wrap">
                    <Link
                      to={getCapabilityDetailLink(step.capability_id)}
                      className="inline-flex items-center gap-1 text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-lg hover:bg-slate-200 transition"
                    >
                      能力说明
                    </Link>
                    {(() => {
                      const runnerSupported = isRunnerSupported(step.capability_id)
                      const testability = getCapabilityTestabilityLabel(step.capability_id)
                      if (runnerSupported) {
                        return (
                          <Link
                            to={`/capability-runner?capability=${step.capability_id}&from_workflow=${workflow.id}`}
                            className="inline-flex items-center gap-1 text-xs bg-slate-900 text-white px-3 py-1 rounded-lg hover:bg-slate-700 transition"
                          >
                            去体验
                            <span className={`ml-1 text-[9px] px-1 rounded ${testability.cls}`}>
                              {testability.text}
                            </span>
                          </Link>
                        )
                      }
                      // Not Runner-supported — show proper status instead of disabled button
                      if (isHighRisk(step.capability_id)) {
                        return (
                          <span className="inline-flex items-center gap-1 text-xs bg-red-50 text-red-600 px-3 py-1 rounded-lg">
                            风险能力，不默认执行
                          </span>
                        )
                      }
                      if (isAdvancedTest(step.capability_id)) {
                        return (
                          <span className="inline-flex items-center gap-1 text-xs bg-sky-50 text-sky-600 px-3 py-1 rounded-lg">
                            高级测试可用
                          </span>
                        )
                      }
                      if (isRunnerNotProductized(step.capability_id)) {
                        return (
                          <span className="inline-flex items-center gap-1 text-xs bg-slate-50 text-slate-500 px-3 py-1 rounded-lg">
                            已验收，Runner 未产品化
                          </span>
                        )
                      }
                      return (
                        <span className="inline-flex items-center gap-1 text-xs bg-slate-50 text-slate-500 px-3 py-1 rounded-lg">
                          {testability.text}
                        </span>
                      )
                    })()}
                    <Link
                      to={getTestConsoleLink(step.capability_id!)}
                      className="text-[10px] text-sky-500 hover:text-sky-700"
                    >
                      高级测试 →
                    </Link>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Expected outputs */}
      {workflow.expected_outputs.length > 0 && (
        <div className="px-5 py-3 border-t border-slate-100">
          <h3 className="text-xs font-medium text-slate-500 mb-1.5">预期输出</h3>
          <div className="flex flex-wrap gap-1">
            {workflow.expected_outputs.map((o) => (
              <span key={o} className="text-[10px] bg-purple-50 text-purple-700 px-1.5 py-0.5 rounded">{o}</span>
            ))}
          </div>
        </div>
      )}

      {/* Risk policy */}
      <div className="px-5 py-3 border-t border-slate-100">
        <h3 className="text-xs font-medium text-slate-500 mb-1.5">风险策略</h3>
        <div className="flex flex-wrap gap-2 text-xs">
          {workflow.risk_policy.allow_direct.length > 0 && (
            <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded">
              可直接: {workflow.risk_policy.allow_direct.join(', ')}
            </span>
          )}
          {workflow.risk_policy.guarded.length > 0 && (
            <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
              需确认: {workflow.risk_policy.guarded.join(', ')}
            </span>
          )}
          {workflow.risk_policy.blocked.length > 0 && (
            <span className="bg-red-50 text-red-700 px-2 py-0.5 rounded">
              阻断: {workflow.risk_policy.blocked.join(', ')}
            </span>
          )}
        </div>
      </div>

      {/* Product usage */}
      {workflow.product_usage.length > 0 && (
        <div className="px-5 py-3 border-t border-slate-100">
          <h3 className="text-xs font-medium text-slate-500 mb-1.5">产品用途</h3>
          <ul className="space-y-0.5">
            {workflow.product_usage.map((u, i) => (
              <li key={i} className="text-xs text-slate-600">• {u}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function CapabilityWorkflowsPage() {
  const [searchParams] = useSearchParams()
  const initialWorkflow = searchParams.get('workflow')

  const [workflows, setWorkflows] = useState<Record<string, CapabilityWorkflow> | null>(null)
  const [selectedWorkflow, setSelectedWorkflow] = useState<CapabilityWorkflow | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialWorkflow) {
      getWorkflow(initialWorkflow)
        .then((data) => { setSelectedWorkflow(data.workflow); setLoading(false) })
        .catch((e) => { setError(String(e)); setLoading(false) })
    } else {
      getWorkflows()
        .then((data) => { setWorkflows(data.workflows); setLoading(false) })
        .catch((e) => { setError(String(e)); setLoading(false) })
    }
  }, [initialWorkflow])

  if (loading) return <div className="p-8 text-sm text-slate-500">加载中…</div>
  if (error) return <div className="p-8 text-sm text-red-600">加载失败：{error}</div>

  // Show selected workflow detail
  if (initialWorkflow && selectedWorkflow) {
    return (
      <div className="p-8 max-w-4xl">
        <div className="mb-4">
          <Link to="/capability-workflows" className="text-xs text-sky-600 hover:underline">← 返回流程列表</Link>
        </div>
        <WorkflowCard workflow={selectedWorkflow} />
      </div>
    )
  }

  if (!workflows) return <div className="p-8 text-sm text-slate-500">无数据</div>

  const workflowList = Object.values(workflows)

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">流程体验</h1>
        <p className="text-sm text-slate-600 mt-1">
          按步骤执行能力调用，体验完整的能力链路。每个步骤都可以跳转到高级测试控制台。
        </p>
      </div>

      <div className="space-y-6">
        {workflowList.map((wf) => (
          <div key={wf.id}>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xl">{FAMILY_EMOJI[wf.family] ?? '📦'}</span>
              <h2 className="text-base font-semibold text-slate-800">{wf.label}</h2>
              <span className="text-xs text-slate-400">{wf.id}</span>
              <Link
                to={`/capability-workflows?workflow=${wf.id}`}
                className="ml-auto text-xs text-sky-600 hover:underline"
              >
                查看详情 →
              </Link>
            </div>
            <p className="text-sm text-slate-600 mb-3">{wf.summary}</p>
            <div className="flex flex-wrap gap-2">
              {wf.steps.filter(s => s.type === 'capability' && s.capability_id).map((step) => (
                <div key={step.step_id} className="flex items-center gap-1.5 bg-slate-50 rounded px-3 py-1.5 text-xs">
                  <span className="text-slate-400">→</span>
                  <span className="font-mono text-slate-700">{step.capability_id}</span>
                  <span className="text-slate-400">({step.label})</span>
                  <Link
                    to={getCapabilityDetailLink(step.capability_id!)}
                    className="text-slate-400 hover:text-slate-600 ml-1"
                  >
                    说明
                  </Link>
                  {isRunnerSupported(step.capability_id!) ? (
                    <Link
                      to={`/capability-runner?capability=${step.capability_id!}`}
                      className="text-sky-600 hover:underline ml-1"
                    >
                      体验
                    </Link>
                  ) : (
                    <span className="text-slate-400 ml-1">高级测试</span>
                  )}
                  <Link
                    to={`/test-console?capability=${step.capability_id}`}
                    className="text-slate-400 hover:text-slate-600 ml-1"
                  >
                    高级测试
                  </Link>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
