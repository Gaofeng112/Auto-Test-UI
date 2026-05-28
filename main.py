"""自然语言 UI 测试入口。"""

import asyncio

from agent import DEFAULT_TASK, run_agent


def read_task() -> str:
    print(DEFAULT_TASK)
    return DEFAULT_TASK


async def main() -> None:
    await run_agent(read_task())


if __name__ == "__main__":
    asyncio.run(main())
