export class AskError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function askQuestion(question, conversationId) {
  const response = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = body && body.detail ? body.detail : `Request failed (${response.status})`;
    throw new AskError(detail, response.status);
  }

  return body;
}
