import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { DocumentInfo, User } from '../types'

export default function Documents({ user }: { user: User }) {
  const [docs, setDocs] = useState<DocumentInfo[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [groups, setGroups] = useState('public')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ type: 'ok' | 'error'; text: string } | null>(null)
  const isAdmin = user.role === 'admin'

  const load = useCallback(async () => setDocs(await api<DocumentInfo[]>('/documents')), [])
  useEffect(() => {
    load().catch(() => {})
  }, [load])

  const upload = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setMessage(null)
    const form = new FormData()
    form.append('file', file)
    if (title.trim()) form.append('title', title.trim())
    form.append('allowed_groups', groups)
    try {
      const doc = await api<DocumentInfo>('/documents', { method: 'POST', body: form })
      setMessage({ type: 'ok', text: `« ${doc.title} » indexé (${doc.n_chunks} passages).` })
      setFile(null)
      setTitle('')
      ;(e.target as HTMLFormElement).reset()
      load()
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Erreur' })
    } finally {
      setBusy(false)
    }
  }

  const remove = async (doc: DocumentInfo) => {
    if (!window.confirm(`Supprimer « ${doc.title} » ?`)) return
    await api(`/documents/${doc.id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="page">
      <h2>Documents</h2>
      <p className="muted">
        {isAdmin
          ? 'Vous voyez tous les documents. Chaque document est visible uniquement par les groupes indiqués.'
          : `Documents accessibles avec vos groupes : ${[...user.groups, 'public'].join(', ')}.`}
      </p>

      {isAdmin && (
        <form className="card upload" onSubmit={upload}>
          <h3>Ajouter un document</h3>
          <div className="row">
            <input type="file" accept=".pdf,.docx,.md,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
            <input placeholder="Titre (optionnel)" value={title} onChange={(e) => setTitle(e.target.value)} />
            <input
              placeholder="Groupes : public, rh, tech…"
              value={groups}
              onChange={(e) => setGroups(e.target.value)}
              title="Groupes autorisés, séparés par des virgules"
            />
            <button type="submit" disabled={busy || !file}>
              {busy ? 'Indexation…' : 'Indexer'}
            </button>
          </div>
          {message && <div className={message.type === 'ok' ? 'success' : 'error'}>{message.text}</div>}
        </form>
      )}

      <table>
        <thead>
          <tr>
            <th>Titre</th>
            <th>Fichier</th>
            <th>Accès</th>
            <th>Passages</th>
            <th>Ajouté le</th>
            {isAdmin && <th />}
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.id}>
              <td>{d.title}</td>
              <td className="muted">{d.filename}</td>
              <td>
                {d.allowed_groups.map((g) => (
                  <span key={g} className={g === 'public' ? 'badge public' : 'badge'}>
                    {g}
                  </span>
                ))}
              </td>
              <td>{d.n_chunks}</td>
              <td className="muted">{new Date(d.created_at).toLocaleDateString('fr-FR')}</td>
              {isAdmin && (
                <td>
                  <button className="ghost danger" onClick={() => remove(d)}>
                    Supprimer
                  </button>
                </td>
              )}
            </tr>
          ))}
          {docs.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                Aucun document.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
