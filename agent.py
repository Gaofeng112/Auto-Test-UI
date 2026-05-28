"""MCP 调用模板（Playwright 版）：stdio 启动 @playwright/mcp。"""

import asyncio
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, RunConfig, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
BASE_URL = os.getenv("OPENAI_BASE_URL")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.2")
MAX_TURNS = int(os.getenv("OPENAI_MAX_TURNS", "80"))
MCP_SESSION_TIMEOUT_SECONDS = int(os.getenv("MCP_SESSION_TIMEOUT_SECONDS", "300"))
LOGIN_CHECK_ENABLED = os.getenv("LOGIN_CHECK_ENABLED", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}
LOGIN_CHECK_MAX_TURNS = int(os.getenv("LOGIN_CHECK_MAX_TURNS", "12"))
LOGIN_CHECK_MAX_ATTEMPTS = int(os.getenv("LOGIN_CHECK_MAX_ATTEMPTS", "3"))
LOGIN_CHECK_URL = os.getenv("LOGIN_CHECK_URL", "https://vip.yaozh.com")
PLAYWRIGHT_ACTION_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_ACTION_TIMEOUT_MS", "15000"))
PLAYWRIGHT_NAVIGATION_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_NAVIGATION_TIMEOUT_MS", "120000"))
PLAYWRIGHT_VIEWPORT_SIZE = os.getenv("PLAYWRIGHT_VIEWPORT_SIZE", "1440x1000")
PLAYWRIGHT_OUTPUT_DIR = Path(os.getenv("PLAYWRIGHT_OUTPUT_DIR", ".playwright-mcp"))
PLAYWRIGHT_USER_DATA_DIR = Path(os.getenv("PLAYWRIGHT_USER_DATA_DIR", ".playwright-mcp/user-data"))
KEEP_BROWSER_OPEN_AFTER_RUN = os.getenv("KEEP_BROWSER_OPEN_AFTER_RUN", "1").strip().lower() not in {
    "0",
    "false",
    "no",
}


def workspace_path(path: Path) -> str:
    """Resolve relative config paths from the project directory."""
    return str(path if path.is_absolute() else PROJECT_DIR / path)


# Playwright MCP：本地子进程，等价于 Cursor 里 mcp.json 的配置
PLAYWRIGHT_MCP = {
    "command": "npx",
    "args": [
        "-y",
        "@playwright/mcp@latest",
        "--output-dir",
        workspace_path(PLAYWRIGHT_OUTPUT_DIR),
        "--user-data-dir",
        workspace_path(PLAYWRIGHT_USER_DATA_DIR),
        "--timeout-action",
        str(PLAYWRIGHT_ACTION_TIMEOUT_MS),
        "--timeout-navigation",
        str(PLAYWRIGHT_NAVIGATION_TIMEOUT_MS),
        "--viewport-size",
        PLAYWRIGHT_VIEWPORT_SIZE,
    ],
}

DEFAULT_TASK = (
    "打开https://vip.yaozh.com，点击研发，点击品种筛选系统，打开列表-按品种浏览，"
    "在药品名称输入框录入{尼卡利单抗注射液}并勾选精确，点击搜索，"
    "记录列表首条及全部返回的bianma、name，"
    "用主表按name精确查询，并按bianma分组校验页面结果"
)

LOGIN_CHECK_TASK = (
    f"打开{LOGIN_CHECK_URL}，只做登录状态快速检查，不执行任何业务测试。"
    "如果页面已经是登录后的会员/工作台/业务页面，或能看到用户名、退出、个人中心、研发等登录后入口，"
    "最终只回复：LOGIN_STATUS=LOGGED_IN。"
    "如果看到登录/注册/账号密码输入框/验证码/请登录/权限受限等未登录状态，"
    "请停在可登录页面或登录弹窗，最终只回复：LOGIN_STATUS=NEED_LOGIN。"
    "如果页面打不开或无法判断，最终只回复：LOGIN_STATUS=UNKNOWN，并简短说明原因。"
)

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(True)


def build_agent(instructions: str, server_connection: MCPServerStdio) -> Agent:
    return Agent(
        name="UI自动测试助手",
        instructions=instructions,
        model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
        mcp_servers=[server_connection],
    )


