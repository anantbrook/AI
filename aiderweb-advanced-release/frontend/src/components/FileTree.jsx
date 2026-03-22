import { useState, useEffect } from 'react'

const ICONS = {
  '.js':'📜','.jsx':'⚛','.ts':'📘','.tsx':'⚛','.py':'🐍',
  '.html':'🌐','.css':'🎨','.scss':'🎨','.json':'📋','.md':'📝',
  '.txt':'📄','.sh':'⚡','.bat':'⚡','.env':'🔑',
  '.png':'🖼','.jpg':'🖼','.svg':'🖼',
  '.sql':'🗄','.toml':'⚙','.yaml':'⚙','.yml':'⚙',
}

function Node({ item, depth }) {
  const [open, setOpen] = useState(depth < 1)
  const [children, setChildren] = useState([])
  const [loaded, setLoaded] = useState(false)

  const toggle = async () => {
    if (!item.isDir) return
    if (!loaded) {
      const r = await fetch(`/api/fs/list?path=${encodeURIComponent(item.path)}`)
      const d = await r.json()
      setChildren(d.items || [])
      setLoaded(true)
    }
    setOpen(o => !o)
  }

  useEffect(() => {
    if (item.isDir && depth < 1 && !loaded) {
      fetch(`/api/fs/list?path=${encodeURIComponent(item.path)}`)
        .then(r => r.json()).then(d => { setChildren(d.items || []); setLoaded(true) })
        .catch(() => {})
    }
  }, [])

  const icon = item.isDir ? (open ? '📂' : '📁') : (ICONS[item.ext] || '📄')

  return (
    <div>
      <div
        onClick={toggle}
        className={`flex items-center gap-1.5 py-0.5 text-xs rounded transition-colors
          ${item.isDir ? 'text-gray-300 hover:text-white cursor-pointer hover:bg-bg3' : 'text-gray-400 cursor-default'}`}
        style={{ paddingLeft: `${8 + depth * 12}px` }}
      >
        <span className="text-sm flex-shrink-0">{icon}</span>
        <span className="truncate">{item.name}</span>
      </div>
      {open && item.isDir && children.map(c => (
        <Node key={c.path} item={c} depth={depth + 1} />
      ))}
    </div>
  )
}

export default function FileTree({ root }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    fetch(`/api/fs/list?path=${encodeURIComponent(root)}`)
      .then(r => r.json()).then(d => setItems(d.items || []))
      .catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [root])

  if (loading) return (
    <div className="flex items-center justify-center py-8">
      <div className="spinner w-4 h-4 border-2 border-border border-t-accent rounded-full" />
    </div>
  )

  return (
    <div className="py-1">
      <div className="flex items-center justify-between px-2 py-1 mb-1">
        <span className="text-xs text-gray-600 italic">AI reads all files automatically</span>
        <button onClick={load} className="text-xs text-gray-500 hover:text-white px-1 transition-colors" title="Refresh">↻</button>
      </div>
      {items.map(item => <Node key={item.path} item={item} depth={0} />)}
    </div>
  )
}
