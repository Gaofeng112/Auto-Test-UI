"""MCP 调用模板（Playwright 版）：stdio 启动 @playwright/mcp。"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, RunConfig, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.exceptions import MaxTurnsExceeded
from agents.mcp import MCPServerStdio

load_dotenv()

BASE_URL = os.getenv("OPENAI_BASE_URL")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.2")
MAX_TURNS = int(os.getenv("OPENAI_MAX_TURNS", "30"))

# Playwright MCP：本地子进程，等价于 Cursor 里 mcp.json 的配置
PLAYWRIGHT_MCP = {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
}

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
set_tracing_disabled(True)


async def main() -> None:
    print("正在启动 Playwright MCP…")

    instructions = Path(__file__).with_name("Prompt.md").read_text(encoding="utf-8").strip()
    if not instructions:
        raise RuntimeError("Prompt.md 为空：请先在 Prompt.md 中配置 agent 提示词。")

    # Playwright MCP：本地子进程，等价于 Cursor 里 mcp.json 的配置
    async with MCPServerStdio(
        name="playwright",
        params=PLAYWRIGHT_MCP,
        client_session_timeout_seconds=120,
        cache_tools_list=True,
    ) as server_connection:
        print(f"已连接: {server_connection.name}")

        tools = await server_connection.list_tools()
        print("可用工具:", [t.name for t in tools[:5]], "...")

        agent = Agent(
            name="UI自动测试助手",
            instructions=instructions,
            model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
            mcp_servers=[server_connection],
        )

        print("\n--- 发送请求 ---")
        try:
            result = await Runner.run(
                agent,
                "打开药智网，在站内搜索「阿司匹林」，验证有搜索结果或明确无结果提示。",
                run_config=RunConfig(tracing_disabled=True),
                max_turns=MAX_TURNS,
            )
            print(f"Agent 回复: {result.final_output}")
        except MaxTurnsExceeded:
            print(f"步骤过多，已达最大轮次（{MAX_TURNS}）。可在 .env 里调大 OPENAI_MAX_TURNS，或把任务拆成多句。")
        except (asyncio.CancelledError, KeyboardInterrupt):
            print("已中断执行。")


if __name__ == "__main__":
    asyncio.run(main())
