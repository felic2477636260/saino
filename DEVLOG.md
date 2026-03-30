# DEVLOG

## 2026-03-14

### Objective

初始化 Saino MVP，打通 `ingest -> retrieve -> analyze -> export` 主链路。

### Completed

- 建立项目目录、配置、数据库 schema 与基础文档
- 实现 PDF 解析、分块、检索与 Skill 注册
- 实现 FastAPI、前端工作台、baseline 与最小测试
- 为 `/health` 增加真实 LLM 配置状态回显

### Notes

- 当前主流程已经统一为真实 Ark API 调用
- mock / fake response 方案已从主链路移除

## 2026-03-15

### Objective

修复第一轮前端改版后的明显可用性问题。

### Completed

- 移除主查询输入框中的 prompt 风格默认文案
- 提升侧边栏对比度与可读性
- 保留 PDF 导出能力并验证前端仍可编译

### Verification

- `python -m py_compile app.py`
- `python -m pytest -q`
