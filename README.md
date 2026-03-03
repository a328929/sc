# sc

批量上传文件至 Telegram 私有频道（个人云盘式）项目。

## 项目结构

- `frontend/`：网页前端（React + TypeScript + Vite）
- `backend/`：后端服务（FastAPI + SQLite + Telethon）
- `config/`：独立配置文件

## 阶段状态

- ✅ 第一阶段：前端界面（文件选择、总进度/当前进度、队列、日志）
- ✅ 第二阶段：后端任务队列、持久化、事件流、WebSocket
- ✅ 第三阶段：真实 Telegram 上传适配（session + api_id/api_hash）

---

## 运行前准备

1. 复制配置：

```bash
cp config/app.example.yaml config/app.yaml
```

2. 编辑 `config/app.yaml`：

- `telegram.api_id`
- `telegram.api_hash`
- `telegram.target_channel`
- `telegram.session_file`（你放入的 `my_session.session` 路径）

3. 前端环境变量：

```bash
cp frontend/.env.example frontend/.env
```

---

## 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

后端能力：

- `POST /api/tasks/upload`：上传并创建任务（multipart）
- `POST /api/tasks/{id}/start`：开始/继续任务
- `POST /api/tasks/{id}/pause`：暂停任务
- `GET /api/tasks/{id}`：任务详情（总进度 + 文件进度）
- `GET /api/tasks/{id}/events`：事件日志
- `WS /api/ws/tasks/{id}`：实时状态推送

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 测试

```bash
cd backend
PYTHONPATH=. pytest -q

cd ../frontend
npm run lint
npm run build
```

---

## 关键说明

1. 第三阶段已接入 **Telethon 实际上传**，不是 mock 上传。
2. 浏览器离开页面后，任务仍由后端进程继续执行。
3. 为避免风控，建议把 `upload.concurrency` 控制在 2~3。
4. 你必须有可用 `session` + `api_id/api_hash`；不存在可长期稳定通用的官方“公共默认 API Key”。
