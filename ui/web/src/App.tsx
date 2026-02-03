import { Routes, Route, useLocation } from 'react-router-dom'
import { EnhancedLayout } from './components/EnhancedLayout'
import { Dashboard } from './pages/Dashboard'
import { EnhancedChat as Chat } from './pages/EnhancedChat'
import { Terminals } from './pages/Terminals'
import { Council } from './pages/Council'
import EnhancedSettings from './pages/EnhancedSettings'
import { Workflows } from './pages/Workflows'
import { WorkflowDesigner } from './pages/WorkflowDesigner'
import { Tools } from './pages/Tools'
import { Memory } from './pages/Memory'
import { Agents } from './pages/Agents'
import { MCPServers } from './pages/MCPServers'
import APEXDashboard from './pages/APEXDashboard'
import MemoryExplorer from './pages/MemoryExplorer'
import SwarmDashboard from './pages/SwarmDashboard'
import GodModeDashboard from './pages/GodModeDashboard'
import FileBrowser from './pages/FileBrowser'
import ProjectsPage from './pages/Projects'
import { useStore } from './store'
import { useEffect } from 'react'

// Comfort & UX Components
import { ErrorBoundary } from './components/ErrorBoundary'
import { Toaster } from './hooks/useToast'
import { ConnectionStatus } from './components/ConnectionStatus'
import { APIKeyWarning } from './components/APIKeyWarning'
import { SetupWizard } from './components/SetupWizard'
import { KeyboardShortcutsModal, useGlobalShortcuts } from './components/KeyboardShortcuts'

// Phase 2 Advanced UX Components
import { QuickActionsFAB } from './components/QuickActions'
import { QuickSettingsPanel } from './components/QuickSettings'
import { ProgressProvider, ProgressOverlay } from './components/Progress'
import { SystemStatusWidget } from './components/SystemStatus'
import { usePageTracking } from './hooks/useSessionPersistence'
import { TipsWidget } from './components/TipsWidget'

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
      {/* Progress Context Provider */}
      <ProgressProvider>
        {/* Toast Notifications */}
        <Toaster />

        {/* All overlays disabled for debugging */}
        {/* <ConnectionStatus /> */}
        {/* <APIKeyWarning /> */}
        {/* <SystemStatusWidget /> */}
        {/* <SetupWizard /> */}
        {/* <KeyboardShortcutsModal /> */}
        {/* <QuickSettingsPanel /> */}
        {/* <ProgressOverlay /> */}
        {/* <TipsWidget /> */}
        {/* <QuickActionsFAB /> */}

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
            <Route path="settings" element={<EnhancedSettings />} />
          </Route>
        </Routes>
      </ProgressProvider>
    </ErrorBoundary>
  )
}
