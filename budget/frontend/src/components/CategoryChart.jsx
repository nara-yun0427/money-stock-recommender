import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { formatWon } from '../utils'

export default function CategoryChart({ byCategory, total }) {
  if (!byCategory.length) {
    return <div className="empty-state">이 기간에 기록된 지출이 없어요.</div>
  }

  return (
    <div className="category-chart">
      <div className="donut-wrap">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={byCategory}
              dataKey="amount"
              nameKey="name"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={2}
              stroke="none"
            >
              {byCategory.map((c) => (
                <Cell key={c.category_id} fill={c.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatWon(value)}
              contentStyle={{ background: '#1a2540', border: '1px solid #29344d', borderRadius: 8 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <div className="donut-total">{formatWon(total)}</div>
          <div className="donut-label">총 지출</div>
        </div>
      </div>

      <ul className="category-legend">
        {byCategory.map((c) => (
          <li key={c.category_id} className="legend-row">
            <span className="legend-dot" style={{ background: c.color }} />
            <span className="legend-name">
              {c.icon} {c.name}
            </span>
            <span className="legend-pct">{c.pct}%</span>
            <span className="legend-amount">{formatWon(c.amount)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
