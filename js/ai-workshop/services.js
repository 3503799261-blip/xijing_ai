import { SERVICE_CAPABILITIES, SERVICE_MESSAGES } from './contracts.js';

/** 当前阶段所有 AI 能力都未接入；未来仅在此服务边界对接受保护的后端。 */
export function getServiceCapabilities() {
  return SERVICE_CAPABILITIES;
}

/** @param {import('./contracts.js').Capability} capability */
function unavailable(capability) {
  return Object.freeze({
    available: false,
    status: 'unavailable',
    capability,
    message: SERVICE_MESSAGES[capability],
  });
}

/**
 * @param {import('./contracts.js').QuestionRequest} _request
 * @returns {Promise<import('./contracts.js').UnavailableResult>}
 */
export async function askOperaQuestion(_request) {
  return unavailable('questionAnswering');
}

/**
 * @param {import('./contracts.js').CreationBrief} _brief
 * @returns {Promise<import('./contracts.js').UnavailableResult>}
 */
export async function startAgentWorkflow(_brief) {
  return unavailable('agentWorkflow');
}

/**
 * @param {import('./contracts.js').CreationBrief} _brief
 * @returns {Promise<import('./contracts.js').UnavailableResult>}
 */
export async function generateConceptImage(_brief) {
  return unavailable('conceptImage');
}

/**
 * @param {{imageId: string}} _request
 * @returns {Promise<import('./contracts.js').UnavailableResult>}
 */
export async function submitModelTask(_request) {
  return unavailable('imageToModel');
}
