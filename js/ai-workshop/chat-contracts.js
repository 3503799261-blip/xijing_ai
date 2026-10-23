import { validateQuestionAnswer } from './contracts.js?v=phase4-1';

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function conversationId(value) {
  if (typeof value !== 'string' || !uuid.test(value)) throw new Error('Invalid conversation identifier');
  return value;
}
function summary(value) {
  conversationId(value?.id);
  if (typeof value.title !== 'string' || value.title.length > 120 || !value.title.trim()
    || ![value.createdAt, value.updatedAt].every((date) => typeof date === 'string' && Number.isFinite(Date.parse(date)))
    || !Number.isSafeInteger(value.turnCount) || value.turnCount < 0) throw new Error('Invalid conversation');
  return { id: value.id, title: value.title, createdAt: value.createdAt, updatedAt: value.updatedAt, turnCount: value.turnCount };
}
export function validateConversationList(value) {
  if (!Array.isArray(value?.items) || value.items.length > 50 || typeof value.hasMore !== 'boolean') throw new Error('Invalid conversation list');
  const items = value.items.map(summary);
  if (new Set(items.map((item) => item.id)).size !== items.length) throw new Error('Duplicate conversations');
  return { items, hasMore: value.hasMore };
}
export function validateConversation(value) {
  const result = summary({ ...value, turnCount: value?.turns?.length });
  if (!Array.isArray(value.turns) || value.turns.length > 200) throw new Error('Invalid conversation history');
  const turns = value.turns.map((turn) => {
    if (typeof turn.id !== 'string' || typeof turn.idempotencyKey !== 'string' || !/^[A-Za-z0-9_-]{8,128}$/.test(turn.idempotencyKey)
      || typeof turn.question !== 'string' || !turn.question.trim() || turn.question.length > 600
      || !['completed', 'failed', 'unknown', 'pending'].includes(turn.status)
      || !Number.isFinite(Date.parse(turn.createdAt))) throw new Error('Invalid conversation turn');
    const answer = turn.status === 'completed' ? validateQuestionAnswer(turn.answer) : null;
    let error = null;
    if (turn.error) {
      if (typeof turn.error.code !== 'string' || typeof turn.error.message !== 'string' || typeof turn.error.retryable !== 'boolean') throw new Error('Invalid turn error');
      error = { code: turn.error.code, message: turn.error.message, retryable: turn.error.retryable };
    }
    return { id: turn.id, idempotencyKey: turn.idempotencyKey, question: turn.question, status: turn.status, answer, error, createdAt: turn.createdAt };
  });
  if (new Set(turns.map((turn) => turn.id)).size !== turns.length) throw new Error('Duplicate turns');
  return { ...result, turns };
}
