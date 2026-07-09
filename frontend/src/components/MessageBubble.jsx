import ChartView from './ChartView';

function RecommendationCard({ text }) {
  return (
    <div className="recommendation-card">
      <div className="recommendation-label">Recommendation</div>
      <p>{text}</p>
    </div>
  );
}

function QueryDetails({ intent, sql, rowCount, truncated }) {
  return (
    <details className="query-details">
      <summary>How this was answered</summary>
      <div className="query-details-body">
        <div>
          <span className="query-details-key">Intent</span>
          <span>{intent}</span>
        </div>
        <div>
          <span className="query-details-key">Rows returned</span>
          <span>
            {rowCount}
            {truncated ? ' (truncated)' : ''}
          </span>
        </div>
        <pre className="query-sql">{sql}</pre>
      </div>
    </details>
  );
}

export default function MessageBubble({ message }) {
  const { role, text, chart, recommendation, intent, sql, rowCount, truncated } = message;

  if (role === 'user') {
    return (
      <div className="message-row message-row-user">
        <div className="bubble bubble-user">{text}</div>
      </div>
    );
  }

  if (role === 'error') {
    return (
      <div className="message-row message-row-assistant">
        <div className="bubble bubble-error">{text}</div>
      </div>
    );
  }

  if (role === 'pending') {
    return (
      <div className="message-row message-row-assistant">
        <div className="bubble bubble-assistant bubble-pending">
          <span className="pulse-dot" />
          <span className="pulse-dot" />
          <span className="pulse-dot" />
        </div>
      </div>
    );
  }

  return (
    <div className="message-row message-row-assistant">
      <div className="bubble bubble-assistant">
        <p className="answer-text">{text}</p>
        <ChartView chart={chart} />
        {recommendation && <RecommendationCard text={recommendation} />}
        {sql && <QueryDetails intent={intent} sql={sql} rowCount={rowCount} truncated={truncated} />}
      </div>
    </div>
  );
}
