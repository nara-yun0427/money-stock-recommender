import { useEffect, useState } from 'react'
import { api } from '../api'
import { PAYMENT_METHOD_LABELS, todayISO } from '../utils'

const EMPTY = {
  date: todayISO(),
  amount: '',
  categoryId: null,
  paymentMethod: 'credit_card',
  memo: '',
}

export default function QuickAddSheet({ categories, editingTx, onSaved, onCancelEdit }) {
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (editingTx) {
      setForm({
        date: editingTx.date,
        amount: String(editingTx.amount),
        categoryId: editingTx.category_id,
        paymentMethod: editingTx.payment_method,
        memo: editingTx.memo || '',
      })
    }
  }, [editingTx])

  async function selectCategory(catId) {
    setForm((f) => ({ ...f, categoryId: catId }))
    if (editingTx) return
    try {
      const res = await api.defaultPaymentMethod(catId)
      if (res.payment_method) {
        setForm((f) => ({ ...f, categoryId: catId, paymentMethod: res.payment_method }))
      }
    } catch {
      // ignore — keep current selection
    }
  }

  function onAmountChange(e) {
    const digits = e.target.value.replace(/[^\d]/g, '')
    setForm((f) => ({ ...f, amount: digits }))
  }

  async function submit(e) {
    e.preventDefault()
    if (!form.categoryId || !form.amount) return
    setSaving(true)
    setError('')
    const payload = {
      date: form.date,
      amount: Number(form.amount),
      category_id: form.categoryId,
      payment_method: form.paymentMethod,
      memo: form.memo || null,
    }
    try {
      if (editingTx) {
        await api.updateTransaction(editingTx.id, payload)
      } else {
        await api.createTransaction(payload)
      }
      setForm(EMPTY)
      onSaved()
    } catch (err) {
      setError(err.message || '저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  function cancelEdit() {
    setForm(EMPTY)
    onCancelEdit()
  }

  const amountDisplay = form.amount ? Number(form.amount).toLocaleString('ko-KR') : ''

  return (
    <form className="quick-add" onSubmit={submit}>
      <div className="quick-add-row">
        <input
          className="amount-input"
          inputMode="numeric"
          placeholder="0"
          value={amountDisplay}
          onChange={onAmountChange}
        />
        <span className="amount-suffix">원</span>
      </div>

      <div className="category-grid">
        {categories.map((c) => (
          <button
            type="button"
            key={c.id}
            className={`category-chip${form.categoryId === c.id ? ' active' : ''}`}
            style={form.categoryId === c.id ? { borderColor: c.color, background: `${c.color}26` } : undefined}
            onClick={() => selectCategory(c.id)}
          >
            <span className="category-icon">{c.icon}</span>
            <span>{c.name}</span>
          </button>
        ))}
      </div>

      <div className="payment-toggle">
        {Object.entries(PAYMENT_METHOD_LABELS).map(([value, label]) => (
          <button
            type="button"
            key={value}
            className={`payment-btn${form.paymentMethod === value ? ' active' : ''}`}
            onClick={() => setForm((f) => ({ ...f, paymentMethod: value }))}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="quick-add-row secondary">
        <input
          className="date-input"
          type="date"
          value={form.date}
          onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
        />
        <input
          className="memo-input"
          type="text"
          placeholder="메모 (선택)"
          value={form.memo}
          onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))}
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="quick-add-actions">
        {editingTx && (
          <button type="button" className="btn-secondary" onClick={cancelEdit}>
            취소
          </button>
        )}
        <button
          type="submit"
          className="btn-primary"
          disabled={saving || !form.categoryId || !form.amount}
        >
          {saving ? '저장 중...' : editingTx ? '수정하기' : '기록하기'}
        </button>
      </div>
    </form>
  )
}
