import { useState, useEffect } from 'react'

const DEFAULT_PROJECTS = [
  { name: 'my-all-project-', path: 'C:\\my all project which ii build\\my-all-project-' },
  { name: 'aisuite',         path: 'C:\\my all project which ii build\\aisuite' },
  { name: 'ai-suite-v8fix',  path: 'C:\\my all project which ii build\\New folder\\ai-suite-v8fix' },
  { name: 'autobot',         path: 'C:\\Users\\Annad\\Downloads\\autobot' },
  { name: 'QRMark-4',        path: 'C:\\my all project which ii build\\QRMark-4' },
  { name: 'CYouTube_Auto',   path: 'C:\\CYouTube_Auto' },
  { name: 'mediavault_fixed',path: 'C:\\Users\\Annad\\Downloads\\mediavault_fixed' },
]

export default function ProjectPicker({ onSelect, onClose }) {
  const [customPath, setCustomPath] = useState('')
  const [recent, setRecent] = useState([])
  const [checking, setChecking] = useState(null)

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('recent_paths') || '[]')
      setRecent(saved)
    } catch {}
  }, [])

  const pick = async (name, path) => {
    setChecking(path)
    // Verify path exists via API
    try {
      const r = await fetch(`/api/fs/list?path=${encodeURIComponent(path)}`)
      const d = await r.json()
      if (d.error) {
        alert(`Folder not found:\n${path}\n\nMake sure the path exists.`)
        setChecking(null)
        return
      }
    } catch {
      setChecking(null)
      return
    }

    // Save to recent
    try {
      const saved = JSON.parse(localStorage.getItem('recent_paths') || '[]')
      const next = [{ name, path }, ...saved.filter(p => p.path !== path)].slice(0, 5)
      localStorage.setItem('recent_paths', JSON.stringify(next))
    } catch {}

    setChecking(null)
    onSelect({ name, path })
  }

  const handleCustom = () => {
    if (!customPath.trim()) return
    const name = customPath.trim().split(/[\\/]/).pop() || 'project'
    pick(name, customPath.trim())
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 animate-in p-4">
      <div className="bg-bg1 border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h2 className="text-base font-semibold text-white">Open Project</h2>
            <p className="text-xs text-gray-500 mt-0.5">Select a folder to work on</p>
          </div>
          <button onClick={onClose}
            className="w-7 h-7 rounded-lg bg-bg3 text-gray-400 hover:text-white hover:bg-red/20 hover:border-red/50 border border-transparent transition-all text-sm">
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">

          {/* Recent projects */}
          {recent.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Recent</div>
              <div className="space-y-1">
                {recent.map((p, i) => (
                  <button key={i} onClick={() => pick(p.name, p.path)}
                    disabled={checking === p.path}
                    className="w-full flex items-center gap-3 px-3 py-2.5 bg-bg2 hover:bg-bg3 border border-border hover:border-accent/50 rounded-lg transition-all text-left group">
                    <span className="text-lg">🕐</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white group-hover:text-accent transition-colors">{p.name}</div>
                      <div className="text-xs text-gray-500 truncate">{p.path}</div>
                    </div>
                    {checking === p.path
                      ? <div className="spinner w-4 h-4 border-2 border-border border-t-accent rounded-full flex-shrink-0" />
                      : <span className="text-gray-600 group-hover:text-accent text-xs">→</span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Your projects */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Your Projects</div>
            <div className="space-y-1">
              {DEFAULT_PROJECTS.map((p, i) => (
                <button key={i} onClick={() => pick(p.name, p.path)}
                  disabled={checking === p.path}
                  className="w-full flex items-center gap-3 px-3 py-2.5 bg-bg2 hover:bg-bg3 border border-border hover:border-accent/50 rounded-lg transition-all text-left group">
                  <span className="text-lg">📁</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white group-hover:text-accent transition-colors">{p.name}</div>
                    <div className="text-xs text-gray-500 truncate">{p.path}</div>
                  </div>
                  {checking === p.path
                    ? <div className="spinner w-4 h-4 border-2 border-border border-t-accent rounded-full flex-shrink-0" />
                    : <span className="text-gray-600 group-hover:text-accent text-xs">→</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Custom path */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Custom Path</div>
            <div className="flex gap-2">
              <input
                value={customPath}
                onChange={e => setCustomPath(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCustom()}
                placeholder="C:\path\to\your\project"
                className="flex-1 bg-bg2 border border-border rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-accent transition-colors placeholder-gray-600 select-text font-mono"
              />
              <button onClick={handleCustom}
                disabled={!customPath.trim() || !!checking}
                className="px-4 py-2 bg-accent hover:bg-accent/80 disabled:bg-bg3 disabled:text-gray-600 text-white rounded-lg text-sm font-medium transition-all">
                Open
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
