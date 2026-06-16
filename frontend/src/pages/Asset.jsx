import { useParams, Link } from 'react-router-dom'

export default function Asset() {
  const { ticker } = useParams()
  return (
    <div>
      <Link to="/" className="text-muted text-sm hover:text-ink">← Recommendations</Link>
      <h1 className="text-2xl font-bold mt-2 mb-4 font-mono">{ticker}</h1>
      <div className="card p-6 text-muted">Asset detail — coming in M1.</div>
    </div>
  )
}
