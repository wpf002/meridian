import {
  BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'

// MAS/TAS/SAS are positive contributors; SRS is a risk penalty (shown red).
const COLORS = { MAS: '#26e3a0', TAS: '#39b6f6', SAS: '#8ad0ff', SRS: '#ff6b7a' }
const LABELS = {
  MAS: 'Macro', TAS: 'Price Trend', SAS: 'News', SRS: 'Risk',
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
          stroke="#5d7689"
          tickLine={false}
          tickFormatter={(n) => LABELS[n] || n}
          fontSize={12}
        />
        <YAxis domain={[0, 1]} stroke="#5d7689" tickLine={false} fontSize={12} />
        <ReferenceLine y={0} stroke="#15303d" />
        <Tooltip
          cursor={{ fill: '#0b192540' }}
          contentStyle={{ background: '#08111a', border: '1px solid #15303d', borderRadius: 8 }}
          labelStyle={{ color: '#dceaf0' }}
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
