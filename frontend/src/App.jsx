import { useEffect, useMemo, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { supabase } from "./supabase";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const THEME_KEY = "ayurveda-theme";

const starterQuestions = [
  "What is Ayurveda?",
  "What are the main concepts of Ayurveda?",
  "What does Ayurveda say about daily routines?",
  "What does the available research say about turmeric?",
  "What are safety considerations when using herbal products?",
  "How are the three Doshas understood in Ayurvedic philosophy?"
];

function formatConversationTitle(text) {
  if (!text) return "New conversation";
  const clean = text.trim().replace(/\s+/g, " ");
  if (clean.length <= 46) return clean;
  const truncated = clean.slice(0, 46);
  const lastSpace = truncated.lastIndexOf(" ");
  const cut = lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated;
  return `${cut}…`;
}

function FormattedAnswerPrimary({ text }) {
  return (
    <div className="formatted-answer">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function Home({ onStart, onLearn, user }) {
  return (
    <div className="home-view">
      <span className="eyebrow">YOUR PERSONAL WELLNESS LIBRARY</span>
      <h1>
        Make space for<br />
        <em>better questions.</em>
      </h1>
      <p className="home-lead">
        Welcome, {user.name.split(" ")[0]}. Discover clear, source-grounded perspectives on Ayurveda, traditional practices, and the evidence around them.
      </p>
      <div className="home-actions">
        <button className="primary-button" onClick={onStart}>
          Start a conversation <span>↗</span>
        </button>
        <button className="secondary-button" onClick={onLearn}>
          Explore the approach
        </button>
      </div>
      <div className="feature-row">
        <div>
          <span>01</span>
          <strong>Ask openly</strong>
          <p>From daily routines to medicinal plants.</p>
        </div>
        <div>
          <span>02</span>
          <strong>See the context</strong>
          <p>Relevant passages appear with every answer.</p>
        </div>
        <div>
          <span>03</span>
          <strong>Stay discerning</strong>
          <p>Traditional knowledge is labeled clearly.</p>
        </div>
      </div>
    </div>
  );
}

function History({ conversations, search, setSearch, open, remove }) {
  return (
    <div className="page-view">
      <span className="eyebrow">YOUR LIBRARY</span>
      <h1>Conversation history</h1>
      <p className="page-lead">Return to a question, or make room for a new one.</p>
      <input
        className="search-input"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search conversations"
      />
      {conversations.length ? (
        <div className="history-list">
          {conversations.map((conversation) => (
            <div className="history-item" key={conversation.id}>
              <button onClick={() => open(conversation)}>
                <span className="history-icon">✦</span>
                <span>
                  <strong>{conversation.title}</strong>
                  <small>
                    {conversation.messages.length} messages ·{" "}
                    {new Date(conversation.updatedAt).toLocaleDateString()}
                  </small>
                </span>
              </button>
              <button
                className="delete-button"
                onClick={() => remove(conversation.id)}
                aria-label={`Delete ${conversation.title}`}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">No conversations found. Start exploring to build your library.</div>
      )}
    </div>
  );
}

function InfoPage({ type, onBack }) {
  const safety = type === "safety";
  const cards = safety
    ? [
        [
          "Urgent symptoms",
          "For severe chest pain, difficulty breathing, stroke symptoms, severe bleeding, poisoning, or an immediate crisis, seek emergency care now."
        ],
        [
          "Medication and conditions",
          "Never stop or change prescribed treatment based on an AI answer. Ask your clinician about herbs, interactions, pregnancy, children, and chronic conditions."
        ],
        [
          "Evidence has layers",
          "Traditional and classical sources describe a tradition. Research and clinical sources answer different questions. We keep those categories visible."
        ]
      ]
    : [
        [
          "Grounded by sources",
          "Your question is matched against the documents in the knowledge base before an answer is generated."
        ],
        [
          "Clear about uncertainty",
          "When relevant evidence is limited, the assistant says so. It does not invent citations, dosages, studies, or guaranteed cures."
        ],
        [
          "Designed to evolve",
          "This lightweight prototype can later move its local index and files to PostgreSQL, pgvector, and durable object storage."
        ]
      ];

  return (
    <div className="page-view info-page">
      <button className="back-button" onClick={onBack}>
        ← Back to assistant
      </button>
      <span className="eyebrow">{safety ? "SAFETY CENTRE" : "THE AYURVEDA APPROACH"}</span>
      <h1>{safety ? "Care comes first." : "A thoughtful place to learn."}</h1>
      <p className="page-lead">
        {safety
          ? "AyurVeda is an educational companion, never a replacement for a qualified health professional."
          : "AyurVeda uses retrieval-augmented generation to help you explore a living tradition with more context and less noise."}
      </p>
      <div className="info-grid">
        {cards.map(([title, text]) => (
          <article className="info-card" key={title}>
            <span>✦</span>
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function AuthOrLanding({ mode, setView, setAuthMode, form, setForm, error, onSubmit, onGuestDemo }) {
  if (!mode) {
    return (
      <div className="landing">
        <header className="landing-nav">
          <button className="brand brand-button">
            <span className="brand-mark">✦</span>
            <span>
              <strong>AyurVeda</strong>
              <small>Source-grounded wellness</small>
            </span>
          </button>
          <div className="landing-nav-actions">
            <button
              className="sign-in-link"
              onClick={() => {
                setAuthMode("login");
                setView("auth");
              }}
            >
              Sign in <span>↗</span>
            </button>
          </div>
        </header>
        <div className="landing-hero">
          <div className="hero-copy">
            <span className="eyebrow">A QUIETER WAY TO LEARN</span>
            <h1>
              Ancient wisdom,<br />
              <em>carefully explored.</em>
            </h1>
            <p>
              Explore Ayurveda through an AI-powered health-awareness assistant grounded in your curated knowledge base.
            </p>
            <div className="hero-actions">
              <button
                className="primary-button"
                onClick={() => {
                  setAuthMode("signup");
                  setView("auth");
                }}
              >
                Create your free account <span>↗</span>
              </button>
              <button
                className="secondary-button"
                onClick={() => {
                  setAuthMode("login");
                  setView("auth");
                }}
              >
                Sign in
              </button>
            </div>
            <div className="trust-row">
              <span>✦ Source-grounded</span>
              <span>♡ Safety-first</span>
              <span>⌁ Private by design</span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="sun-disc" />
            <div className="leaf-shape">✦</div>
            <div className="visual-card">
              <span className="mini-label">TODAY'S EXPLORATION</span>
              <strong>Understanding<br />your daily rhythm</strong>
              <small>Traditional knowledge · 4 sources</small>
            </div>
            <div className="visual-note">
              “Knowledge becomes wisdom<br />when explored with care.”
            </div>
          </div>
        </div>
        <section className="landing-strip">
          <div>
            <strong>Learn with context</strong>
            <span>Every answer starts with retrieved sources.</span>
          </div>
          <div>
            <strong>Know the limits</strong>
            <span>Traditional claims and research stay distinct.</span>
          </div>
          <div>
            <strong>Stay safe</strong>
            <span>No diagnosis, prescriptions, or promises.</span>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <button className="auth-back" onClick={() => setView("home")}>
        ← Back to AyurVeda
      </button>
      <div className="auth-card">
        <div className="auth-intro">
          <span className="brand-mark">✦</span>
          <span className="eyebrow">YOUR KNOWLEDGE SPACE</span>
          <h1>{mode === "login" ? "Welcome back." : "Begin your exploration."}</h1>
          <p>
            {mode === "login"
              ? "Continue learning with answers grounded in your sources."
              : "Create a private space for your Ayurveda conversations."}
          </p>
        </div>
        <form className="auth-form" onSubmit={onSubmit}>
          {mode === "signup" && (
            <label>
              Full name
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="Your name"
              />
            </label>
          )}
          <label>
            Email address
            <input
              type="email"
              required
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              placeholder="you@example.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              placeholder="At least 6 characters"
            />
          </label>
          {error && <div className="auth-error">{error}</div>}
          <button className="primary-button" type="submit">
            {mode === "login" ? "Sign in" : "Create account"} <span>↗</span>
          </button>
          <p className="auth-switch">
            {mode === "login" ? "New to AyurVeda?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => setAuthMode(mode === "login" ? "signup" : "login")}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
          <small className="demo-note">
            Secure authentication powered by Supabase. You may need to confirm your email.
          </small>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("chat");
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "light");
  const [copied, setCopied] = useState(null);
  const [historySearch, setHistorySearch] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  const [answerScale, setAnswerScale] = useState(1);

  const displayName =
    user?.user_metadata?.full_name ||
    user?.email?.split("@")[0]?.replace(/[._-]+/g, " ") ||
    "AyurVeda member";

  const activeConversation = conversations.find((conversation) => conversation.id === activeId);
  const filteredConversations = useMemo(
    () =>
      conversations.filter((conversation) =>
        `${conversation.title} ${conversation.messages.map((message) => message.text).join(" ")}`
          .toLowerCase()
          .includes(historySearch.toLowerCase())
      ),
    [conversations, historySearch]
  );

  useEffect(() => {
    if (!supabase) return undefined;
    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (mounted && data.session?.user) {
        setUser(data.session.user);
      }
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user || null);
      if (!session) setConversations([]);
    });
    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!user || !supabase || user.id === "demo-guest") return;
    supabase
      .from("conversations")
      .select("id,title,updated_at,messages(id,role,content,citations,created_at)")
      .order("updated_at", { ascending: false })
      .then(({ data, error }) => {
        if (error) {
          console.error("Conversation load failed", error);
          return;
        }
        setConversations(
          (data || []).map((conversation) => ({
            id: conversation.id,
            title: conversation.title,
            updatedAt: conversation.updated_at,
            messages: (conversation.messages || [])
              .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
              .map((message) => ({
                role: message.role,
                text: message.content,
                citations: message.citations || []
              }))
          }))
        );
      });
  }, [user]);

  useEffect(() => {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    fetch(`${API_URL}/api/sources`)
      .then((response) => response.json())
      .then((data) => setSources(data.documents || []))
      .catch(() => {});
  }, []);

  function saveConversation(nextMessages, id = activeId) {
    const conversationId = id || crypto.randomUUID();
    const firstUserMsg = nextMessages.find((message) => message.role === "user")?.text;
    const title = formatConversationTitle(firstUserMsg);
    const updatedAt = new Date().toISOString();
    setActiveId(conversationId);
    setConversations((current) => {
      const next = {
        id: conversationId,
        title: current.find((item) => item.id === conversationId)?.title || title,
        messages: nextMessages,
        updatedAt
      };
      return current.some((item) => item.id === conversationId)
        ? current.map((item) => (item.id === conversationId ? next : item))
        : [next, ...current];
    });

    if (!supabase || !user || user.id === "demo-guest") return;
    supabase
      .from("conversations")
      .upsert({ id: conversationId, user_id: user.id, title, updated_at: updatedAt })
      .then(({ error }) => {
        if (error) console.error("Conversation save failed", error);
      });
    const latest = nextMessages[nextMessages.length - 1];
    if (latest) {
      supabase
        .from("messages")
        .insert({
          conversation_id: conversationId,
          user_id: user.id,
          role: latest.role,
          content: latest.text,
          citations: latest.citations || []
        })
        .then(({ error }) => {
          if (error) console.error("Message save failed", error);
        });
    }
  }

  function startNewChat() {
    setActiveId(null);
    setMessages([]);
    setInput("");
    setView("chat");
  }

  function openConversation(conversation) {
    setActiveId(conversation.id);
    setMessages(conversation.messages);
    setView("chat");
  }

  function removeConversation(id) {
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
    if (supabase && user && user.id !== "demo-guest") {
      supabase
        .from("conversations")
        .delete()
        .eq("id", id)
        .then(({ error }) => {
          if (error) console.error("Conversation delete failed", error);
        });
    }
    if (id === activeId) startNewChat();
  }

  async function submitAuth(event) {
    event.preventDefault();
    setAuthError("");
    if (!authForm.email.includes("@") || authForm.password.length < 6) {
      setAuthError("Enter a valid email and a password with at least 6 characters.");
      return;
    }
    if (!supabase) {
      setAuthError("Supabase is not configured. Add the frontend Supabase environment variables.");
      return;
    }
    try {
      const name = authForm.name.trim() || authForm.email.split("@")[0];
      const result =
        authMode === "login"
          ? await supabase.auth.signInWithPassword({
              email: authForm.email,
              password: authForm.password
            })
          : await supabase.auth.signUp({
              email: authForm.email,
              password: authForm.password,
              options: { data: { full_name: name } }
            });
      if (result.error) {
        setAuthError(result.error.message);
        return;
      }
      if (authMode === "signup" && !result.data.session) {
        setAuthError("Account created. Check your email to confirm your account, then sign in.");
        return;
      }
      setView("chat");
    } catch {
      setAuthError("We could not reach Supabase. Check your connection and try again.");
    }
  }

  function enterGuestDemo() {
    setUser({
      id: "demo-guest",
      email: "gaganpaul@ayurveda.local",
      user_metadata: { full_name: "Gagan Paul V" }
    });
    setView("chat");
  }

  async function logout() {
    if (supabase && user?.id !== "demo-guest") await supabase.auth.signOut();
    setUser(null);
    setProfileOpen(false);
    setView("home");
  }

  async function deleteAccount() {
    if (
      !window.confirm("Delete your AyurVeda account and all saved conversations? This cannot be undone.")
    )
      return;
    if (!supabase || user?.id === "demo-guest") {
      setUser(null);
      setConversations([]);
      setView("home");
      return;
    }
    const { error } = await supabase.rpc("delete_my_account");
    if (error) {
      setAuthError(error.message);
      return;
    }
    await supabase.auth.signOut();
    setUser(null);
    setConversations([]);
    setView("home");
  }

  async function ask(question = input) {
    const text = question.trim();
    if (!text || loading) return;
    const nextMessages = [...messages, { role: "user", text }];
    setMessages(nextMessages);
    saveConversation(nextMessages);
    setInput("");
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, top_k: 4 })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      const completed = [
        ...nextMessages,
        { role: "assistant", text: data.answer, citations: data.sources || [] }
      ];
      setMessages(completed);
      saveConversation(completed);
    } catch (err) {
      const errorMsg =
        err?.message || "The Ayurveda knowledge base is currently unavailable. Please try again shortly.";
      const failed = [...nextMessages, { role: "assistant", text: errorMsg }];
      setMessages(failed);
      saveConversation(failed);
    } finally {
      setLoading(false);
    }
  }

  async function copyAnswer(text, index) {
    await navigator.clipboard.writeText(text);
    setCopied(index);
    setTimeout(() => setCopied(null), 1800);
  }

  if (!user) {
    return (
      <AuthOrLanding
        mode={view === "auth" ? authMode : null}
        setView={setView}
        setAuthMode={setAuthMode}
        form={authForm}
        setForm={setAuthForm}
        error={authError}
        onSubmit={submitAuth}
        onGuestDemo={enterGuestDemo}
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand brand-button" onClick={() => setView("home")}>
          <span className="brand-mark">✦</span>
          <span>
            <strong>AyurVeda</strong>
            <small>Source-grounded wellness</small>
          </span>
        </button>

        <div className="top-actions">
          <button
            className="icon-button theme-toggle"
            aria-label="Toggle theme"
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            )}
          </button>

          <div className="profile-wrap">
            <button
              className="user-chip profile-trigger"
              onClick={() => setProfileOpen((open) => !open)}
              aria-expanded={profileOpen}
            >
              <span className="user-avatar">{displayName[0].toUpperCase()}</span>
              <span className="user-name-text">{displayName}</span>
              <span className="profile-chevron">▾</span>
            </button>
            {profileOpen && (
              <div className="profile-popover">
                <span className="profile-large-avatar">{displayName[0].toUpperCase()}</span>
                <strong>{displayName}</strong>
                <small>{user.email}</small>
                <div className="profile-divider" />
                <span className="profile-status">✦ {user.id === "demo-guest" ? "Guest explorer" : "Supabase account"}</span>
                <button className="profile-signout" onClick={logout}>
                  Sign out
                </button>
                <button className="profile-delete" onClick={deleteAccount}>
                  Delete account
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="product-layout">
        <aside className="sidebar">
          <button className="new-chat" onClick={startNewChat}>
            <span className="plus-icon">＋</span> New conversation
          </button>
          <nav>
            <button
              className={view === "chat" ? "nav-item active" : "nav-item"}
              onClick={() => setView("chat")}
            >
              <span className="nav-icon">⌂</span>
              <span>Assistant</span>
            </button>
            <button
              className={view === "history" ? "nav-item active" : "nav-item"}
              onClick={() => setView("history")}
            >
              <span className="nav-icon">◷</span>
              <span>History</span>
              <b>{conversations.length}</b>
            </button>
            <button
              className={view === "about" ? "nav-item active" : "nav-item"}
              onClick={() => setView("about")}
            >
              <span className="nav-icon">ⓘ</span>
              <span>About AyurVeda</span>
            </button>
            <button
              className={view === "safety" ? "nav-item active" : "nav-item"}
              onClick={() => setView("safety")}
            >
              <span className="nav-icon">♡</span>
              <span>Safety centre</span>
            </button>
          </nav>
          <div className="sidebar-bottom">
            <div className="source-count">
              <span className="pulse-dot" /> Knowledge base live
              <strong>{sources.length || 4} sources indexed</strong>
            </div>
            <p>Educational information only. Always seek qualified medical care when needed.</p>
          </div>
        </aside>

        <main className="main-content">
          {view === "home" && (
            <Home
              onStart={() => setView("chat")}
              onLearn={() => setView("about")}
              user={{ name: displayName }}
            />
          )}
          {view === "about" && <InfoPage type="about" onBack={() => setView("chat")} />}
          {view === "safety" && <InfoPage type="safety" onBack={() => setView("chat")} />}
          {view === "history" && (
            <History
              conversations={filteredConversations}
              search={historySearch}
              setSearch={setHistorySearch}
              open={openConversation}
              remove={removeConversation}
            />
          )}
          {view === "chat" && (
            <ChatView
              activeConversation={activeConversation}
              displayName={displayName}
              messages={messages}
              loading={loading}
              input={input}
              setInput={setInput}
              ask={ask}
              startNewChat={startNewChat}
              copyAnswer={copyAnswer}
              copied={copied}
              answerScale={answerScale}
              setAnswerScale={setAnswerScale}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function ChatView({
  activeConversation,
  displayName,
  messages,
  loading,
  input,
  setInput,
  ask,
  startNewChat,
  copyAnswer,
  copied,
  answerScale,
  setAnswerScale
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const hasMessages = messages.length > 0;

  return (
    <section className="chat-area">
      <div className="chat-heading">
        <div className="chat-heading-info">
          <span className="eyebrow">PERSONAL KNOWLEDGE SPACE</span>
          <h1 className={hasMessages ? "active-chat-title" : ""}>
            {hasMessages
              ? activeConversation?.title || "Current inquiry"
              : `Good to see you, ${displayName.split(" ")[0]}.`}
          </h1>
          <p className="chat-subtitle">
            {hasMessages
              ? `Source-grounded Ayurvedic perspectives · ${messages.length} message${messages.length === 1 ? "" : "s"}`
              : "Explore Ayurveda through clear, source-grounded answers."}
          </p>
        </div>

        <div className="chat-actions">
          <div className="text-size-control" role="group" aria-label="Answer text size">
            <span className="text-size-label">Size</span>
            <button
              type="button"
              className={answerScale < 0.95 ? "active" : ""}
              onClick={() => setAnswerScale(Math.max(0.85, Number((answerScale - 0.1).toFixed(1))))}
              aria-label="Decrease text size"
              title="Smaller text"
            >
              A−
            </button>
            <button
              type="button"
              className={Math.abs(answerScale - 1) < 0.05 ? "active" : ""}
              onClick={() => setAnswerScale(1)}
              aria-label="Default text size"
              title="Reset text size"
            >
              A
            </button>
            <button
              type="button"
              className={answerScale > 1.05 ? "active" : ""}
              onClick={() => setAnswerScale(Math.min(1.25, Number((answerScale + 0.1).toFixed(1))))}
              aria-label="Increase text size"
              title="Larger text"
            >
              A+
            </button>
          </div>

          <button
            type="button"
            className="clear-button"
            onClick={startNewChat}
            title="Clear chat and start a fresh inquiry"
          >
            <span className="clear-icon">↺</span>
            <span>Clear</span>
          </button>
        </div>
      </div>

      <div className="messages" style={{ "--answer-scale": answerScale }}>
        {!hasMessages && (
          <div className="welcome-panel">
            <div className="welcome-orbit">✦</div>
            <span className="eyebrow">NAMASTE</span>
            <h2>What would you like to explore?</h2>
            <p>
              Ask about Ayurvedic concepts, daily routines, medicinal plants, holistic nutrition, or the evidence behind traditional practices.
            </p>
            <div className="starter-grid">
              {starterQuestions.map((question) => (
                <button
                  key={question}
                  className="starter-card"
                  onClick={() => ask(question)}
                >
                  <span>{question}</span>
                  <b>↗</b>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            className={`message-row ${message.role}`}
            key={`${message.text.slice(0, 20)}-${index}`}
          >
            <div
              className={`avatar ${message.role === "user" ? "user-avatar-badge" : "assistant-avatar"}`}
            >
              {message.role === "user" ? displayName[0]?.toUpperCase() : "✦"}
            </div>

            <div className="message-content">
              <div className="message-header-row">
                <span className="message-label">
                  {message.role === "user" ? "You" : "AyurVeda assistant"}
                </span>
                {message.role === "assistant" && (
                  <span className="grounded-badge">
                    <span className="badge-spark">✦</span> Grounded in sources
                  </span>
                )}
              </div>

              <div className="message-bubble">
                {message.role === "assistant" ? (
                  <FormattedAnswerPrimary text={message.text} />
                ) : (
                  <div className="user-message-text">{message.text}</div>
                )}
              </div>

              {message.role === "assistant" && (
                <div className="message-tools">
                  <button
                    type="button"
                    className="tool-btn"
                    onClick={() => copyAnswer(message.text, index)}
                    title="Copy answer"
                  >
                    <span>{copied === index ? "✓" : "📋"}</span>
                    <span>{copied === index ? "Copied" : "Copy"}</span>
                  </button>
                  <button
                    type="button"
                    className="tool-btn"
                    onClick={() => ask(messages[index - 1]?.text || "")}
                    title="Regenerate response"
                  >
                    <span>↻</span>
                    <span>Regenerate</span>
                  </button>
                  <span className="evidence-label">
                    {message.citations?.length
                      ? `✦ ${message.citations.length} sources cited`
                      : "Educational synthesis"}
                  </span>
                </div>
              )}

              {message.citations?.length > 0 && (
                <div className="citations">
                  <div className="citation-title">
                    <span>✦</span> Sources used in this answer
                  </div>
                  <div className="citations-container">
                    {message.citations.map((source, sourceIndex) => (
                      <div className="citation-card" key={`${source.name}-${sourceIndex}`}>
                        <div className="citation-header">
                          <span className="source-index">{sourceIndex + 1}</span>
                          <strong className="source-name">{source.name}</strong>
                          {source.page && (
                            <span className="source-page">Page {source.page}</span>
                          )}
                        </div>
                        <p className="citation-snippet">{source.snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-row assistant loading-row">
            <div className="avatar assistant-avatar">✦</div>
            <div className="message-content">
              <div className="message-header-row">
                <span className="message-label">AyurVeda assistant</span>
              </div>
              <div className="message-bubble typing-bubble">
                <div className="typing-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <span className="typing-text">Synthesizing Ayurvedic classical sources…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} className="messages-bottom-anchor" />
      </div>

      <div className="composer-container">
        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            ask();
          }}
        >
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                ask();
              }
            }}
            placeholder="Ask a question about Ayurveda, daily wellness, herbal safety..."
            rows={1}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            title="Send inquiry"
          >
            <span>Send</span>
            <span className="send-arrow">↗</span>
          </button>
        </form>
        <p className="composer-note">
          AyurVeda provides educational information grounded in curated references, not clinical diagnosis or treatment.
        </p>
      </div>
    </section>
  );
}
