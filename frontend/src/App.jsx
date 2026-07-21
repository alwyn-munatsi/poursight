import { useEffect, useRef, useState } from 'react';
import MessageBubble from './components/MessageBubble';
import QuestionForm from './components/QuestionForm';
import { askQuestion, AskError } from './api';
import './App.css';

const CONVERSATION_ID = crypto.randomUUID();

const EXAMPLE_PROMPTS = [
  {
    title: 'Best sellers',
    description: 'Rank items by units sold',
    text: 'What were my five best-selling items last weekend?',
  },
  {
    title: 'Low margins',
    description: 'Find underperforming menu lines',
    text: 'Which menu items have the lowest profit margin?',
  },
  {
    title: 'Match days',
    description: 'Compare beer sales on event days',
    text: 'Did Arsenal match days lift beer sales?',
  },
];

function BrandIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4" y="13" width="3" height="7" rx="1" fill="currentColor" opacity="0.55" />
      <rect x="10.5" y="9" width="3" height="11" rx="1" fill="currentColor" />
      <rect x="17" y="5" width="3" height="15" rx="1" fill="currentColor" opacity="0.75" />
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
    <div className="app-page">
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
          <div className="header-meta">
            <span className="status-pill">
              <span className="status-dot" aria-hidden="true" />
              Ready
            </span>
            <span className="header-badge">Analytics</span>
          </div>
        </header>

        <main className="chat-area">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">
                <BrandIcon />
              </div>
              <p className="empty-state-eyebrow">Business intelligence</p>
              <h2>Ask questions in plain English</h2>
              <p className="empty-state-lead">
                Get grounded answers about sales, margins, inventory, and match-day trends -
                with charts and actionable recommendations.
              </p>
              <div className="example-section">
                <h3 className="example-section-title">Suggested questions</h3>
                <div className="example-grid">
                  {EXAMPLE_PROMPTS.map(({ title, description, text }, index) => (
                    <button
                      key={text}
                      type="button"
                      className="example-card"
                      onClick={() => handleAsk(text)}
                      disabled={pending}
                    >
                      <span className="example-card-index">{String(index + 1).padStart(2, '0')}</span>
                      <span className="example-card-body">
                        <span className="example-card-title">{title}</span>
                        <span className="example-card-description">{description}</span>
                        <span className="example-card-text">{text}</span>
                      </span>
                      <span className="example-card-arrow" aria-hidden="true">
                        →
                      </span>
                    </button>
                  ))}
                </div>
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
    </div>
  );
}
