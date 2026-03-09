import { Routes, Route, useLocation } from 'react-router-dom'
import { lazy, Suspense, useEffect } from 'react'
import { EnhancedLayout } from './components/EnhancedLayout'
import { useStore } from './store'

// Lazy-loaded pages (each becomes its own chunk for faster initial load)
const Dashboard = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const Chat = lazy(() => import('./pages/EnhancedChat').then(m => ({ default: m.EnhancedChat })))
const Terminals = lazy(() => import('./pages/Terminals').then(m => ({ default: m.Terminals })))
const Council = lazy(() => import('./pages/Council').then(m => ({ default: m.Council })))
const EnhancedSettings = lazy(() => import('./pages/EnhancedSettings'))
const Workflows = lazy(() => import('./pages/Workflows').then(m => ({ default: m.Workflows })))
const WorkflowDesigner = lazy(() => import('./pages/WorkflowDesigner').then(m => ({ default: m.WorkflowDesigner })))
const Tools = lazy(() => import('./pages/Tools').then(m => ({ default: m.Tools })))
const Memory = lazy(() => import('./pages/Memory').then(m => ({ default: m.Memory })))
const Agents = lazy(() => import('./pages/Agents').then(m => ({ default: m.Agents })))
const MCPServers = lazy(() => import('./pages/MCPServers').then(m => ({ default: m.MCPServers })))
const APEXDashboard = lazy(() => import('./pages/APEXDashboard'))
const MemoryExplorer = lazy(() => import('./pages/MemoryExplorer'))
const SwarmDashboard = lazy(() => import('./pages/SwarmDashboard'))
const GodModeDashboard = lazy(() => import('./pages/GodModeDashboard'))
const FileBrowser = lazy(() => import('./pages/FileBrowser'))
const ProjectsPage = lazy(() => import('./pages/Projects'))
const AutomationHub = lazy(() => import('./pages/AutomationHub'))
const CapabilityMatrix = lazy(() => import('./pages/CapabilityMatrix'))
const CreativeWorkflows = lazy(() => import('./pages/CreativeWorkflows'))
const OpportunityDiscovery = lazy(() => import('./pages/OpportunityDiscovery'))

// Comfort & UX Components
import { ErrorBoundary } from './components/ErrorBoundary'
import { Toaster } from './hooks/useToast'
import { useGlobalShortcuts } from './components/KeyboardShortcuts'

// Phase 2 Advanced UX Components
import { ProgressProvider } from './components/Progress'
import { usePageTracking } from './hooks/useSessionPersistence'

// Loading fallback for lazy routes
function PageLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100%', color: '#888', fontSize: '14px'
    }}>
      Loading…
    </div>
  )
}

export default function App() {
  const { initialize } = useStore()
  const location = useLocation()

  useEffect(() => {
    initialize()
  }, [initialize])

  // Enable global keyboard shortcuts
  useGlobalShortcuts()

  // Track page visits for session persistence
  usePageTracking(location.pathname)

  return (
    <ErrorBoundary>
      <ProgressProvider>
        <Toaster />
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<EnhancedLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="chat" element={<Chat />} />
              <Route path="terminals" element={<Terminals />} />
              <Route path="council" element={<Council />} />
              <Route path="workflows" element={<Workflows />} />
              <Route path="workflow-designer" element={<WorkflowDesigner />} />
              <Route path="tools" element={<Tools />} />
              <Route path="memory" element={<Memory />} />
              <Route path="memory-explorer" element={<MemoryExplorer />} />
              <Route path="agents" element={<Agents />} />
              <Route path="mcp" element={<MCPServers />} />
              <Route path="apex" element={<APEXDashboard />} />
              <Route path="swarm" element={<SwarmDashboard />} />
              <Route path="god-mode" element={<GodModeDashboard />} />
              <Route path="files" element={<FileBrowser />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="automation-hub" element={<AutomationHub />} />
              <Route path="capability-matrix" element={<CapabilityMatrix />} />
              <Route path="creative-workflows" element={<CreativeWorkflows />} />
              <Route path="opportunity-discovery" element={<OpportunityDiscovery />} />
              <Route path="settings" element={<EnhancedSettings />} />
            </Route>
          </Routes>
        </Suspense>
      </ProgressProvider>
    </ErrorBoundary>
  )
}
