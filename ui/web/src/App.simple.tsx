import { Routes, Route, NavLink, Outlet } from 'react-router-dom'

function SimpleLayout() {
  return (
    <div style={{ display: 'flex', height: '100vh', background: '#0a0a0f', color: 'white' }}>
      {/* Sidebar */}
      <nav style={{ width: '200px', background: '#12121a', padding: '20px' }}>
        <h2 style={{ marginBottom: '20px' }}>BAEL</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li style={{ marginBottom: '10px' }}>
            <NavLink
              to="/"
              style={({ isActive }) => ({
                color: isActive ? '#6366f1' : '#e0e0e0',
                textDecoration: 'none',
                display: 'block',
                padding: '10px',
                borderRadius: '8px',
                background: isActive ? '#6366f120' : 'transparent'
              })}
            >
              Dashboard
            </NavLink>
          </li>
          <li style={{ marginBottom: '10px' }}>
            <NavLink
              to="/chat"
              style={({ isActive }) => ({
                color: isActive ? '#6366f1' : '#e0e0e0',
                textDecoration: 'none',
                display: 'block',
                padding: '10px',
                borderRadius: '8px',
                background: isActive ? '#6366f120' : 'transparent'
              })}
            >
              Chat
            </NavLink>
          </li>
          <li style={{ marginBottom: '10px' }}>
            <NavLink
              to="/tools"
              style={({ isActive }) => ({
                color: isActive ? '#6366f1' : '#e0e0e0',
                textDecoration: 'none',
                display: 'block',
                padding: '10px',
                borderRadius: '8px',
                background: isActive ? '#6366f120' : 'transparent'
              })}
            >
              Tools
            </NavLink>
          </li>
          <li style={{ marginBottom: '10px' }}>
            <NavLink
              to="/settings"
              style={({ isActive }) => ({
                color: isActive ? '#6366f1' : '#e0e0e0',
                textDecoration: 'none',
                display: 'block',
                padding: '10px',
                borderRadius: '8px',
                background: isActive ? '#6366f120' : 'transparent'
              })}
            >
              Settings
            </NavLink>
          </li>
        </ul>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: '20px', overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}

function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to BAEL Dashboard</p>
      <button
        onClick={() => alert('Button clicked!')}
        style={{
          marginTop: '20px',
          padding: '10px 20px',
          background: '#6366f1',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer'
        }}
      >
        Test Click
      </button>
    </div>
  )
}

function ChatPage() {
  return (
    <div>
      <h1>Chat</h1>
      <p>Chat interface</p>
    </div>
  )
}

function ToolsPage() {
  return (
    <div>
      <h1>Tools</h1>
      <p>Available tools</p>
    </div>
  )
}

function SettingsPage() {
  return (
    <div>
      <h1>Settings</h1>
      <p>Settings page</p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SimpleLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="tools" element={<ToolsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