async def check_login(agent: Agent) -> str:
    result = await Runner.run(
        agent,
        LOGIN_CHECK_TASK,
        run_config=RunConfig(tracing_disabled=True),
        max_turns=LOGIN_CHECK_MAX_TURNS,
    )
    output = str(result.final_output).strip()
    print(f"登录检测结果: {output}")
    return output


async def ensure_logged_in(agent: Agent) -> bool:
    if not LOGIN_CHECK_ENABLED:
        print("登录检测已关闭，直接执行任务。")
        return True

    for attempt in range(1, LOGIN_CHECK_MAX_ATTEMPTS + 1):
        print(f"\n--- 登录检测 {attempt}/{LOGIN_CHECK_MAX_ATTEMPTS} ---")
        try:
            status = await check_login(agent)
        except MaxTurnsExceeded:
            status = "LOGIN_STATUS=UNKNOWN 登录检测超过最大轮次"
            print(status)

        if "LOGIN_STATUS=LOGGED_IN" in status:
            return True

        if "LOGIN_STATUS=NEED_LOGIN" not in status and "LOGIN_STATUS=UNKNOWN" not in status:
            print("登录检测返回不明确，按未登录处理。")

        if attempt >= LOGIN_CHECK_MAX_ATTEMPTS:
            break

        await asyncio.to_thread(
            input,
            "\n当前未检测到登录态。请在打开的浏览器中输入账号密码并完成登录，登录成功后回到这里按 Enter 继续检测...",
        )

    print("多次检测后仍未确认登录成功，已停止正式任务。")
    return False


async def run_agent(task: Optional[str] = None) -> str:
    print("正在启动 Playwright MCP…")
    print(f"浏览器登录态目录: {workspace_path(PLAYWRIGHT_USER_DATA_DIR)}")
    print(
        "运行配置: "
        f"max_turns={MAX_TURNS}, "
        f"action_timeout={PLAYWRIGHT_ACTION_TIMEOUT_MS}ms, "
        f"navigation_timeout={PLAYWRIGHT_NAVIGATION_TIMEOUT_MS}ms"
    )

    instructions = (PROJECT_DIR / "Prompt.md").read_text(encoding="utf-8").strip()
    if not instructions:
        raise RuntimeError("Prompt.md 为空：请先在 Prompt.md 中配置 agent 提示词。")

    # Playwright MCP：本地子进程，等价于 Cursor 里 mcp.json 的配置
    async with MCPServerStdio(
        name="playwright",
        params=PLAYWRIGHT_MCP,
        client_session_timeout_seconds=MCP_SESSION_TIMEOUT_SECONDS,
        cache_tools_list=True,
    ) as server_connection:
        print(f"已连接: {server_connection.name}")

        tools = await server_connection.list_tools()
        print("可用工具:", [t.name for t in tools[:5]], "...")

        agent = build_agent(instructions, server_connection)

        print("\n--- 发送请求 ---")
        user_task = (task or os.getenv("UI_TEST_TASK", DEFAULT_TASK)).strip()
        if not user_task:
            raise RuntimeError("UI_TEST_TASK 为空：请在 .env 或 DEFAULT_TASK 中配置测试任务。")
        print(f"任务: {user_task}")

        try:
            if not await ensure_logged_in(agent):
                return "未确认登录成功，正式任务未执行。"

            result = await Runner.run(
                agent,
                user_task,
                run_config=RunConfig(tracing_disabled=True),
                max_turns=MAX_TURNS,
            )
            final_output = str(result.final_output)
            print(f"Agent 回复: {final_output}")
            return final_output
        except MaxTurnsExceeded:
            message = f"步骤过多，已达最大轮次（{MAX_TURNS}）。可在 .env 里调大 OPENAI_MAX_TURNS，或把任务拆成多句。"
            print(message)
            return message
        except (asyncio.CancelledError, KeyboardInterrupt):
            message = "已中断执行。"
            print(message)
            return message
        finally:
            if KEEP_BROWSER_OPEN_AFTER_RUN:
                try:
                    await asyncio.to_thread(
                        input,
                        "\n浏览器保持打开中。请在页面完成登录/验证后，回到这里按 Enter 关闭浏览器并保存登录态...",
                    )
                except EOFError:
                    print("\n检测到非交互终端，跳过等待。")


async def main() -> None:
    await run_agent()


if __name__ == "__main__":
    asyncio.run(main())
