# 可观测性使用指南

本文档介绍如何使用 Prometheus 指标收集和 OpenTelemetry 分布式追踪功能。

---

## 📦 安装依赖

**重要**: 可观测性依赖是**可选的**。如果不安装这些依赖，系统会自动禁用可观测性功能，但不会影响核心功能的正常运行。

```bash
# 安装所有可观测性依赖
pip install -r requirements-observability.txt

# 或者只安装需要的部分
pip install prometheus-client  # 仅 Prometheus 指标
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc  # 仅 OpenTelemetry 追踪
```

**优雅降级**: 
- 如果未安装 `prometheus-client`，指标收集会自动禁用，并在日志中显示警告
- 如果未安装 `opentelemetry`，分布式追踪会自动禁用，并在日志中显示警告
- 核心功能不受影响，可以正常使用

---

## 📊 Prometheus 指标收集

### 启用指标收集

在 `config.yaml` 中添加：

```yaml
observability:
  metrics:
    enabled: true
    port: 9090  # Metrics endpoint port
```

或在代码中配置：

```python
from crawler.observability import configure_metrics

# 启用指标收集
metrics = configure_metrics(enabled=True, port=9090)

# 启动 HTTP 服务器
metrics.start_server()
```

### 访问指标

启动应用后，访问：
```
http://localhost:9090/metrics
```

### 可用指标

#### Counter（计数器）

| 指标名称 | 说明 | 标签 |
|---------|------|------|
| `sync_requests_total` | 同步请求总数 | source_type, source_name, status |
| `llm_requests_total` | LLM 请求总数 | provider, model, status |
| `llm_tokens_total` | LLM Token 使用总数 | provider, model, token_type |

#### Histogram（直方图）

| 指标名称 | 说明 | 标签 |
|---------|------|------|
| `sync_duration_seconds` | 同步操作耗时 | source_type, source_name |
| `llm_response_time_seconds` | LLM 响应时间 | provider, model |

#### Gauge（仪表盘）

| 指标名称 | 说明 | 标签 |
|---------|------|------|
| `active_syncs` | 活跃同步操作数 | source_type |
| `cache_size_bytes` | 缓存大小 | cache_type |

### 在代码中使用指标

```python
from crawler.observability import get_metrics_collector

metrics = get_metrics_collector()

# 使用装饰器追踪同步操作
@metrics.track_sync("confluence", "my-source")
def sync_confluence_space(space_key: str):
    # 同步逻辑
    pass

# 使用装饰器追踪 LLM 调用
@metrics.track_llm("openai", "gpt-4")
def generate_text(prompt: str):
    # LLM 调用逻辑
    pass

# 使用上下文管理器
with metrics.track_active_sync("jira"):
    # 执行同步操作
    pass

# 记录 LLM token 使用
metrics.record_llm_tokens(
    provider="openai",
    model="gpt-4",
    prompt_tokens=100,
    completion_tokens=50
)

# 更新缓存大小
metrics.update_cache_size("wiki", 1024 * 1024)  # 1MB
```

---

## 🔍 OpenTelemetry 分布式追踪

### 启用追踪

在 `config.yaml` 中添加：

```yaml
observability:
  tracing:
    enabled: true
    service_name: "crawler"
    otlp_endpoint: "http://localhost:4317"  # Jaeger OTLP endpoint
    console_export: false  # 调试时设为 true
```

或在代码中配置：

```python
from crawler.observability import TracingConfig, configure_tracing

# 配置追踪
config = TracingConfig(
    enabled=True,
    service_name="crawler",
    otlp_endpoint="http://localhost:4317",
    console_export=False
)

tracer = configure_tracing(config)
```

### 在代码中使用追踪

#### 使用装饰器

```python
from crawler.observability import trace_operation, trace_sync_operation, trace_llm_call

# 通用操作追踪
@trace_operation("process_page", {"page_type": "confluence"})
def process_page(page_id: str):
    # 处理逻辑
    pass

# 同步操作追踪
@trace_sync_operation("confluence", "my-source")
def sync_space(space_key: str):
    # 同步逻辑
    pass

# LLM 调用追踪
@trace_llm_call("openai", "gpt-4")
def generate_analysis(issue_key: str):
    # LLM 调用逻辑
    pass
```

#### 使用上下文管理器

```python
from crawler.observability import trace_span, add_span_attributes, add_span_event

# 创建 span
with trace_span("download_attachments", {"count": 5}):
    for attachment in attachments:
        # 下载附件
        add_span_event("attachment_downloaded", {"id": attachment.id})
    
    # 添加结果属性
    add_span_attributes({"total_size": total_size, "errors": 0})
```

