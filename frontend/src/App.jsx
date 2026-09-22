import { useEffect, useState, useCallback } from 'react'
import './App.css'

const KEYWORDS = [
  { key: '단타', label: '단타' },
  { key: '스윙', label: '스윙' },
  { key: '3개월이상', label: '3개월+' },
  { key: '6개월이상', label: '6개월+' },
  { key: '1년이상', label: '1년+' },
  { key: '3년이상', label: '3년+' },
]

const METRIC_LABELS = {
  ret5: '5일',
  ret20: '20일',
  ret60: '60일',
  ret120: '120일',
  ret250: '1년',
  vol20: '변동성',
  mdd250: '최대낙폭',
  vol_ratio: '거래량비',
  swing_pullback: '저점근접도',
  swing_amplitude: '스윙폭',
  above_ma120: '120일선대비',
  avg_trading_value_5d: '최근거래대금',
  avg_volume_5d: '최근거래량',
  runup_6m: '6개월최대상승',
  mdd_6m: '6개월최대하락',
}

const RAW_PCT_KEYS = new Set(['swing_pullback'])
const CURRENCY_KEYS = new Set(['avg_trading_value_5d'])
const COUNT_KEYS = new Set(['avg_volume_5d'])

function formatPct(v) {
  if (v === null || v === undefined) return '-'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v}%`
}

function StatusBanner({ status, onRefresh }) {
  if (!status) return null
  if (status.state === 'ready') {
    return (
      <div className="banner banner-ok">
        데이터 기준: {status.built_at ? new Date(status.built_at).toLocaleString('ko-KR') : '-'} · 종목 풀{' '}
        {status.universe_size ?? '-'}개
        <button className="link-btn" onClick={onRefresh}>새로고침</button>
      </div>
    )
  }
  if (status.state === 'building') {
    return (
      <div className="banner banner-wait">
        시세 데이터를 준비 중입니다… {status.progress ?? 0}%
      </div>
    )
  }
  return (
    <div className="banner banner-error">
      데이터가 아직 없습니다.
      <button className="link-btn" onClick={onRefresh}>지금 구축하기</button>
    </div>
  )
}

function StockCard({ item }) {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-name">{item.name}</div>
          <div className="card-sub">{item.code} · {item.market}</div>
        </div>
        <div className="card-score">{item.score}</div>
      </div>
      <div className="card-reason">{item.reason}</div>
      <div className="card-metrics">
        {Object.entries(item.metrics)
          .filter(([, v]) => v !== null && v !== undefined)
          .map(([k, v]) => (
            <span key={k} className={`metric ${typeof v === 'number' && v > 0 && k !== 'mdd250' ? 'pos' : typeof v === 'number' && v < 0 ? 'neg' : ''}`}>
              {METRIC_LABELS[k] ?? k}{' '}
              {k === 'vol_ratio'
                ? `${v}x`
                : CURRENCY_KEYS.has(k)
                  ? `${v.toLocaleString('ko-KR')}억`
                  : COUNT_KEYS.has(k)
                    ? `${v.toLocaleString('ko-KR')}주`
                    : RAW_PCT_KEYS.has(k)
                      ? `${v}%`
                      : formatPct(v)}
            </span>
          ))}
      </div>
      <div className="card-price">현재가 {item.close.toLocaleString('ko-KR')}원</div>
    </div>
  )
}

export default function App() {
  const [status, setStatus] = useState(null)
  const [keyword, setKeyword] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/status')
      const data = await res.json()
      setStatus(data)
      return data
    } catch {
      setStatus({ state: 'error' })
      return null
    }
  }, [])

  useEffect(() => {
    loadStatus()
    const id = setInterval(loadStatus, 5000)
    return () => clearInterval(id)
  }, [loadStatus])

  const pick = useCallback(async (kw) => {
    setKeyword(kw)
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch(`/api/recommend?keyword=${encodeURIComponent(kw)}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `요청 실패 (${res.status})`)
      }
      const data = await res.json()
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const forceRefresh = useCallback(async () => {
    await fetch('/api/refresh', { method: 'POST' })
    loadStatus()
  }, [loadStatus])

  const dataReady = status?.state === 'ready'

  return (
    <div className="app">
      <header className="header">
        <h1>국내주식 추천</h1>
        <p className="subtitle">투자 기간을 고르면 조건에 맞는 종목을 보여드려요</p>
      </header>

      <StatusBanner status={status} onRefresh={forceRefresh} />

      <div className="keyword-row">
        {KEYWORDS.map((k) => (
          <button
            key={k.key}
            className={`chip ${keyword === k.key ? 'chip-active' : ''}`}
            disabled={!dataReady || loading}
            onClick={() => pick(k.key)}
          >
            {k.label}
          </button>
        ))}
      </div>

      {loading && <div className="loading">종목을 고르는 중…</div>}
      {error && <div className="banner banner-error">{error}</div>}

      {result && (
        <div className="result">
          <div className="result-desc">{result.desc}</div>
          <div className="card-list">
            {result.items.map((item) => (
              <StockCard key={item.code} item={item} />
            ))}
          </div>
          {result.items.length === 0 && (
            <div className="empty">조건에 맞는 종목을 찾지 못했어요.</div>
          )}
        </div>
      )}

      <footer className="disclaimer">
        본 추천은 과거 가격·거래량 데이터를 기반으로 한 정량 스크리너 결과이며,
        투자 조언이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.
      </footer>
    </div>
  )
}
