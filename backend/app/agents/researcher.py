"""Research is a real Phase 2 RAG tool call, not a fourth model conversation."""
from ..errors import ServiceError

POLICY_VERSION = 'agent_research_v1'


def _retrieve(runtime, question: str) -> dict:
    """Called exclusively on Runtime's existing SQLite/Qdrant owner thread."""
    result = runtime.search_service.search(question, top_k=5, category=None,
                                          mode=runtime.settings.retrieval_mode)
    permitted = []
    for item in result['evidence']:
        chunk = runtime.store.chunk(item['id'])
        source = chunk['source']
        if source.get('external_llm_allowed') is not True:
            continue
        if (item['id'] != chunk['chunk_id'] or item['excerpt'] != chunk['content']
                or item['sourceId'] != chunk['source_id']):
            raise ServiceError('AGENT_EVIDENCE_INVALID', '研究证据与资料库记录不一致，已停止创作。', 503)
        permitted.append({**item, 'sourceVersion': source['document_version'],
                          'sourceContentHash': source['content_hash'],
                          'chunkContentHash': chunk['content_hash']})
    return {**result, 'evidence': permitted, 'uncertain': not bool(permitted)}


async def research_opera(plan: dict, runtime, cancelled=lambda: False) -> dict:
    queries, candidates = [], {}
    for question in plan['researchQueries']:
        if cancelled():
            raise ServiceError('WORKFLOW_CANCELLED', '创作已取消，未执行后续阶段。', 409)
        result = await runtime.knowledge(lambda question=question: _retrieve(runtime, question))
        queries.append({'question': question, 'evidenceIds': [item['id'] for item in result['evidence']],
                        'uncertain': result['uncertain'], 'elapsedSeconds': result['elapsedSeconds'],
                        'retrievalMode': result['retrievalMode']})
        for item in result['evidence']:
            previous = candidates.get(item['id'])
            if previous is None or item['rank'] < previous['rank']:
                candidates[item['id']] = item
    # Round-robin keeps evidence from every subquery instead of consuming five
    # slots with the first query. Ties retain actual per-query retrieval order.
    selected = []
    for offset in range(5):
        for query in queries:
            ids = query['evidenceIds']
            if offset < len(ids) and ids[offset] not in selected:
                selected.append(ids[offset])
            if len(selected) == 5:
                break
        if len(selected) == 5:
            break
    evidence = [candidates[cid] for cid in selected]
    coverage = [{'requirementId': item['id'], 'status': 'candidate' if evidence else 'missing',
                 'evidenceIds': selected} for item in plan['requirements']]
    limitations = ['检索结果仅为候选依据，不代表用户前提成立；适用范围由文化审校继续核查。',
                   '来源为项目原创事实摘要，助手已核对来源，尚未经过京剧专家审核。']
    if not evidence:
        limitations.append('现有资料没有可交给模型的有效证据，请调整文化要求或补充获准资料。')
    elif any(query['uncertain'] for query in queries):
        limitations.append('部分研究问题没有有效资料；设计和审校不得补造这些文化事实。')
    return {'queries': queries, 'evidence': evidence, 'requirementCoverage': coverage,
            'limitations': limitations, 'knowledgeGeneration': (runtime.manifest or {}).get('generation_id'),
            'policyVersion': POLICY_VERSION}
