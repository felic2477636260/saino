# Baselines

该目录用于保存真实 API 条件下生成的对照产物：

- `prompts/direct_doubao_prompt.txt`
  用于在外部平台复现实验时保持相同用户 prompt。
- `outputs/*_legacy.json`
  旧链路在真实 API 下的输出结果。
- `outputs/*_optimized.json`
  当前多阶段链路在真实 API 下的输出结果。
- `outputs/direct_doubao_template.json`
  外部平台基线模板，可与 `scripts/run_eval.py` 一起做对比。

生成 before / after 对照样例前，请先完成真实 API 配置：

```bash
python -m scripts.run_baseline --company-code 002555 --query "请生成企业体检报告" --mode legacy
python -m scripts.run_baseline --company-code 002555 --query "请生成企业体检报告" --mode optimized
```

仓库不再保留 mock 输出作为评测或展示样例。
