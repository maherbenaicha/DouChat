import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { User } from '../types'

const parseGroups = (s: string) =>
  s
    .split(',')
    .map((g) => g.trim().toLowerCase())
    .filter(Boolean)

export default function Users({ currentUser }: { currentUser: User }) {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({ email: '', full_name: '', password: '', groups: '', role: 'user' })
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => setUsers(await api<User[]>('/admin/users')), [])
  useEffect(() => {
    load().catch(() => {})
  }, [load])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await api('/admin/users', {
        method: 'POST',
        body: JSON.stringify({ ...form, groups: parseGroups(form.groups) }),
      })
      setForm({ email: '', full_name: '', password: '', groups: '', role: 'user' })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur')
    }
  }

  const editGroups = async (u: User) => {
    const value = window.prompt(`Groupes de ${u.email} (séparés par des virgules)`, u.groups.join(', '))
    if (value === null) return
    try {
      await api(`/admin/users/${u.id}`, { method: 'PATCH', body: JSON.stringify({ groups: parseGroups(value) }) })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur')
    }
  }

  const remove = async (u: User) => {
    if (!window.confirm(`Supprimer ${u.email} ?`)) return
    await api(`/admin/users/${u.id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="page">
      <h2>Utilisateurs et droits d'accès</h2>
      <p className="muted">Un utilisateur voit les documents « public » et ceux de ses groupes.</p>

      <form className="card upload" onSubmit={create}>
        <h3>Nouvel utilisateur</h3>
        <div className="row">
          <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          <input placeholder="Nom" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <input
            type="password"
            placeholder="Mot de passe (6+)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            minLength={6}
            required
          />
          <input placeholder="Groupes : rh, tech" value={form.groups} onChange={(e) => setForm({ ...form, groups: e.target.value })} />
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="user">Utilisateur</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit">Créer</button>
        </div>
        {error && <div className="error">{error}</div>}
      </form>

      <table>
        <thead>
          <tr>
            <th>Email</th>
            <th>Nom</th>
            <th>Rôle</th>
            <th>Groupes</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.full_name}</td>
              <td>{u.role === 'admin' ? <span className="badge admin">admin</span> : 'utilisateur'}</td>
              <td>
                {u.groups.map((g) => (
                  <span key={g} className="badge">
                    {g}
                  </span>
                ))}
              </td>
              <td className="actions">
                <button className="ghost" onClick={() => editGroups(u)}>
                  Groupes
                </button>
                {u.id !== currentUser.id && (
                  <button className="ghost danger" onClick={() => remove(u)}>
                    Supprimer
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
