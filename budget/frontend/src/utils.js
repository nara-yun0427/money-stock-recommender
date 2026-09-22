export const PAYMENT_METHOD_LABELS = {
  credit_card: '신용카드',
  debit_card: '체크카드',
  cash: '현금',
}

const won = new Intl.NumberFormat('ko-KR')

export function formatWon(amount) {
  return `${won.format(amount)}원`
}

export function formatSignedWon(amount) {
  if (amount > 0) return `+${won.format(amount)}원`
  if (amount < 0) return `${won.format(amount)}원`
  return '변동 없음'
}

export function formatPct(pct) {
  if (pct === null || pct === undefined) return '-'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct}%`
}

export function todayISO() {
  const d = new Date()
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d - tz).toISOString().slice(0, 10)
}
