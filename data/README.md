# Data Directory

上传资料和系统原始资料统一放在 `data/raw` 下，推荐结构如下：

```text
data/
  raw/
    company/<company_code>/
    research/<company_code>/
    industry/<company_code>/
  export/
```

说明：

- `company/<company_code>/`
  公司年报、季报、公告、产品说明等原始资料。
- `research/<company_code>/`
  券商研报、专题研究、跟踪报告等外部研究资料。
- `industry/<company_code>/`
  政策、行业趋势、竞品对比、外部环境资料。
- `export/`
  导出的报告文件或中间产物。

前端上传后，文件会按“资料分类 + 公司代码”自动写入上述目录，并立即进入解析与检索链路。
