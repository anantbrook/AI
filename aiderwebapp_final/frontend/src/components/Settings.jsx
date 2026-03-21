import { useState } from 'react'

export default function Settings({ model, localModels, onModelChange, onClose, onModelsRefresh }) {
  const [mapTokens,  setMapTokens]  = useState(localStorage.getItem('map_tokens')     || '4096')
  const [autoCommit, setAutoCommit] = useState(localStorage.getItem('auto_commit')    === 'true')
  const [aiderArgs,  setAiderArgs]  = useState(localStorage.getItem('aider_extra_args') || '')
  const [deleting,   setDeleting]   = useState(false)
  const [deleteMsg,  setDeleteMsg]  = useState('')

  const save = () => {
    localStorage.setItem('map_tokens',      mapTokens)
    localStorage.setItem('auto_commit',     autoCommit)
    localStorage.setItem('aider_extra_args', aiderArgs)
    onClose()
  }

  const deleteLocal = async () => {
    if (!localModels.length) return
    const ok = confirm(
      `Delete ${localModels.length} local model(s)?\n\n${localModels.join('\n')}\n\nThis frees ~14 GB of disk space.`
    )
    if (!ok) return
    setDeleting(true)
    setDeleteMsg('')
    try {
      const r = await fetch('/api/models/local', { method: 'DELETE' })
      const d = await r.json()
      if (d.ok) {
        setDeleteMsg(`✅ Deleted: ${d.deleted.join(', ')}`)
        onModelsRefresh()
        // If current model was local, switch to cloud default
        if (model && !model.includes('cloud')) {
          onModelChange('ollama/qwen3-coder:480b-cloud')
        }
      } else {
        setDeleteMsg(`⚠️ Some failed: ${d.failed.join(', ')}`)
      }
    } catch {
      setDeleteMsg('❌ Failed — is Ollama running?')
    }
    setDeleting(false)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 animate-in p-4">
      <div className="bg-bg1 border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-white">⚙ Settings</h2>
          <button onClick={onClose}
            className="w-7 h-7 rounded-lg bg-bg3 text-gray-400 hover:text-white transition-all text-sm">✕</button>
        </div>

        <div className="p-5 space-y-5">

          {/* Delete local models */}
          <div className="bg-bg2 border border-border rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-white">Local Models</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {localModels.length > 0
                    ? `${localModels.length} installed — using ~${localModels.length * 5}–10 GB disk`
                    : 'No local models installed ✅'}
                </div>
              </div>
              {localModels.length > 0 && (
                <button
                  onClick={deleteLocal}
                  disabled={deleting}
                  className="px-3 py-1.5 bg-red/20 border border-red/50 text-red text-xs rounded-lg
                    hover:bg-red hover:text-white transition-all disabled:opacity-50 font-medium flex-shrink-0">
                  {deleting ? 'Deleting...' : '🗑 Delete All'}
                </button>
              )}
            </div>
            {localModels.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {localModels.map(m => (
                  <span key={m} className="text-xs bg-bg3 border border-border px-2 py-0.5 rounded font-mono text-yellow">
                    ⚠ {m}
                  </span>
                ))}
              </div>
            )}
            {deleteMsg && (
              <p className="text-xs text-gray-400">{deleteMsg}</p>
            )}
          </div>

          {/* Repo map tokens */}
          <div>
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
              Repo Map Tokens
            </label>
            <select value={mapTokens} onChange={e => setMapTokens(e.target.value)}
              className="w-full bg-bg2 border border-border text-white px-3 py-2 rounded-lg text-sm outline-none focus:border-accent">
              <option value="1024">1024 — Light (faster)</option>
              <option value="2048">2048 — Medium</option>
              <option value="4096">4096 — Full (recommended)</option>
              <option value="8192">8192 — Maximum (big projects)</option>
            </select>
            <p className="text-xs text-gray-600 mt-1">How much of your project the AI reads automatically</p>
          </div>

          {/* Auto commit toggle */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-white">Auto Git Commit</div>
              <div className="text-xs text-gray-500">Commit changes automatically after each edit</div>
            </div>
            <button onClick={() => setAutoCommit(a => !a)}
              className={`w-12 h-6 rounded-full transition-all relative ${autoCommit ? 'bg-accent' : 'bg-bg3 border border-border'}`}>
              <div className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-all ${autoCommit ? 'left-7' : 'left-1'}`} />
            </button>
          </div>

          {/* Extra aider args */}
          <div>
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">
              Extra Aider Arguments
            </label>
            <input value={aiderArgs} onChange={e => setAiderArgs(e.target.value)}
              placeholder="e.g. --no-git --architect"
              className="w-full bg-bg2 border border-border text-white px-3 py-2 rounded-lg text-sm outline-none focus:border-accent font-mono placeholder-gray-600 select-text" />
            <p className="text-xs text-gray-600 mt-1">Advanced: extra flags passed to Aider</p>
          </div>

          {/* Info */}
          <div className="bg-bg2 border border-border rounded-lg p-3 text-xs text-gray-500 space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-accent">ℹ</span>
              <span className="font-medium text-gray-400">How it works</span>
            </div>
            <p>AiderWeb uses <strong className="text-gray-300">Aider</strong> with Ollama <strong className="text-gray-300">cloud models</strong> — no storage needed, runs on Ollama's servers.</p>
            <p>The AI builds a <strong className="text-gray-300">repo-map</strong> of your entire project and decides what to change based on your request.</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-2 px-5 pb-5">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 bg-bg2 border border-border text-gray-400 hover:text-white rounded-lg text-sm transition-all">
            Cancel
          </button>
          <button onClick={save}
            className="flex-1 px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg text-sm font-medium transition-all">
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
