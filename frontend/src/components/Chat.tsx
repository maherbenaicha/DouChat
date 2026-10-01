import { Fragment, useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../api'
import type { ChatResponse, Conversation, Message, Source } from '../types'

const SUGGESTIONS = [
  'Combien de jours de télétravail par semaine ?',
  "Quel est le montant de l'indemnite de teletravial ?",
  'Combien de jours de congés pour un mariage ?',
  'Quel est le salaire d’un ingénieur junior ?',
]

function AnswerText({ text, onCite }: { text: string; onCite: (ref: number) => void }) {
  const parts = text.split(/(\[\d+\])/g)
  return (
    <p className="answer">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/)
        if (!m) return <Fragment key={i}>{part}</Fragment>
        const ref = Number(m[1])
        return (
          <button key={i} className="cite" onClick={() => onCite(ref)} title="Voir la source">
            {ref}
          </button>
        )
      })}
    </p>
  )
}

function Sources({ sources, highlighted }: { sources: Source[]; highlighted: number | null }) {
  if (!sources.length) return null
  return (
    <div className="sources">
      {sources.map((s) => (
        <details key={s.ref} className={highlighted === s.ref ? 'source hl' : 'source'} open={highlighted === s.ref}>
          <summary>
            <span className="cite static">{s.ref}</span>
            <strong>{s.document_title}</strong>
            {s.page && <span className="muted"> · p. {s.page}</span>}
          </summary>
          <p className="snippet">{s.snippet}</p>
        </details>
      ))}
    </div>
  )
}

function AssistantMessage({ msg }: { msg: Message }) {
  const [hl, setHl] = useState<number | null>(null)
  return (
    <div className="msg assistant">
      {msg.corrected_query && (
        <div className="corrected">
          Recherche élargie : <em>{msg.corrected_query}</em>
        </div>
      )}
      <AnswerText text={msg.content} onCite={setHl} />
      <Sources sources={msg.sources ?? []} highlighted={hl} />
    </div>
  )
}

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const loadConversations = useCallback(async () => {
    setConversations(await api<Conversation[]>('/conversations'))
  }, [])

  useEffect(() => {
    loadConversations().catch(() => {})
  }, [loadConversations])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const openConversation = async (id: number) => {
    setActiveId(id)
    setError(null)
    setMessages(await api<Message[]>(`/conversations/${id}/messages`))
  }

  const newConversation = () => {
    setActiveId(null)
    setMessages([])
    setError(null)
  }

  const removeConversation = async (id: number) => {
    await api(`/conversations/${id}`, { method: 'DELETE' })
    if (id === activeId) newConversation()
    loadConversations()
  }

  const send = async (question: string) => {
    if (!question.trim() || busy) return
    setBusy(true)
    setError(null)
    setInput('')
    setMessages((m) => [...m, { id: Date.now(), role: 'user', content: question, sources: null }])
    try {
      const res = await api<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify({ question, conversation_id: activeId }),
      })
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          corrected_query: res.corrected_query,
        },
      ])
      if (activeId === null) {
        setActiveId(res.conversation_id)
        loadConversations()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setBusy(false)
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    send(input)
  }

  return (
    <div className="chat-layout">
      <aside className="sidebar">
        <button onClick={newConversation}>+ Nouvelle conversation</button>
        <ul>
          {conversations.map((c) => (
            <li key={c.id} className={c.id === activeId ? 'active' : ''}>
              <button className="link" onClick={() => openConversation(c.id)} title={c.title}>
                {c.title}
              </button>
              <button className="icon" onClick={() => removeConversation(c.id)} aria-label="Supprimer">
                ×
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <h2>Que voulez-vous savoir ?</h2>
              <p className="muted">
                Les réponses ne s'appuient que sur les documents auxquels vous avez accès, avec leurs sources.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) =>
            m.role === 'user' ? (
              <div key={m.id} className="msg user">
                {m.content}
              </div>
            ) : (
              <AssistantMessage key={m.id} msg={m} />
            ),
          )}
          {busy && <div className="msg assistant muted typing">Recherche dans les documents…</div>}
          {error && <div className="error">{error}</div>}
          <div ref={endRef} />
        </div>
        <form className="composer" onSubmit={onSubmit}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Posez une question sur vos documents…"
            maxLength={2000}
          />
          <button type="submit" disabled={busy || !input.trim()}>
            Envoyer
          </button>
        </form>
      </section>
    </div>
  )
}
