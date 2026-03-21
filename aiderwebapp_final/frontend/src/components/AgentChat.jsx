import { useState, useEffect, useRef, useCallback } from 'react'

const WS_BASE = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

// Event icons for agent activity feed
const EVENT_ICONS = {
  start:  { icon: '🚀', color: 'text-accent' },
  scan:   { icon: '📂', color: 'text-yellow' },
  read:   { icon: '📖', color: 'text-gray-400' },
  think:  { icon: '🧠', color: 'text-purple' },
  edit:   { icon: '✏️', color: 'text-green' },
  cmd:    { icon: '⚡', color: 'text-yellow' },
  error:  { icon: '⚠️', color: 'text-red' },
  done:   { icon: '✅', color: 'text-green' },
}

// Format markdown-ish text
function fmt(text) {
  if (!text) return ''

  // Format <think> blocks
  text = text.replace(/<think>([\s\S]*?)<\/think>/g,
    (_, content) => `<div class="think-block my-2 border-l-2 border-purple/50 pl-3 py-2 bg-purple/5 text-gray-400 text-xs italic"><div class="font-semibold text-purple mb-1">🤔 Thoughts:</div>${esc(content.trim()).replace(/\n/g, '<br>')}</div>`
  )

  // Format <observe> blocks
  text = text.replace(/<observe>([\s\S]*?)<\/observe>/g,
    (_, content) => `<div class="observe-block my-2 border-l-2 border-blue/50 pl-3 py-2 bg-blue/5 text-gray-400 text-xs italic"><div class="font-semibold text-blue mb-1">👀 Observation:</div>${esc(content.trim()).replace(/\n/g, '<br>')}</div>`
  )

  text = text.replace(/```(\w+)?\n?([\s\S]*?)```/g,
    (_, l, c) => `<pre><code>${esc(c.trim())}</code></pre>`)
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>')
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  text = text.replace(/\n/g, '<br>')
  return text
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
}

// Agent event bubble - shows AI activity (reading files, editing, etc.)
function AgentEvent({ event }) {
  const style = EVENT_ICONS[event.event] || { icon: '•', color: 'text-gray-500' }
  return (
    <div className={`flex items-start gap-2 text-xs animate-in ${style.color} py-0.5`}>
      <span className="flex-shrink-0 mt-0.5">{style.icon}</span>
      <span className="opacity-80 break-all">{event.text}</span>
    </div>
  )
}

