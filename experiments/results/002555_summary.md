# 002555 样例对比

- 对比对象：`baselines/outputs/002555_legacy.json` vs `baselines/outputs/002555_optimized.json`
- 查询：`请生成企业体检报告`
- 当前外部平台基线：请在 `baselines/outputs/direct_doubao_template.json` 中手动录入同模型同 prompt 输出后再加入对比

当前规则评分结果：

- `structure_integrity`: legacy `84` -> optimized `100`，增量 `+16`
- `evidence_traceability`: legacy `60` -> optimized `100`，增量 `+40`
- `risk_reasonableness`: legacy `65` -> optimized `77`，增量 `+12`
- `recommendation_usefulness`: legacy `72` -> optimized `96`，增量 `+24`
- `non_repetition`: legacy `100` -> optimized `100`，增量 `0`

从样例可以看到，优化后的主要优势不是“更长”，而是：

- 有明确的 `analysis_plan`
- 有分专题 evidence pack 和 skill outputs
- 有 `verification_notes` 显式暴露证据边界
- 有统一 `report_payload`，可直接供前端、HTML、Markdown、PDF 渲染
