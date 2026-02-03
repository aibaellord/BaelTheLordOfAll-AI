import { useState, useEffect, createContext, useContext } from 'react'
import {
  Folder,
  FolderOpen,
  Plus,
  Settings,
  Trash2,
  Edit3,
  Save,
  X,
  Copy,
  Download,
  Upload,
  Star,
  StarOff,
  ChevronDown,
  Check,
  Archive,
  Clock,
  MessageSquare,
  Database,
  Key,
  Palette,
  Globe
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import clsx from 'clsx'

// Types
export interface Project {
  id: string
  name: string
  description: string
  icon: string
  color: string
  createdAt: number
  updatedAt: number
  starred: boolean
  archived: boolean
  settings: ProjectSettings
  stats: ProjectStats
}

interface ProjectSettings {
  model: string
  temperature: number
  maxTokens: number
  systemPrompt: string
  persona: string | null
  memoryEnabled: boolean
  autoSave: boolean
}

interface ProjectStats {
  messages: number
  tokens: number
  files: number
  lastActive: number
}

// IndexedDB for projects
const DB_NAME = 'bael-projects'
const DB_VERSION = 1
const STORE_NAME = 'projects'

const openDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
  })
}

const saveProject = async (project: Project) => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).put(project)
}

const loadProjects = async (): Promise<Project[]> => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readonly')
  const request = tx.objectStore(STORE_NAME).getAll()
  return new Promise((resolve) => {
    request.onsuccess = () => resolve(request.result || [])
  })
}

const deleteProjectFromDB = async (id: string) => {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).delete(id)
}

// Default project settings
const defaultSettings: ProjectSettings = {
  model: 'anthropic/claude-3.5-sonnet',
  temperature: 0.7,
  maxTokens: 4096,
  systemPrompt: '',
  persona: null,
  memoryEnabled: true,
  autoSave: true
}

// Available colors
const projectColors = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316',
  '#f59e0b', '#84cc16', '#22c55e', '#14b8a6', '#06b6d4'
]

// Available icons
const projectIcons = ['🚀', '💡', '🎯', '📚', '🔬', '🎨', '⚡', '🌟', '🔥', '💎']

// Context for current project
interface ProjectContextType {
  currentProject: Project | null
  setCurrentProject: (project: Project | null) => void
  projects: Project[]
  createProject: (data: Partial<Project>) => Promise<Project>
  updateProject: (id: string, data: Partial<Project>) => Promise<void>
  deleteProject: (id: string) => Promise<void>
}

const ProjectContext = createContext<ProjectContextType | null>(null)

export const useProjects = () => {
  const context = useContext(ProjectContext)
  if (!context) throw new Error('useProjects must be used within ProjectProvider')
  return context
}

// Provider Component
export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [currentProject, setCurrentProject] = useState<Project | null>(null)

  useEffect(() => {
    loadProjects().then(loaded => {
      setProjects(loaded)
      // Load last active project
      const lastActive = localStorage.getItem('bael-current-project')
      if (lastActive) {
        const project = loaded.find(p => p.id === lastActive)
        if (project) setCurrentProject(project)
      }
    })
  }, [])

  useEffect(() => {
    if (currentProject) {
      localStorage.setItem('bael-current-project', currentProject.id)
    }
  }, [currentProject])

  const createProject = async (data: Partial<Project>): Promise<Project> => {
    const project: Project = {
      id: `proj-${Date.now()}`,
      name: data.name || 'New Project',
      description: data.description || '',
      icon: data.icon || projectIcons[Math.floor(Math.random() * projectIcons.length)],
      color: data.color || projectColors[Math.floor(Math.random() * projectColors.length)],
      createdAt: Date.now(),
      updatedAt: Date.now(),
      starred: false,
      archived: false,
      settings: { ...defaultSettings, ...data.settings },
      stats: { messages: 0, tokens: 0, files: 0, lastActive: Date.now() }
    }
    await saveProject(project)
    setProjects(prev => [...prev, project])
    return project
  }

  const updateProject = async (id: string, data: Partial<Project>) => {
    const project = projects.find(p => p.id === id)
    if (!project) return

    const updated = { ...project, ...data, updatedAt: Date.now() }
    await saveProject(updated)
    setProjects(prev => prev.map(p => p.id === id ? updated : p))
    if (currentProject?.id === id) setCurrentProject(updated)
  }

  const deleteProject = async (id: string) => {
    await deleteProjectFromDB(id)
    setProjects(prev => prev.filter(p => p.id !== id))
    if (currentProject?.id === id) setCurrentProject(null)
  }

  return (
    <ProjectContext.Provider value={{
      currentProject,
      setCurrentProject,
      projects,
      createProject,
      updateProject,
      deleteProject
    }}>
      {children}
    </ProjectContext.Provider>
  )
}

