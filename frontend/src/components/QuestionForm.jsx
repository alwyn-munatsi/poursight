import { useEffect, useRef, useState } from 'react';

function SendIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M3.5 10h11M10.5 5.5 15 10l-4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function QuestionForm({ onAsk, disabled }) {
  const [value, setValue] = useState('');
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, [value]);

  function submit(question) {
    const trimmed = question.trim();
    if (!trimmed || disabled) return;
    onAsk(trimmed);
    setValue('');
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(value);
    }
  }

  return (
    <div className="question-form">
      <form
        className="input-row"
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about sales, margins, inventory..."
          disabled={disabled}
          aria-label="Ask PourSight a question"
        />
        <button type="submit" className="send-button" disabled={disabled || !value.trim()}>
          <span>Send</span>
          <SendIcon />
        </button>
      </form>
      <p className="input-hint">
        Press <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line
      </p>
    </div>
  );
}
