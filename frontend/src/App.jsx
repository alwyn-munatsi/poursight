import { useEffect, useRef, useState } from 'react';
import MessageBubble from './components/MessageBubble';
import QuestionForm from './components/QuestionForm';
import { askQuestion, AskError } from './api';
import './App.css';

const CONVERSATION_ID = crypto.randomUUID();

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
          <span className="brand-mark">PourSight</span>
          <span className="brand-sub">The Arsenal Bar &amp; Grill · Bindura, Zimbabwe</span>
        </div>
      </header>

      <main className="chat-area">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Ask a plain-English question about sales, margins, or inventory.</p>
          </div>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {pending && <MessageBubble message={{ id: 'pending', role: 'pending' }} />}
        <div ref={scrollRef} />
      </main>

      <footer className="app-footer">
        <QuestionForm onAsk={handleAsk} disabled={pending} showExamples={messages.length === 0} />
      </footer>
    </div>
  );
}
