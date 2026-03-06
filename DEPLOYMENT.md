# Docker 部署文档

## 本地开发使用 Docker

### 使用 Docker Compose（推荐）

Docker Compose 会自动启动 Paste 服务（使用 SQLite 数据库）：

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f paste

# 停止服务
docker-compose down

# 停止并删除数据
docker-compose down -v
```

服务启动后，访问 http://localhost:8000

### 运行数据库迁移

```bash
# 在运行的容器中执行迁移
docker-compose exec paste alembic upgrade head
```

### 手动构建和运行

```bash
# 构建镜像
docker build -t paste .

# 运行容器
docker run -d \
  --name paste \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/data:/app/data \
  paste
```

## GitHub Actions 自动构建

### 工作流程

当以下事件发生时，GitHub Actions 会自动构建 Docker 镜像：

- 推送代码到 `main` 或 `master` 分支
- 创建新的 tag（如 `v1.0.0`）
- 手动触发工作流

### 构建输出

镜像会推送到 GitHub Container Registry (ghcr.io)：

```bash
# 格式
ghcr.io/<username>/paste:<tag>

# 示例
ghcr.io/bboysoulcn/paste:main
ghcr.io/bboysoulcn/paste:v1.0.0
ghcr.io/bboysoulcn/paste:sha-abc123
```

### 多架构支持

GitHub Actions 会自动构建以下架构的镜像：
- linux/amd64
- linux/arm64

### 使用构建的镜像

```bash
# 登录到 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 拉取镜像
docker pull ghcr.io/<username>/paste:main

# 运行容器
docker run -d \
  --name paste \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -v $(pwd)/data:/app/data \
  ghcr.io/<username>/paste:main
```

## 生产部署

### 使用 Docker Compose

创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  paste:
    image: ghcr.io/<username>/paste:latest
    environment:
      STORAGE_PATH: /app/storage
      EXPIRATION_HOURS: 24
      MAX_FILE_SIZE: 10485760
    volumes:
      - ./storage:/app/storage
      - ./data:/app/data
    ports:
      - "8000:8000"
    restart: unless-stopped
```

启动：

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 使用 Kubernetes

创建 `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paste
spec:
  replicas: 2
  selector:
    matchLabels:
      app: paste
  template:
    metadata:
      labels:
        app: paste
    spec:
      containers:
      - name: paste
        image: ghcr.io/<username>/paste:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: storage
          mountPath: /app/storage
        - name: data
          mountPath: /app/data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: storage
        persistentVolumeClaim:
          claimName: paste-storage
      - name: data
        persistentVolumeClaim:
          claimName: paste-data
---
apiVersion: v1
kind: Service
metadata:
  name: paste
spec:
  selector:
    app: paste
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

部署：

```bash
kubectl apply -f deployment.yaml
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./paste.db` | SQLite 数据库路径 |
| `STORAGE_PATH` | `./storage` | 文件存储路径 |
| `EXPIRATION_HOURS` | `24` | Paste 过期时间（小时） |
| `ID_LENGTH` | `6` | Paste ID 长度 |
| `MAX_FILE_SIZE` | `10485760` | 最大文件大小（字节，默认 10MB） |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |

## 数据持久化

应用使用 SQLite 数据库，需要持久化以下目录：

- `/app/data` - 数据库文件（paste.db）
- `/app/storage` - 上传的文件内容

使用 Docker 或 Kubernetes 时，确保将这些目录挂载到持久化存储。

## 健康检查

容器包含健康检查，会定期检查 `/health` 端点：

```bash
# 手动检查
curl http://localhost:8000/health

# 响应
{"status":"healthy"}
```

## 性能优化

1. **多阶段构建**：减小最终镜像大小
2. **非 root 用户**：提高安全性
3. **健康检查**：自动重启不健康的容器
4. **多架构支持**：支持 amd64 和 arm64 平台
5. **SQLite 数据库**：轻量级，无需额外数据库服务
