import { useEffect, useRef, useState } from 'react';
import MessageBubble from './components/MessageBubble';
import QuestionForm from './components/QuestionForm';
import { askQuestion, AskError } from './api';
import './App.css';

const CONVERSATION_ID = crypto.randomUUID();

const EXAMPLE_PROMPTS = [
  {
    title: 'Best sellers',
    text: 'What were my five best-selling items last weekend?',
  },
  {
    title: 'Low margins',
    text: 'Which menu items have the lowest profit margin?',
  },
  {
    title: 'Match days',
    text: 'Did Arsenal match days lift beer sales?',
  },
];

function BrandIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M8 4h8l-1 12.5a1.5 1.5 0 0 1-1.49 1.35h-3.02A1.5 1.5 0 0 1 9 16.5L8 4Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M7 4h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pending]);

  async function handleAsk(question) {
    const userMessage = { id: crypto.randomUUID(), role: 'user', text: question };
    setMessages((prev) => [...prev, userMessage]);
    setPending(true);

    try {
      const result = await askQuestion(question, CONVERSATION_ID);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: result.answer_text,
          chart: result.chart,
          recommendation: result.recommendation,
          intent: result.intent,
          sql: result.sql,
          rowCount: result.row_count,
          truncated: result.truncated,
        },
      ]);
    } catch (err) {
      const text =
        err instanceof AskError
          ? err.message
          : 'Something went wrong reaching PourSight. Is the backend running?';
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'error', text }]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <BrandIcon />
          </div>
          <div className="brand-text">
            <span className="brand-mark">PourSight</span>
            <span className="brand-sub">The Arsenal Bar &amp; Grill · Bindura, Zimbabwe</span>
          </div>
        </div>
        <span className="header-badge">Analytics</span>
      </header>

      <main className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <BrandIcon />
            </div>
            <h2>Ask anything about your bar</h2>
            <p>
              Plain-English questions about sales, margins, inventory, and match-day trends —
              answered with charts and recommendations.
            </p>
            <div className="example-grid">
              {EXAMPLE_PROMPTS.map(({ title, text }) => (
                <button
                  key={text}
                  type="button"
                  className="example-card"
                  onClick={() => handleAsk(text)}
                  disabled={pending}
                >
                  <span className="example-card-title">{title}</span>
                  <span className="example-card-text">{text}</span>
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {pending && <MessageBubble message={{ id: 'pending', role: 'pending' }} />}
        <div ref={scrollRef} />
      </main>

      <footer className="app-footer">
        <QuestionForm onAsk={handleAsk} disabled={pending} />
      </footer>
    </div>
  );
}
