import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

// MAS/TAS/SAS are positive contributors; SRS is a risk penalty (shown red).
const COLORS = { MAS: '#34d399', TAS: '#22d3ee', SAS: '#7c93ff', SRS: '#f87171' }
const LABELS = {
  MAS: 'Macro', TAS: 'Tactical', SAS: 'Sentiment', SRS: 'Struct. Risk',
}
// component code -> weights dict key
const WEIGHT_KEY = { MAS: 'macro', TAS: 'tactical', SAS: 'sentiment', SRS: 'structural_risk' }

export default function AcsComponentsChart({ components, weights }) {
  const data = [
    { name: 'MAS', value: components.mas },
    { name: 'TAS', value: components.tas },
    { name: 'SAS', value: components.sas },
    { name: 'SRS', value: components.srs },
  ]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <XAxis
          dataKey="name"
          stroke="#8a93a6"
          tickLine={false}
          tickFormatter={(n) => LABELS[n] || n}
          fontSize={12}
        />
        <YAxis domain={[0, 1]} stroke="#8a93a6" tickLine={false} fontSize={12} />
        <ReferenceLine y={0} stroke="#222a39" />
        <Tooltip
          cursor={{ fill: '#222a3955' }}
          contentStyle={{ background: '#121722', border: '1px solid #222a39', borderRadius: 8 }}
          labelStyle={{ color: '#e6e9ef' }}
          formatter={(v, _n, p) => {
            const w = weights?.[WEIGHT_KEY[p.payload.name]]
            return [`${v.toFixed(3)}${w != null ? `  (weight ${w})` : ''}`, LABELS[p.payload.name]]
          }}
        />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={COLORS[d.name]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
