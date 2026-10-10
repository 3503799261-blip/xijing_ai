# 京剧知识资料（Phase 2）

`documents/*.json` 是12个真实来源的原创事实摘要，共35个短主题段落。入库以文档JSON为输入；`sources.json` 是清单，不能作为额外文档重复入库。

所有资料标为 `content_kind=original_fact_summary`、`review_status=source_checked_by_assistant`。它们经过助手对照来源检查，人工复核仍待用户完成。来源机构与真实页面链接用于事实追溯，不意味着摘要原句来自该机构。

`redistribution_allowed` 与 `external_llm_allowed` 只覆盖用户批准的本项目原创摘要展示／复现及云问答，不覆盖来源全文、图片或其他受限材料。详见 [来源与审校记录](../docs/architecture/knowledge-provenance.md)。

每个 section ID 稳定并对应真实页面定位。`content_hash`、实际 chunk ID 和向量维度由入库程序运行后计算。文档更新应增加版本并重建关联索引。

评价题位于 `evaluation/questions.json`，共20题（18个支持、2个不足，至少3题需跨来源）。题目与证据均为 `assistant_source_checked_candidate`；未经真实人工复核，不能将其评价称为人工 gold Recall 或人工正确率。

本目录不包含来源全文、API凭证、向量数据库或硬编码聊天回答；知识摘要是供真实检索使用的资料，不是问答接口返回模板。

2026-10-10浏览器推荐题回归后，cnpoc-face与cnpoc-bao版本增为1.0.1：只补“脸谱”实体标签以帮助泛问颜色检索，事实正文不变；真实更新索引及前后实验保存在evidence。其他文档仍为1.0.0。不能将此元数据修复称为新增权威文献。

