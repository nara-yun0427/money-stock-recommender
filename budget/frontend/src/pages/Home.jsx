import { useEffect, useState } from 'react'
import { api } from '../api'
import QuickAddSheet from '../components/QuickAddSheet.jsx'
import { PAYMENT_METHOD_LABELS, formatWon } from '../utils'

export default function Home({ categories }) {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingTx, setEditingTx] = useState(null)

  async function refresh() {
    setLoading(true)
    try {
      const data = await api.listTransactions({ limit: 30 })
      setTransactions(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleDelete(id) {
    if (editingTx?.id === id) setEditingTx(null)
    await api.deleteTransaction(id)
    refresh()
  }

  function handleSaved() {
    setEditingTx(null)
    refresh()
  }

  return (
    <div className="home-page">
      <QuickAddSheet
        categories={categories}
        editingTx={editingTx}
        onSaved={handleSaved}
        onCancelEdit={() => setEditingTx(null)}
      />

      <div className="section-title">최근 내역</div>
      {loading ? (
        <div className="empty-state">불러오는 중...</div>
      ) : transactions.length === 0 ? (
        <div className="empty-state">아직 기록된 지출이 없어요.</div>
      ) : (
        <ul className="tx-list">
          {transactions.map((t) => (
            <li key={t.id} className="tx-item">
              <button className="tx-main" onClick={() => setEditingTx(t)}>
                <span className="tx-icon" style={{ background: `${t.category.color}26`, color: t.category.color }}>
                  {t.category.icon}
                </span>
                <span className="tx-info">
                  <span className="tx-category">{t.category.name}</span>
                  <span className="tx-meta">
                    {t.date} · {PAYMENT_METHOD_LABELS[t.payment_method]}
                    {t.memo ? ` · ${t.memo}` : ''}
                  </span>
                </span>
                <span className="tx-amount">{formatWon(t.amount)}</span>
              </button>
              <button className="tx-delete" onClick={() => handleDelete(t.id)} aria-label="삭제">
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
