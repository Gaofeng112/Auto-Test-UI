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
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.4")
MAX_TURNS = int(os.getenv("OPENAI_MAX_TURNS", "80"))
MCP_SESSION_TIMEOUT_SECONDS = int(os.getenv("MCP_SESSION_TIMEOUT_SECONDS", "300"))
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


def build_playwright_mcp_params() -> dict:
    args = [
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
    ]

    return {
        "command": "npx",
        "args": args,
    }

DEFAULT_TASK = (
    "打开https://vip.yaozh.com，点击研发，点击品种筛选系统，打开列表-按品种浏览，"
    "在药品名称输入框录入{尼卡利单抗注射液}并勾选精确，点击搜索，"
    "记录列表首条信息"
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

    # Playwright MCP：本地子进程，等价于 Cursor 里 mcp.json 的配置
    async with MCPServerStdio(
        name="playwright",
        params=build_playwright_mcp_params(),
        client_session_timeout_seconds=MCP_SESSION_TIMEOUT_SECONDS,
        cache_tools_list=True,
    ) as server_connection:
        print(f"已连接: {server_connection.name}")

        tools = await server_connection.list_tools()
        print("可用工具:", [t.name for t in tools[:5]], "...")

        agent = build_agent(instructions, server_connection)

        print("\n--- 发送请求 ---")
        user_task = (task or os.getenv("UI_TEST_TASK", DEFAULT_TASK)).strip()
        print(f"任务: {user_task}")

        try:
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
