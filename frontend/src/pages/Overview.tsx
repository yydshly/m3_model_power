/**
 * Overview.tsx — MiniMax Token Plan Workbench homepage.
 *
 * First screen answers:
 * 1. How far has Token Plan verification progressed?
 * 2. What can I do right now?
 * 3. Which capabilities are safe to test?
 * 4. Which capabilities need caution?
 * 5. How do I navigate to capability runner / advanced testing / workflows?
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHealth, getRunnerTemplates, getTestConsoleHistory } from '../api'
import type { TestConsoleHistoryItem } from '../api'
import { useRegistry } from '../store'
import { computeWorkbenchStats } from '../workbenchStatus'
import { buildOverviewStats } from '../domain/overviewStats'
import OverviewHero from '../components/overview/OverviewHero'
import OverviewActionCards from '../components/overview/OverviewActionCards'
import OverviewRecentHistory from '../components/overview/OverviewRecentHistory'
import OverviewRiskGuide from '../components/overview/OverviewRiskGuide'
import OverviewDiagnostics from '../components/overview/OverviewDiagnostics'

export default function Overview() {
  const { registry, error: regErr } = useRegistry()
  const [h, setH] = useState<import('../api').HealthResp | null>(null)
  const [healthErr, setHealthErr] = useState<string | null>(null)
  const [runnerSupported, setRunnerSupported] = useState<Set<string>>(new Set())
  const [runnerTemplatesErr, setRunnerTemplatesErr] = useState<string | null>(null)
  const [recentHistory, setRecentHistory] = useState<TestConsoleHistoryItem[]>([])

  useEffect(() => {
    getHealth()
      .then(setH)
      .catch((e) => setHealthErr(String(e)))
  }, [])

  useEffect(() => {
    getRunnerTemplates()
      .then((r) => setRunnerSupported(new Set(r.supported)))
      .catch((e) => setRunnerTemplatesErr(String(e)))
  }, [])

  useEffect(() => {
    getTestConsoleHistory(5)
      .then((r) => setRecentHistory(r.items))
      .catch(() => setRecentHistory([]))
  }, [])

  const overviewStats = registry ? buildOverviewStats(registry) : null
  const workbenchStats =
    registry && runnerSupported.size > 0
      ? computeWorkbenchStats(registry, runnerSupported)
      : null

  return (
    <div className="p-8 max-w-6xl">
      {/* Hero + core status cards + connectivity */}
      <OverviewHero
        health={h}
        healthErr={healthErr}
        completionPercent={overviewStats?.completionPercent ?? 0}
        inScopeCovered={overviewStats?.inScopeCovered ?? 0}
        inScopeTotal={overviewStats?.inScopeTotal ?? 0}
        directlyTestable={overviewStats?.directlyTestable ?? 0}
        cautionRequired={overviewStats?.cautionRequired ?? 0}
        hasRecentHistory={recentHistory.length > 0}
      />

      {/* "What do I want to do?" action cards */}
      <OverviewActionCards />

      {/* Recent invocation overview */}
      <OverviewRecentHistory />

      {/* Risk explanation */}
      <OverviewRiskGuide />

      {/* Advanced diagnostics — collapsed by default */}
      <OverviewDiagnostics
        overviewStats={overviewStats}
        workbenchStats={workbenchStats}
      />

      {regErr && (
        <div className="mt-6 text-sm text-red-600">无法加载能力图谱：{regErr}</div>
      )}

      {/* Category navigation */}
      {registry && (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">能力目录</h2>
          <div className="grid grid-cols-3 gap-3">
            {registry.categories.map((cat) => {
              const caps = registry.capabilities.filter((c) => c.category === cat.id)
              const ok = caps.filter((c) => c.status === 'implemented').length
              return (
                <Link
                  to={`/category/${cat.id}`}
                  key={cat.id}
                  className="rounded-lg border border-slate-200 bg-white p-4 hover:border-slate-400 transition"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{cat.emoji}</span>
                    <span className="font-medium text-slate-900">{cat.label}</span>
                    <span className="ml-auto text-xs text-slate-500">
                      {ok}/{caps.length}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{cat.desc}</div>
                </Link>
              )
            })}
          </div>
        </section>
      )}

      {runnerTemplatesErr && (
        <div className="mt-6 text-sm text-red-600">
          Runner 产品化状态加载失败，请检查 /api/runner/templates：{runnerTemplatesErr}
        </div>
      )}

      <p className="mt-8 text-xs text-slate-400">
        当前数据来自本项目 registry，不等同于 MiniMax 官方套餐完整说明。
      </p>
    </div>
  )
}
