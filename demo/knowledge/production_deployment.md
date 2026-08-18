# 生产环境部署规范与 SRE 最佳实践

> **版本**: v3.2.1 | **适用**: 生产环境 K8s 集群 | **最后更新**: 2026-08-01

---

## 第 1 章：Kubernetes 部署规范

### 1.1 Deployment 标准模板

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: production
  labels:
    app: payment-service
    tier: backend
    criticality: high
spec:
  replicas: 3
  revisionHistoryLimit: 5

  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # 零停机部署

  minReadySeconds: 30

  selector:
    matchLabels:
      app: payment-service

  template:
    metadata:
      labels:
        app: payment-service
    spec:
      # 容器资源 — 这是 MTTR 的关键
      containers:
        - name: payment-service
          image: registry.internal/payment-service:3.2.1
          ports:
            - containerPort: 8080
              protocol: TCP

          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi        # ★ 必须设置，防止 OOMKilled

          # 存活探针 — 失败则重启容器
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 60   # 给 JVM 足够启动时间
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3

          # 就绪探针 — 失败则从 Service 移除
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 2

          # 优雅关闭
          lifecycle:
            preStop:
              exec:
                command:
                  - /bin/sh
                  - -c
                  - |
                    sleep 15 &&                    # 等待 Service 端点移除
                    kill -SIGTERM 1                # 优雅关闭 JVM

      # 优雅关闭最长等待时间
      terminationGracePeriodSeconds: 45

      # Pod 反亲和 — 避免同节点
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: payment-service
                topologyKey: kubernetes.io/hostname
```

### 1.2 HPA 自动伸缩

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: payment-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  minReplicas: 3
  maxReplicas: 10
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # 5min 稳定窗口
      policies:
        - type: Pods
          value: 1                      # 每分钟最多缩 1 个 Pod
          periodSeconds: 60
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 80
    - type: Resource
      resource:
        name: memory
        target:
          type: AverageValue
          averageValue: 800Mi
```

---

## 第 2 章：JVM 生产配置

### 2.1 Docker 容器 JVM 参数

```dockerfile
FROM eclipse-temurin:17-jre-alpine

# JVM 配置 — 必须感知 Cgroup 限制
ENV JAVA_OPTS="\
  -XX:+UseContainerSupport \
  -XX:MaxRAMPercentage=75.0 \
  -XX:MinRAMPercentage=50.0 \
  -XX:+PrintGCDetails \
  -XX:+PrintGCDateStamps \
  -Xloggc:/logs/gc.log \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/logs/heapdump.hprof \
  -XX:+ExitOnOutOfMemoryError \
  -Djava.security.egd=file:/dev/./urandom"

COPY target/payment-service.jar /app/app.jar
WORKDIR /app

EXPOSE 8080
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

### 2.2 Spring Boot 健康检查端点

```yaml
# application-prod.yml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
      base-path: /actuator
  endpoint:
    health:
      show-details: when-authorized
      probes:
        enabled: true          # Kubernetes Readiness/Liveness
  health:
    db:
      enabled: true            # 检查数据库连接
    redis:
      enabled: true            # 检查 Redis 连接
```

---

## 第 3 章：可观测性标准

### 3.1 Prometheus 告警规则

```yaml
groups:
  - name: payment-service
    rules:
      - alert: PaymentServiceDown
        expr: up{job="payment-service"} == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "payment-service 不可用"

      - alert: High5xxRate
        expr: |
          rate(http_requests_total{status=~"5..",job="payment-service"}[5m])
          /
          rate(http_requests_total{job="payment-service"}[5m]) > 0.05
        for: 3m
        labels: { severity: critical }
        annotations:
          summary: "payment-service 5xx 错误率超过 5%"

      - alert: HighMemoryUsage
        expr: |
          sum(container_memory_working_set_bytes{pod=~"payment-service.*"})
          /
          sum(kube_pod_container_resource_limits{pod=~"payment-service.*",resource="memory"}) > 0.85
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "payment-service 内存使用率超过 85%"

      - alert: PodCrashLoopBackOff
        expr: kube_pod_status_phase{phase="Waiting",pod=~"payment-service.*"} == 1
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "payment-service Pod CrashLoopBackOff"
```

### 3.2 日志标准格式

```xml
<!-- logback-spring.xml -->
<configuration>
  <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdc>true</includeMdc>
      <fieldNames>
        <timestamp>@timestamp</timestamp>
        <version>[ignore]</version>
        <levelValue>[ignore]</levelValue>
      </fieldNames>
      <customFields>{"service":"payment-service","env":"production"}</customFields>
    </encoder>
  </appender>

  <root level="INFO">
    <appender-ref ref="JSON"/>
  </root>
</configuration>
```

### 3.3 关键日志级别使用规范

| 级别 | 触发条件 | 示例 |
|------|---------|------|
| **FATAL** | 进程将退出 | OOM, 数据库不可用 |
| **ERROR** | 功能不可用 | 支付失败、连接池耗尽 |
| **WARN** | 潜在问题 | 重试、超时、降级 |
| **INFO** | 关键流程 | 请求开始/结束、服务启动 |

---

## 第 4 章：应急预案

### 4.1 降级策略

| 依赖 | 故障时行为 | 降级方案 |
|------|-----------|---------|
| 数据库 | 只读模式，写请求排队 | 本地缓存兜底 |
| Redis | 回退到本地 Caffeine 缓存 | 缓存降级不阻塞 |
| 支付网关 | 快速失败，记录待重试队列 | 熔断器打开 |
| 消息队列 | 消息落盘，恢复后重试 | 本地文件队列 |

### 4.2 熔断配置 (Resilience4j)

```yaml
resilience4j.circuitbreaker:
  instances:
    paymentGateway:
      registerHealthIndicator: true
      slidingWindowSize: 10
      minimumNumberOfCalls: 5
      failureRateThreshold: 50        # 50% 失败则熔断
      waitDurationInOpenState: 30s    # 30s 后尝试半开
      permittedNumberOfCallsInHalfOpenState: 3
      recordExceptions:
        - java.net.ConnectException
        - java.net.SocketTimeoutException
```

### 4.3 故障恢复 Runbook

```bash
# P0: 立即恢复服务
kubectl scale deployment/payment-service --replicas=5 -n production
kubectl set resources deployment/payment-service -n production \
  --limits memory=2Gi --requests memory=1Gi

# P1: 获取诊断数据
kubectl describe pod -l app=payment-service -n production > /tmp/pod_describe.txt
kubectl logs --tail=200 -l app=payment-service -n production > /tmp/app_logs.txt
kubectl get events -n production --sort-by='.lastTimestamp' > /tmp/events.txt

# P2: 分析根因
# 检查 Heap Dump
kubectl cp <pod>:/logs/heapdump.hprof ./heapdump.hprof -n production
# 使用 Eclipse MAT 分析

# P3: 防止复发
# 部署修复版本
kubectl set image deployment/payment-service \
  payment-service=registry.internal/payment-service:3.2.2-hotfix
```