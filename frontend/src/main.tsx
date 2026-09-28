import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import {
  ArrowUp,
  BookOpen,
  Check,
  ChevronRight,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Plus,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Upload,
  X,
} from "lucide-react";
import {
  api,
  type Conversation,
  type Document,
  type Message,
  type Session,
  type Source,
} from "./api";
import "./style.css";

const examples = [
  "How do I request VPN access?",
  "What is the SLA for a high-priority incident?",
  "What should I do if my laptop is damaged?",
  "How do I request database access?",
  "What should I do if MFA does not work?",
  "Can I install software without approval?",
];
const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";

export function App() {
  const [session, setSession] = useState<Session | null>(() => {
    try {
      return JSON.parse(sessionStorage.getItem("helpdesk-session") || "null");
    } catch {
      return null;
    }
  });
  const [history, setHistory] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversation, setConversation] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [source, setSource] = useState<Source | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const navigate = useNavigate();
  useEffect(() => {
    if (session)
      api<Conversation[]>("/conversations", session.token)
        .then(async (items) => {
          setHistory(items);
          const active = sessionStorage.getItem(`helpdesk-conversation:${session.email}`);
          if (active && items.some((item) => item.id === active)) {
            setMessages(await api(`/conversations/${active}`, session.token));
            setConversation(active);
          }
        })
        .catch((e) => setError(errorText(e)));
  }, [session]);
  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      let visitor = session;
      if (!visitor) {
        visitor = await api<Session>("/auth/guest", undefined, { method: "POST" });
        sessionStorage.setItem("helpdesk-session", JSON.stringify(visitor));
        setSession(visitor);
      }
      const result = await api<{ conversation_id: string; message: Message }>(
        "/chat",
        visitor.token,
        {
          method: "POST",
          body: JSON.stringify({ question, conversation_id: conversation }),
        },
      );
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: question,
          sources: [],
        },
        result.message,
      ]);
      setConversation(result.conversation_id);
      sessionStorage.setItem(`helpdesk-conversation:${visitor.email}`, result.conversation_id);
      setQuestion("");
      setHistory(await api("/conversations", visitor.token));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function openChat(id: string) {
    if (!session || busy) return;
    setError("");
    setSource(null);
    try {
      setMessages(await api(`/conversations/${id}`, session.token));
      setConversation(id);
      sessionStorage.setItem(`helpdesk-conversation:${session.email}`, id);
      navigate("/");
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function rate(id: string, rating: number) {
    try {
      await api(`/messages/${id}/feedback`, session?.token, {
        method: "PUT",
        body: JSON.stringify({ rating }),
      });
      setRatings((r) => ({ ...r, [id]: rating }));
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="/">
          <span className="brand-icon">
            <BookOpen size={23} />
          </span>
          <span>
            HelpDesk <b>AI</b>
            <small>INTERNAL KNOWLEDGE</small>
          </span>
        </a>
        <button
          className="new-chat"
          disabled={busy}
          onClick={() => {
            setMessages([]);
            setConversation(null);
            if (session) sessionStorage.removeItem(`helpdesk-conversation:${session.email}`);
            setSource(null);
            setError("");
            navigate("/");
          }}
        >
          <Plus size={18} /> New conversation
        </button>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          <NavLink to="/" end>
            <MessageSquare size={18} /> Ask HelpDesk
          </NavLink>
          <NavLink to="/knowledge">
            <BookOpen size={18} /> Knowledge base
          </NavLink>
          {session?.role === "admin" && (
            <>
              <NavLink to="/documents">
                <FileText size={18} /> Manage documents
              </NavLink>
              <NavLink to="/analytics">
                <LayoutDashboard size={18} /> Analytics
              </NavLink>
            </>
          )}
        </nav>
        <div className="nav-label history-label">RECENT CONVERSATIONS</div>
        <div className="history">
          {history.length ? (
            history.map((c) => (
              <button key={c.id} onClick={() => openChat(c.id)} disabled={busy}>
                <MessageSquare size={14} />
                {c.title}
              </button>
            ))
          ) : (
            <p>
              Your conversations will
              <br />
              appear here.
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="demo-card">
            <ShieldCheck size={18} />
            <div>
              <strong>A safe space to explore</strong>
              <p>Portfolio demo · Synthetic policies</p>
            </div>
          </div>
          {session && session.role !== "guest" ? (
            <button
              className="profile"
              onClick={() => {
                sessionStorage.removeItem("helpdesk-session");
                setSession(null);
                setHistory([]);
                setMessages([]);
                setConversation(null);
                navigate("/");
              }}
            >
              <span className="avatar">{session.email[0].toUpperCase()}</span>
              <span>
                {session.role === "admin"
                  ? "IT Administrator"
                  : "Demo employee"}
                <small>Sign out</small>
              </span>
              <LogOut size={16} />
            </button>
          ) : (
            <button
              className="profile"
              aria-label="Sign in to HelpDesk AI"
              onClick={() => setLoginOpen(true)}
            >
              <span className="avatar">G</span>
              <span>
                Guest workspace<small>Administrator sign in</small>
              </span>
              <ChevronRight size={16} />
            </button>
          )}
        </div>
      </aside>
      <main>
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />{" "}
            <strong>Internal IT assistant</strong>
          </div>
          <span className="demo-tag">
            <span /> DEMO ENVIRONMENT
          </span>
        </header>
        {error && (
          <div className="error" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </button>
          </div>
        )}
        <Routes>
          <Route
            path="/"
            element={
              <div className="chat-page">
                <div className="chat-toolbar">
                  <span>
                    <span className="status-dot" /> KNOWLEDGE-BASE ANSWERS
                  </span>
                  <span>
                    <ShieldCheck size={14} /> Sources included
                  </span>
                </div>
                {!messages.length ? (
                  <section className="welcome">
                    <div className="welcome-icon">
                      <Sparkles size={28} />
                    </div>
                    <div className="eyebrow">
                      EVIDENCE-FIRST IT KNOWLEDGE ASSISTANT
                    </div>
                    <h1>
                      Less searching.
                      <br />
                      <span>More getting things done.</span>
                    </h1>
                    <p>
                      Ask questions about the demo IT knowledge base.
                      <br />
                      Every supported answer comes with sources you can verify.
                    </p>
                    <div className="suggestions">
                      {examples.map((q, i) => (
                        <button key={q} onClick={() => setQuestion(q)}>
                          <span className="suggestion-icon">
                            {["↗", "◷", "⌘", "▤", "◈", "↓"][i]}
                          </span>
                          <span>{q}</span>
                          <ChevronRight size={16} />
                        </button>
                      ))}
                    </div>
                    <div className="evidence-note">
                      <ShieldCheck size={15} /> If the documents don't have the
                      answer, we'll say so.
                    </div>
                  </section>
                ) : (
                  <section className="messages" aria-live="polite">
                    {messages.map((m) => (
                      <article key={m.id} className={`message ${m.role}`}>
                        <div className="message-heading">
                          {m.role === "user" ? (
                            "You"
                          ) : (
                            <>
                              <span className="mini-logo">
                                <Sparkles size={14} />
                              </span>{" "}
                              HelpDesk AI{" "}
                              <small>
                                {m.outcome === "fallback"
                                  ? "Insufficient evidence"
                                  : m.outcome === "clarification" ? "Choose a topic"
                                  : "Source-backed answer"}
                              </small>
                            </>
                          )}
                        </div>
                        <div className="message-content">{m.content}</div>
                        {m.synthesis_status && m.synthesis_status !== "used" && (
                          <p className="evidence-note">
                            {m.synthesis_status === "limited"
                              ? "Optional answer rewriting is limited today. This answer uses the approved source facts directly."
                              : "This answer uses the approved source facts directly."}
                          </p>
                        )}
                        {!!m.clarification?.length && (
                          <div className="citations" aria-label="Clarification options">
                            {m.clarification.map((option) => (
                              <button key={option.intent_id} onClick={() => setQuestion(option.question)}>
                                {option.topic}
                              </button>
                            ))}
                          </div>
                        )}
                        {m.sources.length > 0 && (
                          <div className="citations">
                            {m.sources.map((s) => (
                              <button key={s.id} onClick={() => setSource(s)}>
                                <FileText size={14} />
                                <b>{s.citation_number}</b> {s.title}
                              </button>
                            ))}
                          </div>
                        )}
                        {m.role === "assistant" && (
                          <div className="feedback">
                            <span>Was this helpful?</span>
                            <button
                              aria-label="Helpful"
                              aria-pressed={ratings[m.id] === 1}
                              onClick={() => rate(m.id, 1)}
                            >
                              <ThumbsUp size={14} />
                            </button>
                            <button
                              aria-label="Not helpful"
                              aria-pressed={ratings[m.id] === -1}
                              onClick={() => rate(m.id, -1)}
                            >
                              <ThumbsDown size={14} />
                            </button>
                            {ratings[m.id] && <Check size={14} />}
                          </div>
                        )}
                      </article>
                    ))}
                    {busy && (
                      <p className="loading">
                        Searching documents and checking evidence…
                      </p>
                    )}
                  </section>
                )}
                <div className="composer-wrap">
                  {busy && <p className="loading" role="status">Checking the knowledge base… The demo server may take a minute to wake up.</p>}
                  <form className="composer" onSubmit={ask}>
                    <textarea
                      aria-label="Ask an IT question"
                      placeholder="Ask about VPN, access requests, IT policies…"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      maxLength={2000}
                      disabled={busy}
                      rows={2}
                    />
                    <div className="composer-bottom">
                      <span>
                        <BookOpen size={14} /> Answers from approved documents
                      </span>
                      <button
                        type="submit"
                        aria-label="Send question"
                        disabled={busy || !question.trim()}
                      >
                        <ArrowUp size={19} />
                      </button>
                    </div>
                  </form>
                  <p className="disclaimer">
                    Demo policies only. Verify sources before acting. Do not
                    enter confidential information.
                  </p>
                </div>
              </div>
            }
          />
          <Route
            path="/knowledge"
            element={
              <Library session={session} manage={false} onError={setError} />
            }
          />
          <Route
            path="/documents"
            element={<Library session={session} manage onError={setError} />}
          />
          <Route
            path="/analytics"
            element={<Analytics session={session} onError={setError} />}
          />
          <Route
            path="*"
            element={
              <div className="page">
                <h1>Page not found</h1>
                <NavLink to="/">Return to assistant</NavLink>
              </div>
            }
          />
        </Routes>
      </main>
      {source && (
        <aside className="source-panel">
          <button
            className="close"
            aria-label="Close source"
            onClick={() => setSource(null)}
          >
            <X />
          </button>
          <div className="eyebrow">SOURCE EVIDENCE</div>
          <h2>{source.title}</h2>
          <p>
            {source.section || "Document excerpt"}
            {source.page_number ? ` · Page ${source.page_number}` : ""}
          </p>
          <blockquote>{source.excerpt}</blockquote>
          <div className="score">
            Cosine similarity{" "}
            <strong>{source.relevance_score.toFixed(3)}</strong>
          </div>
          <small>
            Retrieval similarity is not a measure of answer certainty. This is
            the evidence snapshot recorded with this answer.
          </small>
          <NavLink to="/knowledge" onClick={() => setSource(null)}>
            Open knowledge base →
          </NavLink>
        </aside>
      )}
      {loginOpen && (
        <div className="modal-backdrop">
          <Login
            onClose={() => setLoginOpen(false)}
            onLogin={(s) => {
              setMessages([]);
              setConversation(null);
              setHistory([]);
              setSession(s);
              sessionStorage.setItem("helpdesk-session", JSON.stringify(s));
              setLoginOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

function Login({
  onClose,
  onLogin,
}: {
  onClose: () => void;
  onLogin: (s: Session) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="modal"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          onLogin(
            await api("/auth/login", undefined, {
              method: "POST",
              body: JSON.stringify({ email, password }),
            }),
          );
        } catch (e) {
          setError(errorText(e));
        } finally {
          setBusy(false);
        }
      }}
    >
      <button
        className="close"
        type="button"
        aria-label="Close sign in"
        onClick={onClose}
      >
        <X />
      </button>
      <div className="eyebrow">WELCOME TO YOUR WORKSPACE</div>
      <h2>Sign in to HelpDesk AI</h2>
      <p>Use the demo account provided by the project administrator.</p>
      <label>
        Email
        <input
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </label>
      <label>
        Password
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {error && <p role="alert">{error}</p>}
      <button className="primary" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <small>
        Portfolio demonstration. No enterprise security guarantee or production
        SLA.
      </small>
    </form>
  );
}

function Library({
  session,
  manage,
  onError,
}: {
  session: Session | null;
  manage: boolean;
  onError: (s: string) => void;
}) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [detail, setDetail] = useState<{
    document: Document;
    chunks: {
      id: string;
      content: string;
      section: string | null;
      page_number: number | null;
    }[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
      setLoading(true);
      api<Document[]>("/documents", session?.token)
        .then(setDocuments)
        .catch((e) => onError(errorText(e)))
        .finally(() => setLoading(false));
  }, [session, onError]);
  if (manage && session?.role !== "admin")
    return (
      <div className="page">
        <h1>Administrator access required</h1>
      </div>
    );
  async function action(path: string, method: string, body?: FormData) {
    setBusy(true);
    try {
      await api(path, session?.token, { method, body });
      setDocuments(await api("/documents", session?.token));
      setDetail(null);
    } catch (e) {
      onError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page">
      <div className="eyebrow">THE SOURCE OF YOUR ANSWERS</div>
      <h1>{manage ? "Manage documents" : "Knowledge base"}</h1>
      <p>
        Approved, synthetic IT policies. Open a document to inspect its indexed
        text.
      </p>
      {manage && (
        <label className="upload">
          <Upload size={20} />
          {busy
            ? "Processing document…"
            : "Upload PDF, TXT or Markdown · max 10 MB"}
          <input
            aria-label="Upload document"
            type="file"
            accept=".pdf,.txt,.md"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                const data = new FormData();
                data.append("file", f);
                void action("/documents", "POST", data);
              }
              e.target.value = "";
            }}
          />
        </label>
      )}
      <input
        className="search"
        aria-label="Search documents"
        placeholder="Search document titles…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <div className="document-grid">
        {documents
          .filter((d) => d.title.toLowerCase().includes(search.toLowerCase()))
          .map((d) => (
            <article className="document-card" key={d.id}>
              <FileText size={24} />
              <h3>{d.title}</h3>
              <small>{d.filename}</small>
              <button
                onClick={async () => {
                  try {
                    setDetail(await api(`/documents/${d.id}`, session?.token));
                  } catch (e) {
                    onError(errorText(e));
                  }
                }}
              >
                Read source <ChevronRight size={14} />
              </button>
              {manage && (
                <div className="document-actions">
                  <button
                    disabled={busy}
                    onClick={() => action(`/documents/${d.id}/reindex`, "POST")}
                  >
                    Re-index
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(`Remove ${d.title} from future answers?`)
                      )
                        void action(`/documents/${d.id}`, "DELETE");
                    }}
                  >
                    Remove
                  </button>
                </div>
              )}
            </article>
          ))}
      </div>
      {loading && <p role="status">Loading documents… The demo server may need a minute to wake up.</p>}
      {!loading && !documents.length && (
        <div className="empty">
          <BookOpen />
          <h3>No documents yet</h3>
          <p>
            An administrator can upload the synthetic knowledge base to get
            started.
          </p>
        </div>
      )}
      {detail && (
        <section className="document-detail">
          <button
            className="close"
            aria-label="Close document"
            onClick={() => setDetail(null)}
          >
            <X />
          </button>
          <h2>{detail.document.title}</h2>
          {detail.chunks.map((c) => (
            <article key={c.id}>
              <h3>
                {c.section || "Excerpt"}{" "}
                {c.page_number ? `· Page ${c.page_number}` : ""}
              </h3>
              <p>{c.content}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}

type Stats = {
  total_questions: number;
  answered: number;
  deterministic_answers: number;
  synthesized_answers: number;
  fallbacks: number;
  clarifications: number;
  top_intents: { intent: string; questions: number }[];
  top_unmatched: { question: string; count: number }[];
  positive_feedback_percent: number | null;
  feedback_count: number;
  top_sources: { title: string; uses: number }[];
  recent_queries: { question: string; created_at: string }[];
};
function Analytics({
  session,
  onError,
}: {
  session: Session | null;
  onError: (s: string) => void;
}) {
  const [stats, setStats] = useState<Stats | null>(null);
  useEffect(() => {
    if (session?.role === "admin")
      api<Stats>("/analytics", session.token)
        .then(setStats)
        .catch((e) => onError(errorText(e)));
  }, [session, onError]);
  if (session?.role !== "admin")
    return (
      <div className="page">
        <h1>Administrator access required</h1>
      </div>
    );
  return (
    <div className="page">
      <div className="eyebrow">OBSERVE & IMPROVE</div>
      <h1>Knowledge in practice</h1>
      <p>Actual demo usage. No estimated business impact.</p>
      {stats ? (
        <>
          <div className="stats">
            {[
              ["Questions", stats.total_questions],
              ["Answered", stats.answered],
              ["Direct source answers", stats.deterministic_answers],
              ["Rewritten answers", stats.synthesized_answers],
              ["Insufficient evidence", stats.fallbacks],
              ["Clarifications", stats.clarifications],
              [
                "Positive feedback",
                stats.positive_feedback_percent === null
                  ? "No ratings"
                  : `${stats.positive_feedback_percent}%`,
              ],
            ].map(([label, value]) => (
              <article key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
          <section className="analytics-section">
            <h2>Top detected intents</h2>
            {stats.top_intents.map((item) => <p key={item.intent}>{item.intent}<b>{item.questions} questions</b></p>)}
          </section>
          <section className="analytics-section">
            <h2>Common unmatched questions</h2>
            {stats.top_unmatched.map((item) => <p key={item.question}>{item.question}<b>{item.count}</b></p>)}
          </section>
          <section className="analytics-section">
            <h2>Most cited documents</h2>
            {stats.top_sources.length ? (
              stats.top_sources.map((s) => (
                <p key={s.title}>
                  {s.title}
                  <b>{s.uses} citations</b>
                </p>
              ))
            ) : (
              <p>No citations recorded yet.</p>
            )}
          </section>
          <section className="analytics-section">
            <h2>Recent questions</h2>
            {stats.recent_queries.length ? (
              stats.recent_queries.map((q, i) => (
                <p key={i}>
                  {q.question}
                  <small>{new Date(q.created_at).toLocaleDateString()}</small>
                </p>
              ))
            ) : (
              <p>No questions yet.</p>
            )}
          </section>
        </>
      ) : (
        <p>Loading usage…</p>
      )}
    </div>
  );
}
