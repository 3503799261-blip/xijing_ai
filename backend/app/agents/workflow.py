"""Three model calls, one real RAG role, finite stages, no paid automatic retry."""
from ..errors import ServiceError
from . import planner, researcher, designer, reviewer
from .schemas import public_citations

AGENT_IDS = ('planner', 'researcher', 'designer', 'reviewer')
PROMPT_VERSIONS = {'planner': planner.PROMPT_VERSION, 'researcher': researcher.POLICY_VERSION,
                   'designer': designer.PROMPT_VERSION, 'reviewer': reviewer.PROMPT_VERSION}


def safe_summary(prefix: str, details=()) -> str:
    """Expose only already validated public fields, with no HTML rendering."""
    text = prefix + (' ' + '；'.join(details) if details else '')
    return text[:899] + '…' if len(text) > 900 else text


def research_summary(artifact: dict) -> str:
    missing = [query['question'] for query in artifact['queries'] if query.get('effectiveUncertain', query['uncertain'])]
    if artifact.get('uncertain', bool(missing) or not artifact['evidence']):
        return safe_summary('资料不足，尚未生成角色。',
                            ['未覆盖查询：' + '；'.join(missing)] + artifact['limitations'])
    return safe_summary(f"完成{len(artifact['queries'])}条真实检索，保留{len(artifact['evidence'])}条候选依据。")


def review_summary(artifact: dict) -> str:
    prefix = {'pass': '辅助文化审校已完成，需由用户决定是否接受方案。',
              'needs_revision': '辅助文化审校发现需修订内容，不能直接接受为最终方案。',
              'insufficient_evidence': '辅助文化审校判定资料不足，不能作为已核实设计。'}[artifact['verdict']]
    return safe_summary(prefix, [issue['field'] + '：' + issue['reason'] for issue in artifact['issues']])


async def run_workflow(runtime, task_id, brief: dict, emit, cancelled=lambda: False) -> dict:
    """Persist actual role boundaries through emit; supervisor owns task state."""
    result = {'schemaVersion': '1.0', 'design': None, 'review': None, 'citations': [],
              'uncertain': True, 'publicationAllowed': False,
              'knowledgeGeneration': (runtime.manifest or {}).get('generation_id'),
              'promptVersions': dict(PROMPT_VERSIONS), 'limitations': []}

    def check_cancelled():
        if cancelled():
            raise ServiceError('WORKFLOW_CANCELLED', '创作已取消，未执行后续阶段。', 409)

    async def step(agent_id, operation, summary, state_for=lambda artifact: 'completed'):
        check_cancelled()
        await emit(agent_id, 'running', summary='正在执行此阶段；结果将在校验后展示。')
        try:
            artifact = await operation()
        except ServiceError as exc:
            await emit(agent_id, 'failed', summary=exc.message, error_code=exc.code,
                       artifact=getattr(exc, 'diagnostic_artifact', None))
            raise
        except Exception:
            await emit(agent_id, 'failed', summary='此阶段发生内部错误，未执行后续创作。', error_code='AGENT_INTERNAL')
            raise ServiceError('AGENT_INTERNAL', '创作阶段暂不可用，未执行后续步骤。', 500)
        # Commit an artifact only once. A clarification/evidence hold is the
        # stage's final state, never a completed -> awaiting transition.
        await emit(agent_id, state_for(artifact), summary=summary(artifact), artifact=artifact)
        check_cancelled()
        return artifact

    # The task store seeds pending states. Re-emitting them is unnecessary and
    # could imply a second execution when a task is restored after a restart.
    plan = await step('planner', lambda: planner.plan_creation(brief, runtime.provider, f'{task_id}:planner'),
                      lambda value: (safe_summary('请补充关键需求后重新提交创作：', value['clarificationQuestions']) if value['clarificationQuestions']
                                     else f"已整理主题「{value['theme']}」及{len(value['requirements'])}项需求。"),
                      lambda value: 'awaiting_confirmation' if value['clarificationQuestions'] else 'completed')
    if plan['clarificationQuestions']:
        result.update(confirmationReason='clarification', limitations=plan['clarificationQuestions'])
        return result

    research = await step('researcher', lambda: researcher.research_opera(plan, runtime, cancelled),
                          research_summary,
                          lambda value: 'awaiting_confirmation'
                          if value['uncertain'] else 'completed')
    result['limitations'] = list(research['limitations'])
    result['knowledgeGeneration'] = research['knowledgeGeneration']
    if research['uncertain']:
        result['confirmationReason'] = 'insufficient_evidence'
        return result

    design = await step('designer', lambda: designer.design_character(brief, plan, research, runtime.provider, f'{task_id}:designer'),
                        lambda value: f"已生成原创角色「{value['name']}」草案，尚待文化审校。")
    review = await step('reviewer', lambda: reviewer.review_culture(brief, plan, research, design, runtime.provider, f'{task_id}:reviewer'),
                        review_summary)
    result.update(design=design, review=review,
                  citations=public_citations(research['evidence'],
                                             design['usedEvidenceIds'] + review['checkedEvidenceIds']),
                  uncertain=review['verdict'] != 'pass',
                  confirmationReason='final_acceptance' if review['verdict'] == 'pass' else review['verdict'])
    result['limitations'].extend(design['limitations'])
    # Four completed stages mean the process ran, never that human confirmation
    # or expert certification has happened. Publication remains forbidden here.
    return result
