import { useState, useEffect, useCallback } from 'react'
import {
  Folder,
  File,
  FileText,
  FileCode,
  FileImage,
  ChevronRight,
  ChevronDown,
  Upload,
  Download,
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  RefreshCw,
  Search,
  FolderPlus,
  Home,
  HardDrive,
  Copy,
  Scissors,
  Clipboard,
  MoreVertical,
  Eye,
  Code,
  Terminal
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

// Types
interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified?: string
  children?: FileNode[]
  extension?: string
}

interface FileTab {
  path: string
  name: string
  content: string
  isDirty: boolean
  language: string
}

// Language detection
const getLanguage = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  const langMap: Record<string, string> = {
    'py': 'python',
    'js': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'jsx': 'javascript',
    'json': 'json',
    'md': 'markdown',
    'yaml': 'yaml',
    'yml': 'yaml',
    'html': 'html',
    'css': 'css',
    'sh': 'bash',
    'zsh': 'bash',
    'sql': 'sql',
    'rs': 'rust',
    'go': 'go',
    'rb': 'ruby',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'h': 'c',
  }
  return langMap[ext] || 'plaintext'
}

// File icon based on type/extension
const FileIcon = ({ node }: { node: FileNode }) => {
  if (node.type === 'directory') {
    return <Folder size={16} className="text-amber-400" />
  }

  const ext = node.extension || node.name.split('.').pop()?.toLowerCase() || ''

  const iconMap: Record<string, React.ReactNode> = {
    'py': <FileCode size={16} className="text-blue-400" />,
    'js': <FileCode size={16} className="text-yellow-400" />,
    'ts': <FileCode size={16} className="text-blue-500" />,
    'tsx': <FileCode size={16} className="text-blue-500" />,
    'jsx': <FileCode size={16} className="text-yellow-400" />,
    'json': <FileText size={16} className="text-amber-400" />,
    'md': <FileText size={16} className="text-gray-400" />,
    'png': <FileImage size={16} className="text-pink-400" />,
    'jpg': <FileImage size={16} className="text-pink-400" />,
    'svg': <FileImage size={16} className="text-orange-400" />,
  }

  return iconMap[ext] || <File size={16} className="text-bael-muted" />
}

