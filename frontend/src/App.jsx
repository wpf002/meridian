import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Recommendations from './pages/Recommendations.jsx'
import Asset from './pages/Asset.jsx'
import Portfolio from './pages/Portfolio.jsx'
import Scenarios from './pages/Scenarios.jsx'
import Status from './pages/Status.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Recommendations />} />
        <Route path="/asset/:ticker" element={<Asset />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/scenarios" element={<Scenarios />} />
        <Route path="/status" element={<Status />} />
      </Route>
    </Routes>
  )
}
