# Auto-Test-UI

基于 OpenAI Agents + Playwright MCP 的自然语言 UI 测试项目，当前主要面向 `https://vip.yaozh.com` 做页面操作、检索和结果校验。

## 核心流程

首次使用先保存登录态：

```powershell
python .\src\login.py
```

脚本会打开药智网页面。请在浏览器里手动登录，登录成功后回到终端按 Enter。登录信息会保存在完整浏览器 profile 目录：

```text
.playwright-mcp/user-data
```

同时会额外导出一份 storage state 到 `.playwright-mcp/vip-auth-state.json`，方便排查，但正式任务默认复用的是完整 profile。

之后运行自然语言任务：

```powershell
python main.py
```

终端会提示输入测试任务。直接回车会使用默认任务，也可以输入新的自然语言步骤。

## 安装

建议在虚拟环境中安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

如果 `npx @playwright/mcp` 首次运行较慢，是因为需要下载或缓存 MCP 包。

## 配置

复制示例配置：

```powershell
copy .env.example .env
```

至少需要配置：

```env
OPENAI_API_KEY=你的模型 API Key
OPENAI_BASE_URL=你的模型服务地址
OPENAI_MODEL=你的模型名称
```

常用配置：

```env
OPENAI_MAX_TURNS=80
MCP_SESSION_TIMEOUT_SECONDS=300
PLAYWRIGHT_STORAGE_STATE=.playwright-mcp/vip-auth-state.json
LOGIN_URL=https://vip.yaozh.com
PLAYWRIGHT_USER_DATA_DIR=.playwright-mcp/user-data
PLAYWRIGHT_ACTION_TIMEOUT_MS=15000
PLAYWRIGHT_NAVIGATION_TIMEOUT_MS=120000
PLAYWRIGHT_VIEWPORT_SIZE=1440x1000
KEEP_BROWSER_OPEN_AFTER_RUN=1
```

`UI_TEST_TASK` 可以写默认任务；也可以不写，运行 `python main.py` 时手动输入。

## 文件说明

- `login.py`：打开浏览器，手动登录药智网，并保存 cookie/storage state。
- `main.py`：自然语言任务入口，从终端读取任务并调用 agent。
- `src/agent.py`：启动 Playwright MCP，复用登录 profile，调用模型执行 UI 自动化。
- `src/login.py`：登录逻辑实现，顶层 `login.py` 会调用它。
- `src/Prompt.md`：agent 的浏览器操作规则、药智网流程约束和输出格式。
- `docs/`：存放项目说明、测试文本等 `.txt` 文档。
- `.env.example`：配置模板。
- `.playwright-mcp/`：MCP 输出和登录态目录，已被 `.gitignore` 忽略。

## 推荐使用顺序

1. 配好 `.env`。
2. 运行 `python login.py`，手动登录并保存 cookie。
3. 运行 `python main.py`，输入自然语言任务。
4. 如果任务提示登录态失效，重新运行 `python login.py`。

## 示例任务

```text
打开https://vip.yaozh.com，点击研发，点击品种筛选系统，打开列表-按品种浏览，在药品名称输入框录入{尼卡利单抗注射液}并勾选精确，点击搜索，记录列表首条及全部返回的bianma、name，用主表按name精确查询，并按bianma分组校验页面结果
```

## 常见问题

### 任务进入登录页

说明 cookie 可能失效或未保存成功。重新执行：

```powershell
python login.py
```

### 页面打开慢或偶发失败

可以适当调大：

```env
PLAYWRIGHT_ACTION_TIMEOUT_MS=20000
PLAYWRIGHT_NAVIGATION_TIMEOUT_MS=180000
OPENAI_MAX_TURNS=100
```

### 任务结束后浏览器一直开着

这是由下面配置控制的：

```env
KEEP_BROWSER_OPEN_AFTER_RUN=1
```

如果希望任务结束后直接关闭，改成：

```env
KEEP_BROWSER_OPEN_AFTER_RUN=0
```

## 注意事项

- 不要提交 `.env` 或 `.playwright-mcp/`，其中可能包含密钥和登录态。
- 当前登录流程是人工登录保存完整浏览器 profile，正式任务不再让 AI 每次检测或尝试登录。
- 如果页面出现验证码、权限限制或登录态失效，先更新登录态，再重新执行任务。
