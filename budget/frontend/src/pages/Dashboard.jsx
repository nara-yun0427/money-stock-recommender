import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { api } from '../api'
import CategoryChart from '../components/CategoryChart.jsx'
import PaymentMethodChart from '../components/PaymentMethodChart.jsx'
import TrendChart from '../components/TrendChart.jsx'
import { formatPct, formatSignedWon } from '../utils'

const PERIODS = [
  { value: 'week', label: '주간' },
  { value: 'month', label: '월간' },
  { value: 'year', label: '연간' },
]

function shiftRef(refDate, period, dir) {
  const unit = period === 'week' ? 'week' : period === 'month' ? 'month' : 'year'
  return dayjs(refDate).add(dir, unit).format('YYYY-MM-DD')
}

function rangeLabel(summary) {
  if (!summary) return ''
  const { period, range } = summary
  const start = dayjs(range.start)
  if (period === 'week') return `${start.format('M/D')} ~ ${dayjs(range.end).format('M/D')}`
  if (period === 'month') return start.format('YYYY년 M월')
  return start.format('YYYY년')
}

function ComparisonCard({ comparison }) {
  if (!comparison) return null
  const positive = comparison.diff_amount > 0
  return (
    <div className={`comparison-card${positive ? ' up' : comparison.diff_amount < 0 ? ' down' : ''}`}>
      <div className="comparison-label">{comparison.label} 대비</div>
      <div className="comparison-value">{formatSignedWon(comparison.diff_amount)}</div>
      <div className="comparison-pct">{formatPct(comparison.diff_pct)}</div>
    </div>
  )
}

export default function Dashboard() {
  const [period, setPeriod] = useState('month')
  const [refDate, setRefDate] = useState(dayjs().format('YYYY-MM-DD'))
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .dashboardSummary(period, refDate)
      .then((data) => {
        if (!cancelled) setSummary(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '불러오기에 실패했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [period, refDate])

  function changePeriod(p) {
    setPeriod(p)
  }

  return (
    <div className="dashboard-page">
      <div className="period-tabs">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            className={`period-tab${period === p.value ? ' active' : ''}`}
            onClick={() => changePeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="range-nav">
        <button className="nav-btn" onClick={() => setRefDate(shiftRef(refDate, period, -1))}>
          ‹
        </button>
        <span className="range-label">{rangeLabel(summary)}</span>
        <button className="nav-btn" onClick={() => setRefDate(shiftRef(refDate, period, 1))}>
          ›
        </button>
      </div>

      {loading && <div className="empty-state">불러오는 중...</div>}
      {error && <div className="form-error">{error}</div>}

      {summary && !loading && (
        <>
          <div className="comparison-row">
            <ComparisonCard comparison={summary.comparison_prev} />
            {summary.comparison_last_year && <ComparisonCard comparison={summary.comparison_last_year} />}
          </div>

          <div className="dashboard-card">
            <div className="card-title">지출 추이</div>
            <TrendChart trend={summary.trend} period={period} />
          </div>

          <div className="dashboard-card">
            <div className="card-title">카테고리별 지출</div>
            <CategoryChart byCategory={summary.by_category} total={summary.total} />
          </div>

          <div className="dashboard-card">
            <div className="card-title">결제수단별 지출</div>
            <PaymentMethodChart byPaymentMethod={summary.by_payment_method} />
          </div>
        </>
      )}
    </div>
  )
}
