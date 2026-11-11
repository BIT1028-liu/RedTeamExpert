# RedTeamExpert

防御型安全情报 Agent —— 基于 LangGraph + 智谱 GLM + Tavily 联网搜索的网络安全 AI 助手。

## 免责声明

1. **用途限制**：本项目仅面向**防御方向**的安全工作（威胁情报分析、检测与加固建议、应急响应）。
   系统提示词内置道德底线与法律合规双层规则（详见 `app/agents/RedTeamExpert.py` 的 A–F 节），
   会对未授权入侵、漏洞武器化等请求明确拒绝。**禁止**将本项目用于任何未授权的渗透测试、
   系统入侵、数据窃取或其他违法违规活动。
2. **合规义务**：使用者应遵守所在司法辖区的法律法规（包括但不限于《中华人民共和国网络安全法》
   《数据安全法》《个人信息保护法》《关键信息基础设施安全保护条例》）。任何针对真实系统的
   安全测试都必须事先取得书面授权。
3. **责任归属**：本项目按「现状」提供，不含任何明示或默示的担保。使用者因下载、部署或使用
   本项目而产生的一切后果（包括对自身或第三方系统的影响、数据损失、法律风险）由使用者自行承担，
   作者不承担任何责任。
4. **AI 输出免责**：本项目的分析结论由大语言模型生成，可能存在错误、过时或遗漏。涉及漏洞处置、
   应急响应等关键决策时，请务必结合权威来源（CISA、CNVD/CNNVD、厂商公告）人工核实，
   不要将 AI 输出作为唯一依据。
5. **API Key 安全**：使用本项目需自行申请 API Key 并妥善保管。作者不会索取任何密钥；
   请勿将密钥提交到公开仓库。

## 功能特性

- 🌐 **安全情报检索**：Tavily 联网搜索，实时抓取漏洞通报、安全事件、厂商公告（CISA / CNVD / MSRC 等一手来源优先）
- 📋 **结构化分析**：按「事件概述 → MITRE ATT&CK/ATLAS 攻击链映射 → 影响评估 → 研判」四维框架输出情报分析
- 🛡️ **防御方案输出**：P0/P1/P2 优先级，含 SIEM / YARA / Suricata / WAF / LLM 输入输出过滤检测规则
- 💬 **多轮会话**：LangGraph checkpointer 持久化对话上下文，支持会话列表 / 历史回看 / 删除
- 📡 **SSE 流式响应**：打字机效果实时输出
- 📎 **文件上传**：阿里云 OSS 预签名 URL 上传/下载（图片、PDF 等）

## 架构

```
┌──────────┐   SSE    ┌─────────────────────┐   create_agent
│  前端     │ ───────▶ │  FastAPI (app/)      │ ──────────────▶ GLM-5.3-flash
│          │          │  ├─ routes_chat      │                  （智谱开放平台）
└──────────┘          │  ├─ routes_sessions  │                    │
                      │  ├─ routes_oss       │                    ▼
                      │  └─ services         │               TavilySearch
                      │     └─ SQLite        │               （联网搜索）
                      │        ├─ sessions   │
                      │        └─ checkpoints│ ── LangGraph 会话持久化
                      └─────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)（包管理）
- 智谱 API Key（[开放平台](https://open.bigmodel.cn)）
- Tavily API Key（[官网](https://app.tavily.com)，每月有免费额度）

### 安装与配置

```bash
git clone https://github.com/BIT1028-liu/RedTeamExpert.git
cd RedTeamExpert

# 安装依赖
uv sync

# 配置环境变量：复制模板并填入你的 API Key
cp .env.example .env
# Windows PowerShell: copy .env.example .env
```

`.env` 至少填写：

```
YOUR_API_KEY=<智谱 API Key>
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4
TAVILY_API_KEY=<Tavily API Key>
```

> ⚠️ `.env` 已被 `.gitignore` 排除，请确保你的 API Key 永远不会进入 git。

### 方式一：langgraph dev（开发调试）

```bash
uv run langgraph dev
```

启动后终端会给出本地 API 地址与 LangGraph Studio 入口，可在浏览器中直接与 Agent 对话调试。

> 提示词含中文时部分终端会触发编码问题，可先执行 `$env:PYTHONUTF8="1"`（PowerShell，仅当前会话生效）再启动；
> 也可 `setx PYTHONUTF8 1` 永久生效（会改变整机的 Python 默认编码，按需选择）。

### 方式二：FastAPI 后端（完整服务）

```bash
uv run uvicorn app.main:app --reload --port 8000
```

浏览器访问 `http://127.0.0.1:8000/docs` 查看交互式接口文档。

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息，SSE 流式返回（`meta` → `token`* → `end`） |
| GET | `/api/sessions` | 会话列表（按最近活跃排序） |
| POST | `/api/sessions` | 新建空会话，返回 `thread_id` |
| GET | `/api/sessions/{thread_id}/messages` | 读取某会话完整历史 |
| DELETE | `/api/sessions/{thread_id}` | 删除会话及其全部对话记录 |
| POST | `/api/oss/upload` | 上传文件到 OSS（≤10MB，白名单扩展名） |
| GET | `/api/oss/download-url?key=...` | 获取预签名下载链接（60 秒 ~ 7 天） |
| GET | `/health` | 健康检查 |

请求体示例（`/api/chat`）：

```json
{"message": "最近一周有什么值得关注的 AI 安全事件？", "thread_id": null}
```

`thread_id` 传 `null` 新建会话；后续请求带上响应 `meta` 事件返回的 `thread_id` 即可续聊。

## 项目结构

```
RedTeamExpert/
├── app/                        # FastAPI 后端
│   ├── main.py                 # 入口：lifespan 装配 checkpointer + Agent
│   ├── api/                    # 路由层（chat / sessions / oss）
│   ├── agents/RedTeamExpert.py # Agent 定义（系统提示词 A–F 节在此）
│   ├── core/config.py          # 环境变量统一加载
│   └── services/               # OSS / 会话注册表
├── RedTeamExpert.py            # 独立版 Agent（自包含，不依赖 app/）
├── langgraph.json              # langgraph dev 配置
├── lc_RedTeamExpert.ipynb      # Agent 开发过程 notebook（学习笔记）
├── lc_*.ipynb                  # LangChain/LangGraph 各知识点学习笔记
└── README.md                   # 本文件
```

> 当前 Agent 只接入 **Tavily 联网搜索** 一个工具；后续需要再扩展其他工具。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

- **免责**：MIT 协议第 11-13 条明确软件按「现状」提供、不承担任何担保与赔偿责任，
  与本项目顶部的[免责声明](#免责声明)共同构成完整的责任边界。
- **合规**：MIT 仅约束代码版权层面，**不免除使用者的法定义务**——无论协议如何，
  使用本项目仍须遵守所在司法辖区的法律法规（见免责声明第 2 条）。将本项目用于
  未授权的安全测试属违法行为，与本项目及作者的立场无关。
