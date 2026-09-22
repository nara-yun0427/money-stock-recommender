import { useEffect, useState } from 'react'
import './App.css'
import { api } from './api'
import Dashboard from './pages/Dashboard.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'

export default function App() {
  const [authState, setAuthState] = useState('checking') // checking | out | in
  const [categories, setCategories] = useState([])
  const [tab, setTab] = useState('home')

  useEffect(() => {
    api
      .checkAuth()
      .then((res) => setAuthState(res.authenticated ? 'in' : 'out'))
      .catch(() => setAuthState('out'))
  }, [])

  useEffect(() => {
    if (authState === 'in') {
      api.listCategories().then(setCategories).catch(() => {})
    }
  }, [authState])

  if (authState === 'checking') {
    return <div className="splash">불러오는 중...</div>
  }

  if (authState === 'out') {
    return <Login onSuccess={() => setAuthState('in')} />
  }

  async function logout() {
    await api.logout()
    setAuthState('out')
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span>내 가계부</span>
        <button className="logout-btn" onClick={logout}>
          로그아웃
        </button>
      </header>
      <main className="app-main">
        {tab === 'home' ? <Home categories={categories} /> : <Dashboard />}
      </main>
      <nav className="tab-bar">
        <button className={`tab-btn${tab === 'home' ? ' active' : ''}`} onClick={() => setTab('home')}>
          홈
        </button>
        <button
          className={`tab-btn${tab === 'dashboard' ? ' active' : ''}`}
          onClick={() => setTab('dashboard')}
        >
          대시보드
        </button>
      </nav>
    </div>
  )
}
