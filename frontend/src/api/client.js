import axios from 'axios'

// Same-origin in dev via the Vite proxy; override with VITE_API_BASE for a
// separately-hosted backend.
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || '/api' })

export default api

export const getStatus = () => api.get('/status').then((r) => r.data)
export const getHealth = () => api.get('/health').then((r) => r.data)
export const getUniverse = () => api.get('/universe').then((r) => r.data)
export const addAsset = (ticker, name, sector) =>
  api.post('/universe', null, { params: { ticker, name: name || ticker, sector } }).then((r) => r.data)
export const removeAsset = (ticker) => api.delete(`/universe/${ticker}`).then((r) => r.data)
export const getRecommendations = () => api.get('/recommend').then((r) => r.data)
export const getScan = (ticker) => api.get(`/scan/${ticker}`).then((r) => r.data)
export const getPortfolio = () => api.get('/portfolio').then((r) => r.data)
export const compareAssets = (a, b) =>
  api.get('/compare', { params: { a, b } }).then((r) => r.data)
export const getScenarios = () => api.get('/scenarios').then((r) => r.data)
export const runScenario = (name) =>
  api.post(`/scenario/${encodeURIComponent(name)}`).then((r) => r.data)
export const getBrief = () => api.get('/brief').then((r) => r.data)
export const getRegime = () => api.get('/regime').then((r) => r.data)
export const getAlerts = () => api.get('/alerts').then((r) => r.data)
export const ackAlert = (id) => api.post(`/alerts/${id}/ack`).then((r) => r.data)
