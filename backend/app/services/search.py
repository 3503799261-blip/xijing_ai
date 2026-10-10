"""Reusable real semantic retrieval, separated from chat and the LLM."""
import time
from ..errors import ServiceError

class SearchService:
    def __init__(self, embedding, store, vectors, min_score=0.57):
        self.embedding, self.store, self.vectors = embedding, store, vectors
        self.min_score = min_score
        self.entities = {entity for chunk in store.all_chunks() for entity in chunk['entity_names']} if hasattr(store, 'all_chunks') else set()

    def matched_entities(self, question):
        singles = [term for term in self.entities if len(term) == 1 and term in question]
        terms = [term for term in self.entities if len(term) >= 2 and term not in {'京剧', '行当', '角色'} and term in question]
        compound_singles = set(singles) if len(singles) >= 2 else set()
        terms.extend(compound_singles)
        return sorted({term for term in terms if term in compound_singles or not any(term != longer and term in longer for longer in terms)}, key=lambda term: (-len(term), term))

    def search(self, question: str, top_k=5, category=None, mode='vector') -> dict:
        started = time.perf_counter()
        try: vector = self.embedding.encode_query(question)
        except ValueError:
            raise ServiceError('QUESTION_TOKEN_LIMIT', '问题超过Embedding长度限制，请缩短后重试。', 400)
        vector_hits = self.vectors.search(vector, limit=10 if mode == 'hybrid' else min(10, max(top_k, 5)), category=category)
        scores = {h['chunk_id']: h['score'] for h in vector_hits}
        ids = [h['chunk_id'] for h in vector_hits]
        keyword = {}
        entity_coverage = {}
        matched_entities = []
        if mode == 'hybrid':
            matched_entities = self.matched_entities(question)
            lexical = self.store.lexical_search(question, limit=10, entity_terms=matched_entities)
            missing = [hit['chunk_id'] for hit in lexical if hit['chunk_id'] not in scores]
            extra_vectors = self.vectors.search(vector, limit=10, category=category, candidate_ids=missing) if missing else []
            scores.update({hit['chunk_id']: hit['score'] for hit in extra_vectors})
            keyword = {h['chunk_id']: h['keyword_score'] for h in lexical}
            ranking = {cid: 1/(60+i) for i, cid in enumerate(ids, 1)}
            for i, hit in enumerate(lexical, 1):
                ranking[hit['chunk_id']] = ranking.get(hit['chunk_id'], 0) + 1/(60+i)
            # Exact metadata entities distinguish "净" from "正净" and a
            # broad taxonomy mention from sections addressing the named roles.
            # RRF breaks ties; this is an explicit lexical re-ranker, not a
            # reranker model or a new semantic score.
            entity_coverage = {cid: sum(term in self.store.chunk(cid)['entity_names'] for term in matched_entities) for cid in ranking}
            ids = sorted(ranking, key=lambda cid: (entity_coverage[cid], ranking[cid]), reverse=True)
        evidence = []
        for cid in ids:
            # Exact corpus entities provide an explicit lexical route for short
            # summaries. Their actual Qdrant scores are never relabelled as
            # having passed the semantic threshold. The answer layer still
            # checks evidence support of all question premises.
            if cid not in scores or (scores[cid] < self.min_score and cid not in keyword and not entity_coverage.get(cid)): continue
            chunk = self.store.chunk(cid)
            if category and chunk['category'] != category: continue
            source = chunk['source']
            evidence.append({'id': cid, 'chunkId': cid, 'sourceId': chunk['source_id'], 'sectionId': chunk['section_id'], 'title': source['title'], 'locator': chunk['locator'], 'url': source['source_url'], 'excerpt': chunk['content'], 'contentKind': source['content_kind'], 'category': chunk['category'], 'entityNames': chunk['entity_names'], 'vectorScore': scores[cid], 'keywordScore': keyword.get(cid), 'entityMatchCount': entity_coverage.get(cid, 0), 'acceptedBy': 'vector_threshold' if scores[cid] >= self.min_score else ('exact_entity_keyword' if cid in keyword else 'exact_entity_metadata'), 'rank': len(evidence)+1, 'reviewStatus': source['review_status']})
            if len(evidence) >= top_k: break
        return {'question': question, 'evidence': evidence, 'uncertain': not bool(evidence), 'retrievalMode': mode, 'matchedEntities': matched_entities, 'elapsedSeconds': round(time.perf_counter()-started, 4), 'threshold': self.min_score, 'candidateScores': [{'chunkId': h['chunk_id'], 'score': h['score']} for h in vector_hits]}