// Tree Node Component
function TreeNode({
  node,
  level = 0,
  expanded,
  onToggle,
  onSelect,
  selectedPath,
  onContextMenu
}: {
  node: FileNode
  level?: number
  expanded: Set<string>
  onToggle: (path: string) => void
  onSelect: (node: FileNode) => void
  selectedPath: string | null
  onContextMenu: (e: React.MouseEvent, node: FileNode) => void
}) {
  const isExpanded = expanded.has(node.path)
  const isSelected = selectedPath === node.path
  const isDir = node.type === 'directory'

  return (
    <div>
      <div
        className={clsx(
          'flex items-center gap-1 py-1 px-2 rounded cursor-pointer transition-colors',
          isSelected ? 'bg-bael-primary/20 text-bael-primary' : 'hover:bg-bael-border/50',
          level > 0 && 'ml-4'
        )}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
        onClick={() => isDir ? onToggle(node.path) : onSelect(node)}
        onContextMenu={(e) => onContextMenu(e, node)}
      >
        {isDir ? (
          <span className="w-4 flex-shrink-0">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        ) : (
          <span className="w-4" />
        )}
        <FileIcon node={node} />
        <span className="text-sm truncate">{node.name}</span>
        {node.size !== undefined && !isDir && (
          <span className="ml-auto text-xs text-bael-muted">
            {node.size < 1024 ? `${node.size}B` : `${(node.size / 1024).toFixed(1)}KB`}
          </span>
        )}
      </div>

      <AnimatePresence>
        {isDir && isExpanded && node.children && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            {node.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                level={level + 1}
                expanded={expanded}
                onToggle={onToggle}
                onSelect={onSelect}
                selectedPath={selectedPath}
                onContextMenu={onContextMenu}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Simple Code Editor (without Monaco for now - can be upgraded)
function SimpleEditor({
  content,
  language,
  onChange,
  readOnly = false
}: {
  content: string
  language: string
  onChange: (content: string) => void
  readOnly?: boolean
}) {
  return (
    <div className="h-full relative">
      <pre className="absolute inset-0 overflow-auto p-4 m-0">
        <code className={`language-${language}`}>
          <textarea
            value={content}
            onChange={(e) => onChange(e.target.value)}
            readOnly={readOnly}
            className="w-full h-full bg-transparent text-bael-text font-mono text-sm resize-none outline-none"
            spellCheck={false}
            style={{ minHeight: '100%' }}
          />
        </code>
      </pre>
    </div>
  )
}

// Context Menu
function ContextMenu({
  x,
  y,
  node,
  onClose,
  onAction
}: {
  x: number
  y: number
  node: FileNode
  onClose: () => void
  onAction: (action: string, node: FileNode) => void
}) {
  const items = node.type === 'directory' ? [
    { icon: FolderPlus, label: 'New Folder', action: 'newFolder' },
    { icon: Plus, label: 'New File', action: 'newFile' },
    { divider: true },
    { icon: Edit3, label: 'Rename', action: 'rename' },
    { icon: Copy, label: 'Copy Path', action: 'copyPath' },
    { divider: true },
    { icon: Trash2, label: 'Delete', action: 'delete', danger: true },
  ] : [
    { icon: Eye, label: 'Open', action: 'open' },
    { icon: Code, label: 'Open in Editor', action: 'edit' },
    { icon: Terminal, label: 'Open in Terminal', action: 'terminal' },
    { divider: true },
    { icon: Edit3, label: 'Rename', action: 'rename' },
    { icon: Copy, label: 'Copy Path', action: 'copyPath' },
    { icon: Download, label: 'Download', action: 'download' },
    { divider: true },
    { icon: Trash2, label: 'Delete', action: 'delete', danger: true },
  ]

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="fixed z-50 bg-bael-surface border border-bael-border rounded-lg shadow-xl py-1 min-w-[180px]"
        style={{ left: x, top: y }}
      >
        {items.map((item, i) =>
          item.divider ? (
            <div key={i} className="border-t border-bael-border my-1" />
          ) : (
            <button
              key={i}
              onClick={() => { onAction(item.action!, node); onClose() }}
              className={clsx(
                'w-full flex items-center gap-2 px-3 py-1.5 text-sm transition-colors',
                item.danger
                  ? 'text-bael-error hover:bg-bael-error/10'
                  : 'text-bael-text hover:bg-bael-border/50'
              )}
            >
              <item.icon size={14} />
              {item.label}
            </button>
          )
        )}
      </motion.div>
    </>
  )
}

// Main File Browser Component
export function FileBrowser() {
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['/']))
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [openTabs, setOpenTabs] = useState<FileTab[]>([])
  const [activeTab, setActiveTab] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: FileNode } | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentPath, setCurrentPath] = useState('/Volumes/SSD320/BaelTheLordOfAll-AI')

  // Load file tree
  const loadFileTree = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/v1/files/list?path=${encodeURIComponent(currentPath)}`)
      if (response.ok) {
        const data = await response.json()
        setFileTree(data.files || [])
      } else {
        // Fallback with mock data for development
        setFileTree([
          {
            name: 'core',
            path: `${currentPath}/core`,
            type: 'directory',
            children: [
              { name: 'singularity', path: `${currentPath}/core/singularity`, type: 'directory' },
              { name: 'brain', path: `${currentPath}/core/brain`, type: 'directory' },
              { name: 'memory', path: `${currentPath}/core/memory`, type: 'directory' },
            ]
          },
          {
            name: 'api',
            path: `${currentPath}/api`,
            type: 'directory',
            children: [
              { name: 'server.py', path: `${currentPath}/api/server.py`, type: 'file', size: 2053 },
              { name: 'singularity_api.py', path: `${currentPath}/api/singularity_api.py`, type: 'file', size: 920 },
            ]
          },
          {
            name: 'ui',
            path: `${currentPath}/ui`,
            type: 'directory',
          },
          { name: 'requirements.txt', path: `${currentPath}/requirements.txt`, type: 'file', size: 512 },
          { name: 'README.md', path: `${currentPath}/README.md`, type: 'file', size: 3421 },
          { name: 'Makefile', path: `${currentPath}/Makefile`, type: 'file', size: 1854 },
        ])
      }
    } catch (error) {
      console.error('Failed to load file tree:', error)
    }
    setIsLoading(false)
  }, [currentPath])

  useEffect(() => {
    loadFileTree()
  }, [loadFileTree])

  // Load file content
  const loadFile = async (node: FileNode) => {
    // Check if already open
    const existingTab = openTabs.find(t => t.path === node.path)
    if (existingTab) {
      setActiveTab(node.path)
      return
    }

    try {
      const response = await fetch(`/api/v1/files/read?path=${encodeURIComponent(node.path)}`)
      let content = ''

      if (response.ok) {
        const data = await response.json()
        content = data.content || ''
      } else {
        content = `// Failed to load file: ${node.path}\n// API not available in development mode`
      }

      const newTab: FileTab = {
        path: node.path,
        name: node.name,
        content,
        isDirty: false,
        language: getLanguage(node.name)
      }

      setOpenTabs(prev => [...prev, newTab])
      setActiveTab(node.path)
    } catch (error) {
      console.error('Failed to load file:', error)
    }
  }

  // Save file
  const saveFile = async (path: string) => {
    const tab = openTabs.find(t => t.path === path)
    if (!tab) return

    try {
      await fetch('/api/v1/files/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, content: tab.content })
      })

      setOpenTabs(prev => prev.map(t =>
        t.path === path ? { ...t, isDirty: false } : t
      ))
    } catch (error) {
      console.error('Failed to save file:', error)
    }
  }

  // Toggle folder expansion
  const toggleExpand = (path: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  // Handle file selection
  const handleSelect = (node: FileNode) => {
    setSelectedPath(node.path)
    if (node.type === 'file') {
      loadFile(node)
    }
  }

  // Handle context menu
  const handleContextMenu = (e: React.MouseEvent, node: FileNode) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, node })
  }

  // Handle context menu actions
  const handleAction = async (action: string, node: FileNode) => {
    switch (action) {
      case 'open':
      case 'edit':
        if (node.type === 'file') loadFile(node)
        break
      case 'copyPath':
        navigator.clipboard.writeText(node.path)
        break
      case 'delete':
        if (confirm(`Delete ${node.name}?`)) {
          await fetch(`/api/v1/files/delete?path=${encodeURIComponent(node.path)}`, { method: 'DELETE' })
          loadFileTree()
        }
        break
      case 'download':
        // Create download link
        const a = document.createElement('a')
        a.href = `/api/v1/files/download?path=${encodeURIComponent(node.path)}`
        a.download = node.name
        a.click()
        break
    }
  }

  // Close tab
  const closeTab = (path: string) => {
    const tab = openTabs.find(t => t.path === path)
    if (tab?.isDirty && !confirm('Unsaved changes. Close anyway?')) {
      return
    }

    setOpenTabs(prev => prev.filter(t => t.path !== path))
    if (activeTab === path) {
      const remaining = openTabs.filter(t => t.path !== path)
      setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].path : null)
    }
  }

  // Update tab content
  const updateTabContent = (path: string, content: string) => {
    setOpenTabs(prev => prev.map(t =>
      t.path === path ? { ...t, content, isDirty: true } : t
    ))
  }

  // Handle file upload
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    for (const file of Array.from(files)) {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const content = event.target?.result as string
        await fetch('/api/v1/files/write', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: `${currentPath}/${file.name}`,
            content
          })
        })
        loadFileTree()
      }
      reader.readAsText(file)
    }
  }

  const activeTabData = openTabs.find(t => t.path === activeTab)

  return (
    <div className="flex h-full bg-bael-bg">
      {/* Sidebar - File Tree */}
      <div className="w-72 border-r border-bael-border flex flex-col bg-bael-surface">
        {/* Header */}
        <div className="p-3 border-b border-bael-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-bael-text flex items-center gap-2">
              <HardDrive size={16} /> Files
            </h3>
            <div className="flex items-center gap-1">
              <label className="p-1.5 hover:bg-bael-border rounded cursor-pointer transition-colors">
                <Upload size={14} className="text-bael-muted" />
                <input type="file" multiple onChange={handleUpload} className="hidden" />
              </label>
              <button
                onClick={loadFileTree}
                className="p-1.5 hover:bg-bael-border rounded transition-colors"
              >
                <RefreshCw size={14} className={clsx('text-bael-muted', isLoading && 'animate-spin')} />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-bael-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="w-full bg-bael-bg border border-bael-border rounded-lg pl-8 pr-3 py-1.5 text-sm text-bael-text placeholder:text-bael-muted outline-none focus:border-bael-primary/50"
            />
          </div>
        </div>

        {/* Breadcrumb */}
        <div className="px-3 py-2 border-b border-bael-border flex items-center gap-1 text-xs text-bael-muted overflow-x-auto">
          <button
            onClick={() => setCurrentPath('/Volumes/SSD320/BaelTheLordOfAll-AI')}
            className="hover:text-bael-text transition-colors"
          >
            <Home size={12} />
          </button>
          <ChevronRight size={10} />
          <span className="text-bael-text truncate">BaelTheLordOfAll-AI</span>
        </div>

        {/* File Tree */}
        <div className="flex-1 overflow-y-auto py-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw size={20} className="animate-spin text-bael-muted" />
            </div>
          ) : (
            fileTree.map((node) => (
              <TreeNode
                key={node.path}
                node={node}
                expanded={expanded}
                onToggle={toggleExpand}
                onSelect={handleSelect}
                selectedPath={selectedPath}
                onContextMenu={handleContextMenu}
              />
            ))
          )}
        </div>
      </div>

      {/* Main Content - Editor */}
      <div className="flex-1 flex flex-col">
        {/* Tabs */}
        <div className="flex items-center bg-bael-surface border-b border-bael-border overflow-x-auto">
          {openTabs.map((tab) => (
            <div
              key={tab.path}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 border-r border-bael-border cursor-pointer transition-colors min-w-0',
                activeTab === tab.path
                  ? 'bg-bael-bg text-bael-text'
                  : 'text-bael-muted hover:bg-bael-bg/50'
              )}
              onClick={() => setActiveTab(tab.path)}
            >
              <FileIcon node={{ name: tab.name, path: tab.path, type: 'file' }} />
              <span className="text-sm truncate max-w-[120px]">{tab.name}</span>
              {tab.isDirty && <span className="w-2 h-2 rounded-full bg-amber-400" />}
              <button
                onClick={(e) => { e.stopPropagation(); closeTab(tab.path) }}
                className="p-0.5 hover:bg-bael-border rounded transition-colors"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>

        {/* Editor Area */}
        <div className="flex-1 relative">
          {activeTabData ? (
            <>
              {/* Toolbar */}
              <div className="absolute top-0 right-0 z-10 flex items-center gap-1 p-2">
                <button
                  onClick={() => saveFile(activeTabData.path)}
                  disabled={!activeTabData.isDirty}
                  className={clsx(
                    'flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors',
                    activeTabData.isDirty
                      ? 'bg-bael-primary text-white hover:bg-bael-primary/80'
                      : 'bg-bael-border text-bael-muted cursor-not-allowed'
                  )}
                >
                  <Save size={14} />
                  Save
                </button>
              </div>

              {/* Editor */}
              <SimpleEditor
                content={activeTabData.content}
                language={activeTabData.language}
                onChange={(content) => updateTabContent(activeTabData.path, content)}
              />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-bael-muted">
              <FileText size={48} className="mb-4 opacity-50" />
              <p>Select a file to edit</p>
              <p className="text-sm mt-1">or drag and drop files to upload</p>
            </div>
          )}
        </div>
      </div>

      {/* Context Menu */}
      <AnimatePresence>
        {contextMenu && (
          <ContextMenu
            x={contextMenu.x}
            y={contextMenu.y}
            node={contextMenu.node}
            onClose={() => setContextMenu(null)}
            onAction={handleAction}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

export default FileBrowser