// Chat message bubble
function Message({ msg }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex gap-3 animate-in ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0 font-bold
        ${isUser ? 'bg-accent/20 text-accent' : 'bg-bg2 border border-border text-green'}`}>
        {isUser ? 'Y' : '⬡'}
      </div>
      <div className={`min-w-0 ${isUser ? 'max-w-[75%]' : 'flex-1'}`}>
        {/* Agent events inside AI message */}
        {msg.events?.length > 0 && (
          <div className="bg-bg2/50 border border-border/50 rounded-lg p-3 mb-2 space-y-0.5 overflow-x-auto max-h-60">
            {msg.events.map((ev, i) => <AgentEvent key={i} event={ev} />)}
          </div>
        )}

        {/* Main message content */}
        {msg.content && (
          <div className={`rounded-xl px-4 py-3 text-sm leading-relaxed
            ${isUser
              ? 'bg-accent/15 border border-accent/30 text-white'
              : 'bg-bg2 border border-border text-gray-200'
            }`}
            dangerouslySetInnerHTML={{ __html: fmt(msg.content) }}
          />
        )}

        {/* Streaming cursor */}
        {msg.streaming && !msg.content && (
          <div className="bg-bg2 border border-border rounded-xl px-4 py-3 flex items-center gap-2">
            <div className="flex gap-1">
              {[0,1,2].map(i => (
                <div key={i} className="w-1.5 h-1.5 rounded-full bg-accent pulse"
                  style={{ animationDelay: `${i*200}ms` }} />
              ))}
            </div>
            <span className="text-xs text-gray-500">Agent working...</span>
          </div>
        )}

        {/* Edited files summary */}
        {msg.editedFiles?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {msg.editedFiles.map((f, i) => (
              <span key={i} className="text-xs bg-green/10 border border-green/30 text-green px-2 py-0.5 rounded font-mono">
                ✏️ {f.split(/[\\/]/).pop()}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Suggested prompts
const SUGGESTIONS = [
  'Explain this entire project to me',
  'Find and fix all bugs',
  'Add proper error handling everywhere',
  'Add dark mode',
  'Write tests for the main functionality',
  'Refactor code to be cleaner',
  'Add loading states to UI',
  'Optimize performance',
]

export default function AgentChat({ project, model, ollamaOnline }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const [statusText, setStatusText] = useState('')
  const wsRef = useRef(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const currentMsgId = useRef(null)

  // Reset on project change
  useEffect(() => {
    setMessages([])
    setInput('')
    setRunning(false)
    setStatusText('')
  }, [project?.path])

  // Auto scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Connect WebSocket
  const getWs = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return wsRef.current
    const ws = new WebSocket(`${WS_BASE}/ws/agent`)
    wsRef.current = ws
    return ws
  }, [])

  const send = () => {
    const text = input.trim()
    if (!text || running || !project) return

    if (!ollamaOnline) {
      setMessages(m => [...m, {
        role: 'ai', content: '⚠️ **Ollama is offline.** Please start it:\n\n`ollama serve`\n\nThen try again.'
      }])
      return
    }

    setInput('')
    setRunning(true)

    // Add user message
    setMessages(m => [...m, { role: 'user', content: text }])

    // Add AI message placeholder
    const msgId = Date.now()
    currentMsgId.current = msgId
    setMessages(m => [...m, {
      id: msgId,
      role: 'ai',
      content: '',
      events: [],
      streaming: true,
      editedFiles: []
    }])

    const ws = getWs()
    let aiContent = ''
    let events = []

    const onMsg = (e) => {
      const data = JSON.parse(e.data)

      if (data.type === 'agent_event') {
        // Live agent activity (reading files, editing, etc.)
        events = [...events, { event: data.event, text: data.text }]
        setStatusText(data.text)
        setMessages(m => m.map(msg =>
          msg.id === msgId ? { ...msg, events } : msg
        ))

      } else if (data.type === 'chunk') {
        // AI text output
        aiContent += data.text
        setMessages(m => m.map(msg =>
          msg.id === msgId ? { ...msg, content: aiContent } : msg
        ))

      } else if (data.type === 'done') {
        // All done
        setMessages(m => m.map(msg =>
          msg.id === msgId ? {
            ...msg,
            streaming: false,
            editedFiles: data.edited_files || []
          } : msg
        ))
        setRunning(false)
        setStatusText('')
        ws.removeEventListener('message', onMsg)

      } else if (data.type === 'error') {
        setMessages(m => m.map(msg =>
          msg.id === msgId ? {
            ...msg,
            content: `❌ Error: ${data.text}\n\nMake sure Ollama is running and the model is downloaded.`,
            streaming: false
          } : msg
        ))
        setRunning(false)
        setStatusText('')
        ws.removeEventListener('message', onMsg)

      } else if (data.type === 'stopped') {
        setMessages(m => m.map(msg =>
          msg.id === msgId ? { ...msg, content: aiContent + '\n\n*[Stopped by user]*', streaming: false } : msg
        ))
        setRunning(false)
        setStatusText('')
        ws.removeEventListener('message', onMsg)
      }
    }

    ws.addEventListener('message', onMsg)

    const doSend = () => ws.send(JSON.stringify({
      type: 'run',
      path: project.path,
      model,
      message: text
    }))

    if (ws.readyState === WebSocket.OPEN) doSend()
    else ws.addEventListener('open', doSend, { once: true })
  }

  const stop = () => {
    wsRef.current?.send(JSON.stringify({ type: 'stop' }))
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const onInputChange = (e) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px'
  }

  const clearChat = () => setMessages([])

  return (
    <div className="flex flex-col flex-1 overflow-hidden min-h-0">

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 min-h-0">

        {messages.length === 0 ? (
          /* Welcome screen */
          <div className="flex flex-col items-center justify-center h-full text-center gap-5 py-8">
            <div className="text-6xl">⬡</div>
            <div>
              <h1 className="text-2xl font-bold text-white mb-2">
                {project?.name || 'AiderWeb'}
              </h1>
              <p className="text-gray-500 text-sm max-w-md leading-relaxed">
                {project
                  ? `AI agent with full access to your entire project. Just describe what you want — the agent reads all files automatically and makes changes.`
                  : 'Open a project folder using the + tab button above to get started.'}
              </p>
            </div>

            {project && (
              <div className="w-full max-w-lg">
                <p className="text-xs text-gray-600 mb-3 text-center">Quick start:</p>
                <div className="grid grid-cols-2 gap-2">
                  {SUGGESTIONS.map(s => (
                    <button key={s} onClick={() => setInput(s)}
                      className="text-left px-3 py-2 bg-bg2 border border-border rounded-lg text-xs text-gray-400 hover:text-white hover:border-accent/50 hover:bg-bg3 transition-all">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {!ollamaOnline && (
              <div className="flex items-center gap-2 px-4 py-2 bg-red/10 border border-red/30 rounded-lg text-xs text-red">
                <span>⚠️</span>
                <span>Ollama is offline. Run <code>ollama serve</code> to start it.</span>
              </div>
            )}
          </div>
        ) : (
          messages.map((msg, i) => <Message key={i} msg={msg} />)
        )}

        <div ref={bottomRef} />
      </div>

      {/* Status bar when running */}
      {running && statusText && (
        <div className="flex items-center gap-2 px-4 py-2 bg-bg1 border-t border-border text-xs text-gray-400">
          <div className="spinner w-3 h-3 border border-border border-t-accent rounded-full flex-shrink-0" />
          <span className="flex-1 truncate">{statusText}</span>
          <button onClick={stop}
            className="text-red hover:text-red/70 flex-shrink-0 font-medium">
            Stop
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border bg-bg1 p-3">
        <div className="flex gap-2 items-end">
          <div className={`flex-1 bg-bg2 border rounded-xl px-3 py-2.5 transition-colors
            ${running ? 'border-accent/30' : 'border-border focus-within:border-accent'}`}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={onInputChange}
              onKeyDown={onKey}
              disabled={running}
              placeholder={
                !project ? 'Open a project first using the + tab...' :
                !ollamaOnline ? 'Ollama is offline — run: ollama serve' :
                running ? 'Agent is working...' :
                'Describe what you want to build, fix, or improve... (Enter to send)'
              }
              rows={1}
              style={{ maxHeight: 180 }}
              className="w-full bg-transparent text-white text-sm outline-none resize-none placeholder-gray-600 select-text leading-relaxed"
            />
          </div>

          <button
            onClick={running ? stop : send}
            disabled={!project && !running}
            className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold transition-all flex-shrink-0
              ${running
                ? 'bg-red/20 border border-red/50 text-red hover:bg-red hover:text-white'
                : 'bg-accent hover:bg-accent/80 text-white disabled:bg-bg3 disabled:text-gray-600 disabled:cursor-not-allowed'
              }`}
          >
            {running ? '■' : '▲'}
          </button>
        </div>

        <div className="flex items-center justify-between mt-2 px-1">
          <div className="flex items-center gap-2 text-xs text-gray-600">
            <span>⬡ Reads entire project automatically</span>
            {project && <span>· {project.path.split(/[\\/]/).pop()}</span>}
          </div>
          <button onClick={clearChat} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
            Clear
          </button>
        </div>
      </div>
    </div>
  )
}
