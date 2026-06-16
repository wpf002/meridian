import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

// Scan any ticker in the market — navigates to its full scan.
export default function SearchBox() {
  const [value, setValue] = useState('')
  const navigate = useNavigate()

  const submit = (e) => {
    e.preventDefault()
    const ticker = value.trim().toUpperCase()
    if (ticker) {
      navigate(`/asset/${ticker}`)
      setValue('')
    }
  }

  return (
    <form onSubmit={submit} className="flex-1 max-w-md">
      <label className="flex items-center gap-2 chip w-full focus-within:border-green/50">
        <span className="text-muted">⌕</span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Scan any ticker…"
          spellCheck={false}
          autoComplete="off"
          className="flex-1 bg-transparent outline-none text-ink placeholder:text-faint font-mono text-sm uppercase"
        />
      </label>
    </form>
  )
}
