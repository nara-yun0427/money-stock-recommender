const BASE = '/api'

class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'same-origin',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    ...options,
  })
  if (res.status === 401) {
    throw new ApiError(401, '로그인이 필요합니다.')
  }
  if (!res.ok) {
    let message = `요청에 실패했습니다. (${res.status})`
    try {
      const data = await res.json()
      if (data?.detail) message = data.detail
    } catch {
      // ignore
    }
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  checkAuth: () => request('/auth/check'),
  login: (pin) => request('/auth/login', { method: 'POST', body: JSON.stringify({ pin }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),

  listCategories: () => request('/categories'),

  listTransactions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/transactions${qs ? `?${qs}` : ''}`)
  },
  createTransaction: (payload) =>
    request('/transactions', { method: 'POST', body: JSON.stringify(payload) }),
  updateTransaction: (id, payload) =>
    request(`/transactions/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteTransaction: (id) => request(`/transactions/${id}`, { method: 'DELETE' }),
  defaultPaymentMethod: (categoryId) =>
    request(`/transactions/default-payment-method?category_id=${categoryId}`),

  dashboardSummary: (period, refDate) =>
    request(`/dashboard/summary?period=${period}&ref_date=${refDate}`),
}

export { ApiError }