// Project Switcher Component (for header)
export function ProjectSwitcher() {
  const { currentProject, setCurrentProject, projects, createProject } = useProjects()
  const [isOpen, setIsOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)

  const activeProjects = projects.filter(p => !p.archived)
  const starredProjects = activeProjects.filter(p => p.starred)
  const otherProjects = activeProjects.filter(p => !p.starred)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-bael-bg border border-bael-border rounded-lg hover:border-bael-primary/50 transition-colors"
      >
        {currentProject ? (
          <>
            <span
              className="w-5 h-5 rounded flex items-center justify-center text-xs"
              style={{ backgroundColor: currentProject.color + '20', color: currentProject.color }}
            >
              {currentProject.icon}
            </span>
            <span className="text-sm text-bael-text max-w-[120px] truncate">
              {currentProject.name}
            </span>
          </>
        ) : (
          <>
            <Folder size={16} className="text-bael-muted" />
            <span className="text-sm text-bael-muted">No Project</span>
          </>
        )}
        <ChevronDown size={14} className="text-bael-muted" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute left-0 top-full mt-2 w-72 bg-bael-surface border border-bael-border rounded-xl shadow-xl z-50 overflow-hidden"
            >
              {/* Header */}
              <div className="p-3 border-b border-bael-border flex items-center justify-between">
                <span className="text-sm font-medium text-bael-text">Projects</span>
                <button
                  onClick={() => setShowCreate(true)}
                  className="p-1.5 hover:bg-bael-border rounded-lg transition-colors"
                >
                  <Plus size={14} className="text-bael-muted" />
                </button>
              </div>

              {/* Project List */}
              <div className="max-h-80 overflow-y-auto">
                {/* No Project Option */}
                <button
                  onClick={() => { setCurrentProject(null); setIsOpen(false) }}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2.5 transition-colors',
                    !currentProject ? 'bg-bael-primary/10' : 'hover:bg-bael-border/50'
                  )}
                >
                  <Globe size={16} className="text-bael-muted" />
                  <span className="text-sm">Global (No Project)</span>
                  {!currentProject && <Check size={14} className="ml-auto text-bael-primary" />}
                </button>

                {/* Starred */}
                {starredProjects.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-xs text-bael-muted uppercase tracking-wide">
                      Starred
                    </div>
                    {starredProjects.map(project => (
                      <ProjectItem
                        key={project.id}
                        project={project}
                        isActive={currentProject?.id === project.id}
                        onSelect={() => { setCurrentProject(project); setIsOpen(false) }}
                      />
                    ))}
                  </>
                )}

                {/* Other Projects */}
                {otherProjects.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-xs text-bael-muted uppercase tracking-wide">
                      Projects
                    </div>
                    {otherProjects.map(project => (
                      <ProjectItem
                        key={project.id}
                        project={project}
                        isActive={currentProject?.id === project.id}
                        onSelect={() => { setCurrentProject(project); setIsOpen(false) }}
                      />
                    ))}
                  </>
                )}

                {activeProjects.length === 0 && (
                  <div className="px-3 py-8 text-center text-bael-muted text-sm">
                    No projects yet
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="p-2 border-t border-bael-border">
                <button
                  onClick={() => setShowCreate(true)}
                  className="w-full flex items-center justify-center gap-2 py-2 text-sm text-bael-primary hover:bg-bael-primary/10 rounded-lg transition-colors"
                >
                  <Plus size={14} />
                  Create New Project
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Create Project Modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateProjectModal
            onClose={() => setShowCreate(false)}
            onCreate={async (data) => {
              const project = await createProject(data)
              setCurrentProject(project)
              setShowCreate(false)
              setIsOpen(false)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// Project Item in Switcher
function ProjectItem({
  project,
  isActive,
  onSelect
}: {
  project: Project
  isActive: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={clsx(
        'w-full flex items-center gap-3 px-3 py-2.5 transition-colors',
        isActive ? 'bg-bael-primary/10' : 'hover:bg-bael-border/50'
      )}
    >
      <span
        className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
        style={{ backgroundColor: project.color + '20', color: project.color }}
      >
        {project.icon}
      </span>
      <div className="flex-1 text-left min-w-0">
        <p className="text-sm text-bael-text truncate">{project.name}</p>
        <p className="text-xs text-bael-muted">
          {project.stats.messages} messages
        </p>
      </div>
      {project.starred && (
        <Star size={12} className="text-amber-400 fill-amber-400" />
      )}
      {isActive && <Check size={14} className="text-bael-primary" />}
    </button>
  )
}

// Create Project Modal
function CreateProjectModal({
  onClose,
  onCreate
}: {
  onClose: () => void
  onCreate: (data: Partial<Project>) => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [icon, setIcon] = useState(projectIcons[0])
  const [color, setColor] = useState(projectColors[0])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onCreate({ name, description, icon, color })
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-bael-surface border border-bael-border rounded-xl shadow-2xl z-50"
      >
        <form onSubmit={handleSubmit}>
          <div className="p-4 border-b border-bael-border flex items-center justify-between">
            <h3 className="font-semibold text-bael-text">Create New Project</h3>
            <button type="button" onClick={onClose} className="p-1 hover:bg-bael-border rounded">
              <X size={18} />
            </button>
          </div>

          <div className="p-4 space-y-4">
            {/* Preview */}
            <div className="flex items-center gap-3 p-3 bg-bael-bg rounded-lg">
              <span
                className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl"
                style={{ backgroundColor: color + '20', color }}
              >
                {icon}
              </span>
              <div>
                <p className="font-medium text-bael-text">{name || 'Project Name'}</p>
                <p className="text-sm text-bael-muted">{description || 'Project description'}</p>
              </div>
            </div>

            {/* Name */}
            <div>
              <label className="block text-sm text-bael-muted mb-1.5">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Awesome Project"
                className="w-full bg-bael-bg border border-bael-border rounded-lg px-3 py-2 text-bael-text placeholder:text-bael-muted outline-none focus:border-bael-primary/50"
                autoFocus
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm text-bael-muted mb-1.5">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of your project..."
                rows={2}
                className="w-full bg-bael-bg border border-bael-border rounded-lg px-3 py-2 text-bael-text placeholder:text-bael-muted outline-none focus:border-bael-primary/50 resize-none"
              />
            </div>

            {/* Icon */}
            <div>
              <label className="block text-sm text-bael-muted mb-1.5">Icon</label>
              <div className="flex flex-wrap gap-2">
                {projectIcons.map((i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setIcon(i)}
                    className={clsx(
                      'w-9 h-9 rounded-lg flex items-center justify-center transition-all',
                      icon === i
                        ? 'bg-bael-primary/20 ring-2 ring-bael-primary'
                        : 'bg-bael-bg hover:bg-bael-border'
                    )}
                  >
                    {i}
                  </button>
                ))}
              </div>
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm text-bael-muted mb-1.5">Color</label>
              <div className="flex flex-wrap gap-2">
                {projectColors.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setColor(c)}
                    className={clsx(
                      'w-7 h-7 rounded-full transition-all',
                      color === c && 'ring-2 ring-offset-2 ring-offset-bael-surface'
                    )}
                    style={{ backgroundColor: c, ringColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="p-4 border-t border-bael-border flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-bael-muted hover:text-bael-text transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-4 py-2 bg-bael-primary text-white rounded-lg text-sm hover:bg-bael-primary/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create Project
            </button>
          </div>
        </form>
      </motion.div>
    </>
  )
}

// Projects Page
export function ProjectsPage() {
  const { projects, createProject, updateProject, deleteProject, setCurrentProject } = useProjects()
  const [filter, setFilter] = useState<'all' | 'starred' | 'archived'>('all')
  const [showCreate, setShowCreate] = useState(false)

  const filteredProjects = projects.filter(p => {
    if (filter === 'starred') return p.starred && !p.archived
    if (filter === 'archived') return p.archived
    return !p.archived
  })

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-bael-text">Projects</h1>
          <p className="text-bael-muted">Manage your workspaces and isolated contexts</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-bael-primary text-white rounded-lg hover:bg-bael-primary/80 transition-colors"
        >
          <Plus size={18} />
          New Project
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6">
        {(['all', 'starred', 'archived'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              'px-4 py-1.5 rounded-lg text-sm transition-colors capitalize',
              filter === f
                ? 'bg-bael-primary/20 text-bael-primary'
                : 'text-bael-muted hover:text-bael-text hover:bg-bael-border/50'
            )}
          >
            {f}
          </button>
        ))}
        <span className="text-bael-muted text-sm ml-2">
          {filteredProjects.length} project{filteredProjects.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProjects.map((project) => (
          <motion.div
            key={project.id}
            layout
            className="bg-bael-surface border border-bael-border rounded-xl p-4 hover:border-bael-primary/30 transition-colors group"
          >
            <div className="flex items-start gap-3 mb-3">
              <span
                className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                style={{ backgroundColor: project.color + '20', color: project.color }}
              >
                {project.icon}
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-bael-text truncate">{project.name}</h3>
                <p className="text-sm text-bael-muted truncate">{project.description || 'No description'}</p>
              </div>
              <button
                onClick={() => updateProject(project.id, { starred: !project.starred })}
                className="p-1 hover:bg-bael-border rounded transition-colors"
              >
                {project.starred ? (
                  <Star size={16} className="text-amber-400 fill-amber-400" />
                ) : (
                  <StarOff size={16} className="text-bael-muted" />
                )}
              </button>
            </div>

            <div className="flex items-center gap-4 text-xs text-bael-muted mb-3">
              <span className="flex items-center gap-1">
                <MessageSquare size={12} />
                {project.stats.messages}
              </span>
              <span className="flex items-center gap-1">
                <Database size={12} />
                {project.stats.tokens.toLocaleString()} tokens
              </span>
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {new Date(project.updatedAt).toLocaleDateString()}
              </span>
            </div>

            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => setCurrentProject(project)}
                className="flex-1 py-1.5 bg-bael-primary text-white text-sm rounded-lg hover:bg-bael-primary/80 transition-colors"
              >
                Open
              </button>
              <button
                onClick={() => updateProject(project.id, { archived: !project.archived })}
                className="p-1.5 hover:bg-bael-border rounded-lg transition-colors"
                title={project.archived ? 'Unarchive' : 'Archive'}
              >
                <Archive size={14} className="text-bael-muted" />
              </button>
              <button
                onClick={() => {
                  if (confirm(`Delete "${project.name}"?`)) deleteProject(project.id)
                }}
                className="p-1.5 hover:bg-bael-error/10 rounded-lg transition-colors"
                title="Delete"
              >
                <Trash2 size={14} className="text-bael-error" />
              </button>
            </div>
          </motion.div>
        ))}

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <div className="col-span-full text-center py-12">
            <FolderOpen size={48} className="mx-auto mb-4 text-bael-muted opacity-50" />
            <p className="text-bael-muted">No projects found</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-4 text-bael-primary hover:underline"
            >
              Create your first project
            </button>
          </div>
        )}
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <CreateProjectModal
            onClose={() => setShowCreate(false)}
            onCreate={async (data) => {
              await createProject(data)
              setShowCreate(false)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

export default ProjectsPage
