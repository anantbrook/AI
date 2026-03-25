import { useState, useEffect, useRef } from 'react'
import FileTree from './components/FileTree'
import AgentChat from './components/AgentChat'
import Terminal from './components/Terminal'
import GitPanel from './components/GitPanel'
import ProjectPicker from './components/ProjectPicker'
import Settings from './components/Settings'

export default function App() {
  const [projects, setProjects]         = useState([])
  const [activeTab, setActiveTab]       = useState(0)
  const [cloudModels, setCloudModels]   = useState([])
  const [localModels, setLocalModels]   = useState([])
  const [model, setModel]               = useState('ollama/qwen3-coder:480b-cloud')
  const [ollamaOnline, setOllamaOnline] = useState(false)
  const [showTerminal, setShowTerminal] = useState(true)
  const [showFiles, setShowFiles]       = useState(true)
  const [showGit, setShowGit]           = useState(false)
  const [showPicker, setShowPicker]     = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [gitData, setGitData]           = useState(null)
  const [projectStats, setProjectStats] = useState(null)
  const [sidebarW, setSidebarW]         = useState(220)
  const resizing = useRef(false)

  const project = projects[activeTab] || null

  // Load saved projects once on mount
  useEffect(() => {
    fetch('/api/projects').then(r => r.json()).then(d => {
      if (Array.isArray(d) && d.length > 0) setProjects(d)
    }).catch(err => console.error('Error loading projects:', err))
  }, [])

  // Poll Ollama status + model list every 10s
  useEffect(() => {
    const check = () =>
      fetch('/api/models').then(r => r.json()).then(d => {
        setOllamaOnline(d.online !== false)
        setCloudModels(d.cloud || [])
        setLocalModels(d.local  || [])
        // Auto-select first cloud model if current model is a local one
        const firstCloud = (d.cloud || [])[0]
        if (firstCloud && !model.includes('cloud')) {
          setModel(`ollama/${firstCloud}`)
        }
      }).catch(() => setOllamaOnline(false))
    check()
    const t = setInterval(check, 10000)
    return () => clearInterval(t)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Persist projects list to backend
  useEffect(() => {
    if (projects.length > 0) {
      fetch('/api/projects', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(projects),
      }).catch(err => console.error('Error persisting projects:', err))
    }
  }, [projects])

  // Load git + stats whenever the active project changes
  useEffect(() => {
    if (!project) { setGitData(null); setProjectStats(null); return }
    fetch(`/api/git/status?path=${encodeURIComponent(project.path)}`).then(r => r.json()).then(setGitData).catch(err => console.error('Error fetching git status:', err))
    fetch(`/api/scan?path=${encodeURIComponent(project.path)}`).then(r => r.json()).then(setProjectStats).catch(err => console.error('Error scanning project:', err))
  }, [project?.path])

  // Sidebar resize listeners
  useEffect(() => {
    const onMove = e => { if (resizing.current) setSidebarW(Math.max(160, Math.min(480, e.clientX))) }
    const onUp   = () => { resizing.current = false; document.body.style.cursor = '' }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup',   onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [])

  const openProject = p => {
    const idx = projects.findIndex(x => x.path === p.path)
    if (idx >= 0) { setActiveTab(idx); setShowPicker(false); return }
    const next = [...projects, p]
    setProjects(next)
    setActiveTab(next.length - 1)
    setShowPicker(false)
  }

  const removeProject = (i, e) => {
    e.stopPropagation()
    const next = [...projects]
    next.splice(i, 1)
    setProjects(next)
    setActiveTab(Math.min(activeTab, Math.max(0, next.length - 1)))
  }

  const refreshModels = () =>
    fetch('/api/models').then(r => r.json()).then(d => {
      setCloudModels(d.cloud || [])
      setLocalModels(d.local  || [])
    })

  const isLocal = !model.includes('cloud') && model !== ''

  return (
    <div className="flex flex-col h-screen bg-bg0 overflow-hidden select-none">

      {/* ── TITLE BAR ──────────────────────────── */}
      <div className="h-10 flex items-center gap-2 px-3 bg-bg1 border-b border-border flex-shrink-0 z-20">
        <span className="text-accent text-xl">⬡</span>
        <span className="font-bold text-sm text-white mr-1">AiderWeb</span>

        {/* Project tabs */}
        <div className="flex items-end gap-0.5 flex-1 h-full overflow-x-auto">
          {projects.map((p, i) => (
            <div key={i}
              onClick={() => { setActiveTab(i); setProjectStats(null); setGitData(null) }}
              className={`relative flex items-center gap-1.5 px-3 h-8 mt-2 rounded-t border border-b-0
                cursor-pointer text-xs whitespace-nowrap group flex-shrink-0 transition-all
                ${i === activeTab
                  ? 'bg-bg0 border-border text-white'
                  : 'bg-bg2 border-border/40 text-gray-400 hover:text-white hover:bg-bg3'}`}>
              <span>📁</span>
              <span>{p.name}</span>
              <button onClick={e => removeProject(i, e)}
                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red ml-0.5">✕</button>
              {i === activeTab && <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent rounded-full" />}
            </div>
          ))}
          <button onClick={() => setShowPicker(true)}
            className="flex items-center justify-center w-7 h-7 mt-2 rounded border border-border
              text-gray-400 hover:text-white hover:bg-bg3 hover:border-accent/50 text-lg transition-all flex-shrink-0"
            title="Open project">+</button>
        </div>

        {/* Right-side controls */}
        <div className="flex items-center gap-1.5 flex-shrink-0">

          {/* File count + type badge */}
          {projectStats && (
            <div className="hidden md:flex items-center gap-1 text-xs text-gray-500 bg-bg2 border border-border px-2 py-1 rounded">
              <span>📋 {projectStats.count}</span>
              <span className="text-gray-700">·</span>
              <span className="text-accent">{projectStats.type}</span>
            </div>
          )}

          {/* Git branch */}
          {gitData?.branch && (
            <button onClick={() => setShowGit(g => !g)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded border transition-all
                ${showGit ? 'bg-accent/20 border-accent/50 text-accent' : 'border-border text-gray-400 hover:text-white'}`}>
              ⎇ {gitData.branch}
              {(gitData.status || '').trim() && <span className="w-1.5 h-1.5 rounded-full bg-yellow" />}
            </button>
          )}

          {/* Ollama status dot */}
          <div className="flex items-center gap-1.5 px-2 py-1 bg-bg2 border border-border rounded text-xs">
            <div className={`w-2 h-2 rounded-full transition-all
              ${ollamaOnline ? 'bg-green shadow-[0_0_4px_#3fb950]' : 'bg-red'}`} />
            <span className="text-gray-400 hidden sm:inline">{ollamaOnline ? 'Ollama' : 'Offline'}</span>
          </div>

          {/* Model selector — cloud models first, local models last with warning */}
          <select value={model} onChange={e => setModel(e.target.value)}
            className="hidden sm:block bg-bg2 border border-border text-white text-xs px-2 py-1 rounded outline-none cursor-pointer max-w-[190px]">
            {cloudModels.length > 0 ? (
              <optgroup label="☁ Cloud (no storage)">
                {cloudModels.map(m => <option key={m} value={`ollama/${m}`}>⭐ {m}</option>)}
              </optgroup>
            ) : (
              <>
                <option value="ollama/qwen3-coder:480b-cloud">⭐ qwen3-coder:480b-cloud</option>
                <option value="ollama/deepseek-v3.1:671b-cloud">⭐ deepseek-v3.1:671b-cloud</option>
              </>
            )}
            {localModels.length > 0 && (
              <optgroup label="⚠ Local (delete in Settings)">
                {localModels.map(m => <option key={m} value={`ollama/${m}`}>⚠ {m}</option>)}
              </optgroup>
            )}
          </select>

          {/* Warn badge when a local model is selected */}
          {isLocal && (
            <span className="hidden md:inline text-xs text-yellow bg-yellow/10 border border-yellow/30 px-2 py-1 rounded">
              ⚠ Local
            </span>
          )}

          <button onClick={() => setShowFiles(f => !f)}
            className="hidden md:block text-xs px-2 py-1 border border-border text-gray-400 hover:text-white rounded transition-all">
            {showFiles ? '◀' : '▶'} Files
          </button>

          <button onClick={() => setShowTerminal(t => !t)}
            className="hidden md:block text-xs px-2 py-1 border border-border text-gray-400 hover:text-white rounded transition-all">
            {showTerminal ? '▼' : '▲'} Term
          </button>

          <button onClick={() => setShowSettings(true)}
            className="w-7 h-7 flex items-center justify-center border border-border text-gray-400 hover:text-white hover:bg-bg3 rounded transition-all">
            ⚙
          </button>
        </div>
      </div>

      {/* ── MAIN LAYOUT ────────────────────────── */}
      <div className="flex flex-1 overflow-hidden min-h-0">

        {showFiles && (
          <>
            <div className="flex flex-col bg-bg1 border-r border-border flex-shrink-0"
              style={{ width: sidebarW }}>
              <div className="flex items-center px-3 py-2 border-b border-border flex-shrink-0">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider truncate">
                  {project?.name || 'Explorer'}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto min-h-0">
                {project ? (
                  <FileTree root={project.path} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full gap-3 p-5 text-center">
                    <div className="text-4xl">📁</div>
                    <p className="text-gray-500 text-xs">No project open</p>
                    <button onClick={() => setShowPicker(true)}
                      className="px-3 py-1.5 bg-accent/20 border border-accent/50 text-accent rounded-lg text-xs hover:bg-accent hover:text-bg0 transition-all">
                      Open Project
                    </button>
                  </div>
                )}
              </div>
              {showGit && gitData && <GitPanel data={gitData} />}
            </div>

            {/* Resize handle */}
            <div className="w-0.5 hover:w-1 bg-transparent hover:bg-accent/30 cursor-col-resize flex-shrink-0 transition-all"
              onMouseDown={() => { resizing.current = true; document.body.style.cursor = 'col-resize' }} />
          </>
        )}

        <div className="flex-1 flex flex-col overflow-hidden min-w-0 min-h-0">
          <AgentChat project={project} model={model} ollamaOnline={ollamaOnline} />
          {showTerminal && <Terminal project={project} />}
        </div>
      </div>

      {/* ── MODALS ─────────────────────────────── */}
      {showPicker   && <ProjectPicker onSelect={openProject} onClose={() => setShowPicker(false)} />}
      {showSettings && (
        <Settings
          model={model}
          localModels={localModels}
          onModelChange={setModel}
          onClose={() => setShowSettings(false)}
          onModelsRefresh={refreshModels}
        />
      )}
    </div>
  )
}
