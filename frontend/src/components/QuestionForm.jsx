import { useState } from 'react';

const EXAMPLE_QUESTIONS = [
  'What were my five best-selling items last weekend?',
  'Which menu items have the lowest profit margin?',
  'Did Arsenal match days lift beer sales?',
];

export default function QuestionForm({ onAsk, disabled, showExamples }) {
  const [value, setValue] = useState('');

  function submit(question) {
    const trimmed = question.trim();
    if (!trimmed || disabled) return;
    onAsk(trimmed);
    setValue('');
  }

  return (
    <div className="question-form">
      {showExamples && (
        <div className="example-chips">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              className="example-chip"
              onClick={() => submit(q)}
              disabled={disabled}
            >
              {q}
            </button>
          ))}
        </div>
      )}
      <form
        className="input-row"
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
      >
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask about sales, margins, inventory..."
          disabled={disabled}
          aria-label="Ask PourSight a question"
        />
        <button type="submit" disabled={disabled || !value.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
