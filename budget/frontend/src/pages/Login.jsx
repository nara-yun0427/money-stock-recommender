import { useState } from 'react'
import { api, ApiError } from '../api'

export default function Login({ onSuccess }) {
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    if (!pin) return
    setLoading(true)
    setError('')
    try {
      await api.login(pin)
      onSuccess()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '로그인에 실패했습니다.')
      setPin('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="login-title">내 가계부</div>
        <div className="login-sub">PIN을 입력하세요</div>
        <input
          className="login-input"
          type="password"
          inputMode="numeric"
          autoFocus
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="••••"
        />
        {error && <div className="login-error">{error}</div>}
        <button className="login-btn" type="submit" disabled={loading || !pin}>
          {loading ? '확인 중...' : '입장하기'}
        </button>
      </form>
    </div>
  )
}
