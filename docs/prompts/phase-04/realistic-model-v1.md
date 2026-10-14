# 第二次写实建模候选 Prompt

版本：`realistic_model_v1.0`。冻结时间：2026-10-14T12:45:54.212224+00:00（UTC）。状态：**FROZEN_FOR_REVIEW / NOT_APPROVED**。

- 角色暂名：绛绣·戏韵；方案标识 `realistic_character_proposal_v1`。正式角色ID/任务ID仍为空。
- 资产用途：`realistic_showcase_candidate_v1`，比赛主展示候选。
- 风格：`realistic` / 写实国风。
- 候选ID：`92e3d09f-57ce-49b2-8d57-1c0664a72689`，SECOND_REALISTIC_SHOWCASE版本1。
- 原JPEG SHA-256：`0170077ef813f95b2e0da4666f0a7919078d0a811ac04d61613e69a31a621095`。
- 无损预览PNG SHA-256：`7b8fb1a42bf79d0210c1571e65ae92d856fa73761d42d9cd044836764aad4d45`。
- 候选规范化快照Hash：`80a893202c9d09e508ceba0a2796a3e2b1aab54f812c6790b23177f18bde3e33`，包括风格、图片、版本及状态字段；不是仅对下面文本的Hash。
- 以下正文UTF-8 SHA-256（不含代码块及末尾换行）：`777afaa81b1e696d98dac00e695727e17c40f38983691786d52b69a40f62fad2`。

## 冻结正文

```text
Positive:
A realistic Chinese Peking Opera-inspired digital character, a single full-body standing figure based on the supplied reference image, realistic human proportions, red and gold embroidered silk-like long robe, ornate opera-inspired crown silhouette as visible in the reference, white water-sleeve-like extensions, layered fabric, clearly readable costume silhouette, detailed fabric material, game character concept, clean white studio background, suitable for image-to-3D reconstruction. This is an original visual interpretation, not a verified historical costume or identified traditional character.

Geometry guidance:
Maintain the complete head-to-foot silhouette and visible footwear. Preserve the reference pose and major costume layers. Resolve visible arms and body boundaries without inventing hidden anatomy or accessories. Keep a stable main volume; small crown rods and bead clusters may be simplified for reconstruction. Preserve the long sleeve outlines; do not require independent geometry for every bead or embroidery stitch. The unseen back is a reconstruction estimate and must be reviewed.

Negative:
No text, no watermark, no extra characters, no duplicated accessories, no distorted hands, no unrealistic anatomy, no cropped head or feet, no chibi proportions, no added weapons or costume symbols absent from the reference.
```

## 使用边界与修改规则

本正文从实际候选不可覆盖快照导出，内容逐字核对。冠饰与水袖式表达只描述图片外观，不认证历史人物、传统冠式或行当。`game character concept` 是视觉目标，不代表已具备游戏资产拓扑、骨骼绑定或动画质量。

这是人工审核与意图追踪版本，**不是批准记录**，没有新建模型。现有普通图生3D供应商接口没有正向/负向文本Prompt字段，本正文当前不会作为供应商参数发送，也不能保证生成结果服从它；输入图才是拟定图生3D参考。

冻结后不原地修改。若人审要求改图、风格、文化元素或正文，应另建版本并重算Hash、重新确认图片和费用；保留此v1历史。不能悄悄替换图片、自动生成图、调用Neural4D或继承第1次内部图许可。

图片来源仅有用户声明“百度公开资源”，具体作者、比赛展示、上传与3D衍生许可未确认。正式角色关联、文化匹配和单次建模批准仍未完成。

实际文字审校和候选快照见 [准备结果](../../evidence/phase-04/modeling/02-realistic/realistic-preparation-result.json)，审核入口见 [第二次授权表](../../reports/phase-04-second-model-approval.md)。本轮不再调用DeepSeek。
