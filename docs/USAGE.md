# Atlassian 数据爬取工具 - 使用指南

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置
复制示例配置文件并编辑：
```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，填入你的 Atlassian 实例信息：
- URL: 你的 Atlassian 域名（如 `https://your-domain.atlassian.net`）
- Username: 你的邮箱
- API Token: 在 https://id.atlassian.com/manage-profile/security/api-tokens 创建

### 3. 运行同步
```bash
# 同步所有数据源
python cli.py sync

# 只同步 Confluence
python cli.py sync --type confluence

# 只同步 Jira
python cli.py sync --type jira

# 同步特定数据源
python cli.py sync --source sakiko222-confluence
```

### 4. 查看状态
```bash
python cli.py status
```

## 输出结构

```
sources/
├── confluence/
│   └── [source-name]/
│       └── [space-key]/
│           ├── [page-title].md
│           └── attachments/
└── jira/
    └── [source-name]/
        └── [project-key]/
            └── [issue-type]/
                ├── [issue-key].md
                └── attachments/
```

## 增量更新

工具会自动跟踪已同步的内容，只下载变更的页面和 issues。状态保存在 `.atlassian-sync-state.json` 文件中。

## 错误处理

- 失败的操作会自动重试 3 次
- 错误会记录到 `sync-errors.log`
- 同步完成后会显示错误报告

## 数据格式

### Confluence 页面
- 标准 Markdown 格式
- 包含元数据：来源、作者、创建/更新时间
- 附件下载到 `attachments/` 子目录

### Jira Issues
- 标准 Markdown 格式
- 包含所有标准字段和自定义字段
- 包含评论、工作日志、关联 issues
- 包含完整的原始 JSON 数据（折叠显示）
- 按 issue type 分类存储

## 常见问题

### 如何获取 API Token？
访问 https://id.atlassian.com/manage-profile/security/api-tokens 创建新的 API token。

### 如何添加多个数据源？
在 `config.yaml` 中的 `sources.confluence` 或 `sources.jira` 数组中添加新的配置项。

### 如何重新同步所有数据？
删除 `.atlassian-sync-state.json` 文件，然后运行 `python cli.py sync`。

### 同步频率建议
- 开发环境：每天 1-2 次
- 生产环境：根据需要，建议每小时或每天
- 可以使用 cron 或 Windows 任务计划程序自动运行

## 与 llm-wiki-compiler 集成

生成的 markdown 文件可以直接作为 llm-wiki-compiler 的输入源：

1. 将 `sources/` 目录配置为 llm-wiki-compiler 的源目录
2. llm-wiki-compiler 会自动处理概念提取和结构化
3. 无需额外的数据转换步骤
