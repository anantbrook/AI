import { useState, useEffect, useRef } from 'react'

const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

const QUICK_CMDS = ['npm run dev', 'npm install', 'npm run build', 'python main.py', 'git status', 'git log --oneline -5', 'ls', 'dir']

export default function Terminal({ project }) {
  const [output, setOutput] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const [height, setHeight] = useState(200)
  const wsRef = useRef(null)
  const outRef = useRef(null)
  const history = useRef([])
  const histIdx = useRef(-1)
  const resizing = useRef(false)

  const connect = (cwd) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(`${WS_BASE}/ws/terminal`)
    wsRef.current = ws
    ws.onopen = () => ws.send(JSON.stringify({ cwd: cwd || '' }))
    ws.onmessage = e => {
      const d = JSON.parse(e.data)
      if (d.type === 'ready') {
        setConnected(true)
        if (cwd) ws.send(JSON.stringify({ type: 'input', text: `cd "${cwd}"\r` }))
      } else if (d.type === 'output') {
        setOutput(o => [...o.slice(-400), d.text])
        setTimeout(() => outRef.current?.scrollTo(0, outRef.current.scrollHeight), 10)
      }
    }
    ws.onclose = ws.onerror = () => setConnected(false)
  }

  useEffect(() => {
    connect(project?.path)
    return () => wsRef.current?.close()
  }, [project?.path])

  const sendCmd = (cmd) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) { connect(project?.path); return }
    wsRef.current.send(JSON.stringify({ type: 'input', text: cmd + '\r' }))
  }

  const onKey = (e) => {
    if (e.key === 'Enter') {
      if (input.trim()) { history.current.unshift(input); histIdx.current = -1 }
      sendCmd(input); setInput('')
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const i = histIdx.current + 1
      if (i < history.current.length) { histIdx.current = i; setInput(history.current[i]) }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      const i = histIdx.current - 1
      if (i < 0) { histIdx.current = -1; setInput('') }
      else { histIdx.current = i; setInput(history.current[i]) }
    } else if (e.ctrlKey && e.key === 'c') {
      sendCmd('\x03')
    }
  }

  // Resize
  const onResizeDown = (e) => {
    resizing.current = true
    const startY = e.clientY, startH = height
    const onMove = (e) => { if (resizing.current) setHeight(Math.max(80, Math.min(600, startH + startY - e.clientY))) }
    const onUp = () => { resizing.current = false; window.removeEventListener('mousemove', onMove) }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp, { once: true })
  }

  return (
    <div className="bg-bg0 border-t border-border flex-shrink-0 flex flex-col" style={{ height }}>
      {/* Resize bar */}
      <div className="h-1 hover:bg-accent/30 cursor-ns-resize flex-shrink-0 transition-colors" onMouseDown={onResizeDown} />

      {/* Header */}
      <div className="flex items-center justify-between px-3 h-8 bg-bg1 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Terminal</span>
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green' : 'bg-red'}`} />
          {!connected && (
            <button onClick={() => connect(project?.path)} className="text-xs text-accent hover:underline">reconnect</button>
          )}
        </div>
        <div className="flex items-center gap-1">
          {QUICK_CMDS.slice(0, 4).map(cmd => (
            <button key={cmd} onClick={() => sendCmd(cmd)}
              className="text-xs font-mono text-gray-500 hover:text-white bg-bg2 hover:bg-bg3 px-1.5 py-0.5 rounded border border-border transition-all">
              {cmd}
            </button>
          ))}
          <button onClick={() => setOutput([])} className="text-xs text-gray-500 hover:text-white px-1.5 ml-1">Clear</button>
        </div>
      </div>

      {/* Output */}
      <div ref={outRef} className="flex-1 overflow-y-auto px-3 py-1 font-mono text-xs text-gray-300 leading-5" style={{ minHeight: 0 }}>
        {output.length === 0 ? (
          <span className="text-gray-600">Terminal ready. {project ? `Working in: ${project.path}` : 'Open a project first.'}</span>
        ) : (
          output.map((o, i) => <span key={i} className="whitespace-pre-wrap break-all">{o}</span>)
        )}
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-t border-border flex-shrink-0">
        <span className="text-green font-mono text-sm flex-shrink-0">❯</span>
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey}
          className="flex-1 bg-transparent text-white font-mono text-xs outline-none select-text"
          placeholder="Run a command..." spellCheck={false} />
      </div>
    </div>
  )
}
