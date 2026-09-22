import dayjs from 'dayjs'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { formatWon } from '../utils'

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

export default function TrendChart({ trend, period }) {
  const tickFormatter = (label) => {
    if (period === 'year') return label
    if (period === 'week') return WEEKDAY_LABELS[dayjs(label).day()]
    const day = Number(label.slice(-2))
    return day % 5 === 0 || day === 1 ? String(day) : ''
  }

  return (
    <ResponsiveContainer width="100%" height={140}>
      <AreaChart data={trend} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="label"
          tickFormatter={tickFormatter}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={{ stroke: '#29344d' }}
          tickLine={false}
          interval={0}
        />
        <Tooltip
          formatter={(value) => formatWon(value)}
          contentStyle={{ background: '#1a2540', border: '1px solid #29344d', borderRadius: 8 }}
          labelStyle={{ color: '#e5e7eb' }}
        />
        <Area type="monotone" dataKey="amount" stroke="#22c55e" fill="url(#trendFill)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
