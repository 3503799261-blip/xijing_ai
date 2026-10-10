"""Reusable real semantic retrieval, separated from chat and the LLM."""
import time
from ..errors import ServiceError

class SearchService:
    def __init__(self, embedding, store, vectors, min_score=0.57):
        self.embedding, self.store, self.vectors = embedding, store, vectors
        self.min_score = min_score

    def search(self, question: str, top_k=5, category=None, mode='vector') -> dict:
        started = time.perf_counter()
        try: vector = self.embedding.encode_query(question)
        except ValueError:
            raise ServiceError('QUESTION_TOKEN_LIMIT', '问题超过Embedding长度限制，请缩短后重试。', 400)
        vector_hits = self.vectors.search(vector, limit=min(10, max(top_k, 5)), category=category)
        scores = {h['chunk_id']: h['score'] for h in vector_hits}
        ids = [h['chunk_id'] for h in vector_hits]
        keyword = {}
        if mode == 'hybrid':
            lexical = self.store.lexical_search(question, limit=10)
            keyword = {h['chunk_id']: h['keyword_score'] for h in lexical}
            ranking = {cid: 1/(60+i) for i, cid in enumerate(ids, 1)}
            for i, hit in enumerate(lexical, 1):
                ranking[hit['chunk_id']] = ranking.get(hit['chunk_id'], 0) + 1/(60+i)
            ids = sorted(ranking, key=ranking.get, reverse=True)
        evidence = []
        for cid in ids:
            # Lexical-only hits are not promoted as semantic evidence; retain vector quality gate.
            if cid not in scores or scores[cid] < self.min_score: continue
            chunk = self.store.chunk(cid)
            if category and chunk['category'] != category: continue
            source = chunk['source']
            evidence.append({'id': cid, 'chunkId': cid, 'sourceId': chunk['source_id'], 'sectionId': chunk['section_id'], 'title': source['title'], 'locator': chunk['locator'], 'url': source['source_url'], 'excerpt': chunk['content'], 'contentKind': source['content_kind'], 'category': chunk['category'], 'entityNames': chunk['entity_names'], 'vectorScore': scores[cid], 'keywordScore': keyword.get(cid), 'rank': len(evidence)+1, 'reviewStatus': source['review_status']})
            if len(evidence) >= top_k: break
        return {'question': question, 'evidence': evidence, 'uncertain': not bool(evidence), 'retrievalMode': mode, 'elapsedSeconds': round(time.perf_counter()-started, 4), 'threshold': self.min_score, 'candidateScores': [{'chunkId': h['chunk_id'], 'score': h['score']} for h in vector_hits]}
