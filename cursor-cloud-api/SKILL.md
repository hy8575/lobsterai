# Cursor Cloud API Skill

## 描述

调用 Cursor Cloud Agents API（https://api.cursor.com），用于创建/管理云端 Agent、获取任务状态与对话记录。  
**认证方式**：Basic Auth（API Key 作为用户名，密码为空）。**不要**使用 Bearer 或 `api.cursor.cloud`。

## 配置

- **API Key**：从环境变量 `CURSOR_API_KEY` 读取（格式 `crsr_xxx`），或在调用时由上层传入，**不要**在技能文件中硬编码。
- **Base URL**：`https://api.cursor.com`（**不是** api.cursor.cloud）。

## 常用端点（均为 GET 除注明外）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v0/me` | 当前 API Key 信息（名称、邮箱、创建时间） |
| GET | `/v0/models` | 可用模型 ID 列表（用于 launch 时 `model` 字段） |
| GET | `/v0/agents` | 列出当前用户的 Cloud Agents（可加 `?limit=20`） |
| GET | `/v0/agents/{id}` | 获取指定 Agent 状态与结果 |
| GET | `/v0/agents/{id}/conversation` | 获取该 Agent 的对话历史（user/assistant messages） |
| POST | `/v0/agents` | 创建并启动一个 Agent（需 body：prompt、source.repository 等） |
| POST | `/v0/agents/{id}/followup` | 向已有 Agent 追加后续指令 |
| POST | `/v0/agents/{id}/stop` | 停止运行中的 Agent |
| DELETE | `/v0/agents/{id}` | 删除 Agent |

## 调用方式（供 OpenClaw / exec 使用）

- **curl 示例（GET）**：
  ```bash
  curl -s -u "${CURSOR_API_KEY}:" "https://api.cursor.com/v0/me"
  curl -s -u "${CURSOR_API_KEY}:" "https://api.cursor.com/v0/models"
  ```
- **curl 示例（POST 创建 Agent）**：
  ```bash
  curl -s -X POST "https://api.cursor.com/v0/agents" \
    -u "${CURSOR_API_KEY}:" \
    -H "Content-Type: application/json" \
    -d '{"prompt":{"text":"任务描述"},"source":{"repository":"https://github.com/org/repo"}}'
  ```

## 使用场景（量化研报复现）

- **任务拆解**：对「研报复现」类任务，可 POST 创建 Agent，`prompt.text` 中写入「请对以下研报做任务拆解：…」；再轮询 GET `/v0/agents/{id}` 直至 status 为 FINISHED，最后 GET `/v0/agents/{id}/conversation` 解析助手回复作为拆解结果反馈给 ECS 或用户。

## 参考

- 官方文档：https://cursor.com/docs/cloud-agent/api/endpoints  
- 本地调试脚本：`openclaw-config/scripts/cursor-api-debug.ps1`（需设置 `CURSOR_API_KEY` 后运行）。
