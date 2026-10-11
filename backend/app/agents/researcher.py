"""Research is a real Phase 2 RAG tool call, not a fourth model conversation."""
import re
from ..errors import ServiceError

POLICY_VERSION = 'agent_research_v4'
MAX_RETRIEVALS = 3


def _retrieve(runtime, question: str, required_entities=()) -> dict:
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
    catalog = getattr(runtime.search_service, 'entities', set())
    known = [entity for entity in required_entities if entity in catalog]
    # Only corpus metadata on the existing owner thread can supply expansion
    # terms. No invented synonyms, culture facts, new model, or Qdrant client.
    names = {term for chunk in runtime.store.all_chunks() for term in chunk['entity_names']} if known else set()
    expansions = {entity: sorted((term for term in names if 2 <= len(term) <= 40
                                  and term != entity and entity in term and term in catalog),
                                 key=lambda term: (len(term), term))[:3] for entity in known} if known else {}
    return {**result, 'evidence': permitted, 'uncertain': result['uncertain'] or not bool(permitted),
            '_entityExpansions': expansions}


def contains_entity(item: dict, entity: str) -> bool:
    return entity in item['excerpt'] or entity in item.get('entityNames', [])


def select_evidence(queries: list, candidates: dict, required_entities: list) -> list:
    # Keep one literal candidate for each required entity before filling the
    # remaining slots round-robin. This is coverage, not semantic validation.
    selected = []
    ordered = list(dict.fromkeys(cid for query in queries for cid in query['evidenceIds']))
    for entity in required_entities:
        cid = next((cid for cid in ordered if contains_entity(candidates[cid], entity)), None)
        if cid is not None and cid not in selected:
            selected.append(cid)
    for offset in range(5):
        for query in queries:
            ids = query['evidenceIds']
            if offset < len(ids) and ids[offset] not in selected:
                selected.append(ids[offset])
            if len(selected) == 5:
                return [candidates[cid] for cid in selected]
    return [candidates[cid] for cid in selected]


async def research_opera(plan: dict, runtime, cancelled=lambda: False) -> dict:
    queries, candidates, expansions = [], {}, {}
    required_entities = plan.get('requiredEntities', [])

    async def retrieve(question, origin='plan', entity=None, expanded_terms=()):
        if cancelled():
            raise ServiceError('WORKFLOW_CANCELLED', '创作已取消，未执行后续阶段。', 409)
        result = await runtime.knowledge(lambda: _retrieve(runtime, question, required_entities))
        expansions.update(result['_entityExpansions'])
        # Similarity to another premiere/person is not evidence for an exact
        # dated premise. This conservative textual check is deliberately narrow,
        # not a general semantic or historical truth validator.
        years = re.findall(r'(?<!\d)(1\d{3}|20\d{2})年(?!\d)', question)
        missing_years = [year for year in years if not any(year in item['excerpt'] for item in result['evidence'])]
        checked_entities = [entity] if entity else [term for term in required_entities if term in question]
        missing_entities = [term for term in checked_entities
                            if not any(contains_entity(item, term) for item in result['evidence'])]
        queries.append({'question': question, 'evidenceIds': [item['id'] for item in result['evidence']],
                        'origin': origin, 'expandedTerms': list(expanded_terms), 'recheckedEntity': entity,
                        'uncertain': result['uncertain'] or bool(missing_years) or bool(missing_entities),
                        'retrievalUncertain': result['uncertain'], 'missingYears': missing_years,
                        'missingEntities': missing_entities, 'resolvedBy': [],
                        'retrievalScores': [{key: item.get(key) for key in ('id', 'rank', 'vectorScore', 'keywordScore')}
                                            for item in result['evidence']],
                        'elapsedSeconds': result['elapsedSeconds'],
                        'retrievalMode': result['retrievalMode']})
        if 'candidateScores' in result:
            queries[-1]['candidateScores'] = result['candidateScores']
        for item in result['evidence']:
            previous = candidates.get(item['id'])
            if previous is None or item['rank'] < previous['rank']:
                candidates[item['id']] = item

    for question in plan['researchQueries'][:MAX_RETRIEVALS]:
        await retrieve(question)
    missing_initial = [entity for entity in required_entities
                       if not any(contains_entity(item, entity) for item in candidates.values())]
    for entity in missing_initial:
        terms = expansions.get(entity, [])
        if len(queries) == MAX_RETRIEVALS:
            break
        if terms:
            await retrieve('京剧 ' + ' '.join([entity, *terms]), 'entity_recheck', entity, terms)
    resolved = {query['recheckedEntity']: index for index, query in enumerate(queries)
                if query['origin'] == 'entity_recheck' and not query['uncertain']}
    for query in queries:
        # Preserve the original uncertainty. A successful catalog recheck may
        # resolve only its missing entity; no dates or unrelated uncertainty.
        can_resolve = (query['origin'] == 'plan' and query['missingEntities']
                       and not query['missingYears']
                       and all(entity in resolved for entity in query['missingEntities']))
        query['effectiveUncertain'] = bool(query['uncertain'] and not can_resolve)
        if can_resolve:
            query['resolvedBy'] = [resolved[entity] for entity in query['missingEntities']]
    evidence = select_evidence(queries, candidates, required_entities)
    selected = [item['id'] for item in evidence]
    missing_entities = [entity for entity in plan.get('requiredEntities', [])
                        if not any(contains_entity(item, entity) for item in evidence)]
    uncertain = not bool(evidence) or bool(missing_entities) or any(query['effectiveUncertain'] for query in queries)
    coverage = [{'requirementId': item['id'], 'status': 'candidate' if evidence else 'missing',
                 'evidenceIds': selected} for item in plan['requirements']]
    limitations = ['检索结果仅为候选依据，不代表用户前提成立；适用范围由文化审校继续核查。',
                   '来源为项目原创事实摘要，助手已核对来源，尚未经过京剧专家审核。']
    if any(query['origin'] == 'entity_recheck' for query in queries):
        limitations.append('补查仅使用已有资料元数据中的相关词；词同现仅表示候选覆盖，语义支持仍需文化审校及用户核对。')
    if not evidence:
        limitations.append('现有资料没有可交给模型的有效证据，请调整文化要求或补充获准资料。')
    elif uncertain:
        limitations.append('部分研究问题没有有效资料；设计和审校不得补造这些文化事实。')
    if missing_entities:
        limitations.append('未找到指定人物或传统名称的精确依据：' + '、'.join(missing_entities) + '；相似人物不能替代。')
    missing_years = list(dict.fromkeys(year for query in queries for year in query['missingYears']))
    if missing_years:
        limitations.append('候选资料未记载指定年份：' + '、'.join(missing_years) + '年；其他首演年份不能替代。')
    return {'queries': queries, 'evidence': evidence, 'requirementCoverage': coverage,
            'limitations': limitations, 'knowledgeGeneration': (runtime.manifest or {}).get('generation_id'),
            'missingEntities': missing_entities, 'uncertain': uncertain, 'policyVersion': POLICY_VERSION}
