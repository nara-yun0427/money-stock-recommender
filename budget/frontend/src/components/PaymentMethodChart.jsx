import { PAYMENT_METHOD_LABELS, formatWon } from '../utils'

export default function PaymentMethodChart({ byPaymentMethod }) {
  return (
    <div className="payment-chart">
      {byPaymentMethod.map((m) => (
        <div key={m.method} className="payment-row">
          <div className="payment-row-head">
            <span>{PAYMENT_METHOD_LABELS[m.method]}</span>
            <span className="payment-row-nums">
              {formatWon(m.amount)} · {m.pct}%{' '}
              <span className="payment-target">(목표 {m.target_pct}%)</span>
            </span>
          </div>
          <div className="payment-bar-track">
            <div className="payment-bar-fill" style={{ width: `${Math.min(m.pct, 100)}%` }} />
            <div className="payment-bar-target" style={{ left: `${Math.min(m.target_pct, 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