#### 嵌套 span

```python
from crawler.observability import trace_span

with trace_span("sync_all_sources"):
    for source in sources:
        with trace_span("sync_source", {"source": source.name}):
            # 同步单个源
            pass
```

---

## 🚀 部署指南

### 1. 启动 Prometheus

使用 Docker：

```bash
docker run -d \
  --name prometheus \
  -p 9091:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

`prometheus.yml` 配置：

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'crawler'
    static_configs:
      - targets: ['host.docker.internal:9090']
```

### 2. 启动 Jaeger

使用 Docker：

```bash
docker run -d \
  --name jaeger \
  -p 4317:4317 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

访问 Jaeger UI: `http://localhost:16686`

### 3. 导入 Grafana 仪表板

1. 访问 Grafana: `http://localhost:3000`
2. 添加 Prometheus 数据源
3. 导入 `grafana/crawler-dashboard.json`

---

## 📈 监控查询示例

### Prometheus 查询

```promql
# 同步请求速率
rate(sync_requests_total[5m])

# 同步成功率
sum(rate(sync_requests_total{status="success"}[5m])) / sum(rate(sync_requests_total[5m])) * 100

# P95 同步耗时
histogram_quantile(0.95, rate(sync_duration_seconds_bucket[5m]))

# LLM 错误率
rate(llm_requests_total{status="error"}[5m])

# 活跃同步操作数
active_syncs

# Token 使用速率
rate(llm_tokens_total[5m])
```

### 告警规则

在 Prometheus 中配置告警：

```yaml
groups:
  - name: crawler_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(sync_requests_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} req/s"

      - alert: SlowSyncOperations
        expr: histogram_quantile(0.95, rate(sync_duration_seconds_bucket[5m])) > 300
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow sync operations"
          description: "P95 sync duration is {{ $value }}s"

      - alert: HighLLMLatency
        expr: histogram_quantile(0.95, rate(llm_response_time_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High LLM latency"
          description: "P95 LLM response time is {{ $value }}s"
```

---

## 🧪 测试可观测性

### 测试指标收集

```python
import time
from crawler.observability import configure_metrics

# 配置并启动
metrics = configure_metrics(enabled=True, port=9090)
metrics.start_server()

# 模拟同步操作
@metrics.track_sync("confluence", "test-source")
def test_sync():
    time.sleep(2)
    return {"pages": 10}

# 执行操作
result = test_sync()

# 访问 http://localhost:9090/metrics 查看指标
```

### 测试追踪

```python
from crawler.observability import TracingConfig, configure_tracing, trace_span

# 配置追踪（输出到控制台）
config = TracingConfig(
    enabled=True,
    service_name="test-crawler",
    console_export=True
)
configure_tracing(config)

# 创建追踪
with trace_span("test_operation", {"test": "true"}):
    time.sleep(1)
    print("Operation completed")

# 查看控制台输出的追踪信息
```

---

## 📊 Grafana 仪表板

仪表板包含以下面板：

1. **Sync Requests Rate** - 同步请求速率
2. **Sync Duration (p95)** - 同步耗时 P95
3. **LLM Requests Rate** - LLM 请求速率
4. **LLM Response Time (p95)** - LLM 响应时间 P95
5. **Active Sync Operations** - 活跃同步操作数
6. **LLM Token Usage** - Token 使用速率
7. **Cache Size** - 缓存大小
8. **Error Rate** - 错误率（带告警）
9. **Success Rate** - 成功率
10. **Total Requests (24h)** - 24小时总请求数
11. **Avg Sync Duration** - 平均同步耗时
12. **Avg LLM Response Time** - 平均 LLM 响应时间

---

## 🔧 故障排查

### 指标端点无法访问

1. 检查端口是否被占用：`netstat -an | grep 9090`
2. 检查防火墙设置
3. 确认 `metrics.start_server()` 已调用

### 追踪数据未显示

1. 检查 Jaeger 是否运行：`docker ps | grep jaeger`
2. 检查 OTLP 端点配置是否正确
3. 查看应用日志中的追踪配置信息

### Grafana 无数据

1. 检查 Prometheus 数据源配置
2. 确认 Prometheus 能访问指标端点
3. 检查查询语句是否正确

---

## 📚 参考资料

- [Prometheus Documentation](https://prometheus.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
