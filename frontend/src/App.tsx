import { NavLink, Route, Routes } from 'react-router-dom'
import CapabilityPage from './pages/Capability'
import CapabilityProfilesPage from './pages/CapabilityProfiles'
import CapabilityRunnerPage from './pages/CapabilityRunner'
import CapabilityScenariosPage from './pages/CapabilityScenarios'
import CapabilityWorkflowsPage from './pages/CapabilityWorkflows'
import CategoryPage from './pages/Category'
import ModelsPage from './pages/Models'
import Overview from './pages/Overview'
import TestConsole from './pages/TestConsole'
import { RegistryProvider, useRegistry } from './store'

export default function App() {
  return (
    <RegistryProvider>
      <Shell />
    </RegistryProvider>
  )
}

function Shell() {
  const { registry, error, reload } = useRegistry()
  return (
    <div className="flex h-full">
      <aside className="w-60 shrink-0 border-r border-slate-200 bg-white flex flex-col">
        <div className="px-4 py-5 border-b border-slate-200">
          <div className="text-lg font-semibold text-slate-900">MiniMax 工作台</div>
          <div className="text-xs text-slate-500 mt-1">TokenPlanPlus · 极速版</div>
        </div>
        <nav className="p-2 space-y-0.5 flex-1 overflow-auto">
          <NavItem to="/" emoji="🏠" label="总览" />
          {registry?.categories.map((c) => (
            <NavItem key={c.id} to={`/category/${c.id}`} emoji={c.emoji} label={c.label}
              hint={`${registry.capabilities.filter((x) => x.category === c.id && x.status === 'implemented').length}/${registry.capabilities.filter((x) => x.category === c.id).length}`}
            />
          ))}
          <NavItem to="/models-all" emoji="🧬" label="所有模型" />
          <NavItem to="/capability-profiles" emoji="🧭" label="能力画像" />
          <NavItem to="/capability-scenarios" emoji="🎯" label="场景推荐" />
          <NavItem to="/capability-workflows" emoji="🔁" label="流程体验" />
          <NavItem to="/capability-runner" emoji="⚡" label="能力体验" />
          <NavItem to="/test-console" emoji="🧪" label="高级测试" />
        </nav>
        <div className="p-3 border-t border-slate-200 text-xs text-slate-500">
          {error ? (
            <div className="text-red-600">注册中心不可达</div>
          ) : (
            <div>
              {registry ? `${registry.capabilities.length} 能力 · ${registry.models.filter(m => m.enabled).length} 模型` : '加载中…'}
            </div>
          )}
          <button onClick={reload} className="mt-2 text-sky-600 hover:underline">重新加载</button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/category/:id" element={<CategoryPage />} />
          <Route path="/cap/:id" element={<CapabilityPage />} />
          <Route path="/models-all" element={<ModelsPage />} />
          <Route path="/test-console" element={<TestConsole />} />
          <Route path="/capability-profiles" element={<CapabilityProfilesPage />} />
          <Route path="/capability-scenarios" element={<CapabilityScenariosPage />} />
          <Route path="/capability-workflows" element={<CapabilityWorkflowsPage />} />
          <Route path="/capability-runner" element={<CapabilityRunnerPage />} />
        </Routes>
      </main>
    </div>
  )
}

function NavItem({ to, emoji, label, hint }: { to: string; emoji: string; label: string; hint?: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-2 px-3 py-2 rounded-md text-sm ${
          isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
        }`
      }
    >
      <span className="text-base leading-none">{emoji}</span>
      <span>{label}</span>
      {hint && <span className="ml-auto text-[10px] opacity-70">{hint}</span>}
    </NavLink>
  )
}
