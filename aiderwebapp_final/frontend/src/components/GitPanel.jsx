export default function GitPanel({ data }) {
  if (!data) return null
  const statusLines = (data.status || '').split('\n').filter(Boolean)
  const logLines = (data.log || '').split('\n').filter(Boolean)
  const clr = s => s === 'M' ? 'text-yellow' : s === '?' ? 'text-red' : s === 'A' ? 'text-green' : 'text-gray-400'

  return (
    <div className="border-t border-border bg-bg0 max-h-44 overflow-y-auto flex-shrink-0">
      <div className="px-3 py-1.5 border-b border-border flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Git</span>
        {data.branch && <span className="text-xs text-accent bg-accent/10 px-1.5 py-0.5 rounded">⎇ {data.branch}</span>}
      </div>
      {statusLines.length > 0 && (
        <div className="px-3 py-1">
          <div className="text-xs text-gray-600 mb-0.5">Changes</div>
          {statusLines.map((l, i) => (
            <div key={i} className={`text-xs font-mono py-0.5 ${clr(l[0])}`}>
              <span className="opacity-60 mr-1">{l[0]}</span>{l.slice(3)}
            </div>
          ))}
        </div>
      )}
      {logLines.length > 0 && (
        <div className="px-3 py-1 border-t border-border">
          <div className="text-xs text-gray-600 mb-0.5">Commits</div>
          {logLines.map((l, i) => (
            <div key={i} className="text-xs font-mono text-gray-400 py-0.5 truncate">{l}</div>
          ))}
        </div>
      )}
      {!statusLines.length && !logLines.length && (
        <div className="px-3 py-2 text-xs text-gray-600">No git info</div>
      )}
    </div>
  )
}
