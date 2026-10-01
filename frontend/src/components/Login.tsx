import { useState, type FormEvent } from 'react'
import { api, tokenStore } from '../api'

const DEMO = [
  { label: 'Admin', email: 'admin@docuchat.local', password: 'admin123' },
  { label: 'Alice (RH)', email: 'alice@docuchat.local', password: 'demo1234' },
  { label: 'Bob (Tech)', email: 'bob@docuchat.local', password: 'demo1234' },
  { label: 'Chloé (stagiaire)', email: 'chloe@docuchat.local', password: 'demo1234' },
]

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const { access_token } = await api<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      tokenStore.set(access_token)
      onLogin()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de connexion')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <h1>
          <span className="logo">◆</span> DocuChat
        </h1>
        <p className="muted">Posez vos questions sur les documents internes. Réponses sourcées.</p>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Mot de passe
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? 'Connexion…' : 'Se connecter'}
        </button>
        <div className="demo">
          <span className="muted">Comptes de démo :</span>
          {DEMO.map((d) => (
            <button
              type="button"
              key={d.email}
              className="chip"
              onClick={() => {
                setEmail(d.email)
                setPassword(d.password)
              }}
            >
              {d.label}
            </button>
          ))}
        </div>
      </form>
    </div>
  )
}
