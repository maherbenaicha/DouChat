import { useCallback, useEffect, useState } from 'react'
import { api, tokenStore } from './api'
import Chat from './components/Chat'
import Documents from './components/Documents'
import Login from './components/Login'
import Users from './components/Users'
import type { User } from './types'

type Tab = 'chat' | 'documents' | 'users'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('chat')

  const loadMe = useCallback(async () => {
    if (!tokenStore.get()) {
      setLoading(false)
      return
    }
    try {
      setUser(await api<User>('/auth/me'))
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMe()
    const onLogout = () => setUser(null)
    window.addEventListener('docuchat:logout', onLogout)
    return () => window.removeEventListener('docuchat:logout', onLogout)
  }, [loadMe])

  const logout = () => {
    tokenStore.set(null)
    setUser(null)
    setTab('chat')
  }

  if (loading) return <div className="center muted">Chargement…</div>
  if (!user) return <Login onLogin={loadMe} />

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span> DocuChat
        </div>
        <nav className="tabs">
          <button className={tab === 'chat' ? 'active' : ''} onClick={() => setTab('chat')}>
            Assistant
          </button>
          <button className={tab === 'documents' ? 'active' : ''} onClick={() => setTab('documents')}>
            Documents
          </button>
          {user.role === 'admin' && (
            <button className={tab === 'users' ? 'active' : ''} onClick={() => setTab('users')}>
              Utilisateurs
            </button>
          )}
        </nav>
        <div className="user">
          <span className="muted">{user.full_name || user.email}</span>
          {user.role === 'admin' ? (
            <span className="badge admin">admin</span>
          ) : (
            user.groups.map((g) => (
              <span key={g} className="badge">
                {g}
              </span>
            ))
          )}
          <button className="ghost" onClick={logout}>
            Déconnexion
          </button>
        </div>
      </header>
      <main className="content">
        {tab === 'chat' && <Chat />}
        {tab === 'documents' && <Documents user={user} />}
        {tab === 'users' && user.role === 'admin' && <Users currentUser={user} />}
      </main>
    </div>
  )
}
