"""手动登录药智网并保存 Playwright storage state。"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parents[1]
LOGIN_URL = os.getenv("LOGIN_URL", "https://vip.yaozh.com")
STORAGE_STATE = Path(os.getenv("PLAYWRIGHT_STORAGE_STATE", ".playwright-mcp/vip-auth-state.json"))
USER_DATA_DIR = Path(os.getenv("PLAYWRIGHT_USER_DATA_DIR", ".playwright-mcp/user-data"))
VIEWPORT_SIZE = os.getenv("PLAYWRIGHT_VIEWPORT_SIZE", "1440x1000")


def workspace_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_DIR / path


def parse_viewport(size: str) -> dict[str, int]:
    width, height = size.lower().split("x", 1)
    return {"width": int(width), "height": int(height)}


async def main() -> None:
    storage_state_path = workspace_path(STORAGE_STATE)
    user_data_dir = workspace_path(USER_DATA_DIR)
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,
            viewport=parse_viewport(VIEWPORT_SIZE),
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")

        print(f"已打开: {LOGIN_URL}")
        print("请在浏览器中手动完成登录。登录成功后，回到这里按 Enter 保存 cookie/storage state。")
        await asyncio.to_thread(input, "登录完成后按 Enter 保存> ")

        await context.storage_state(path=str(storage_state_path))
        await context.close()

    print(f"登录态已保存: {storage_state_path}")
    print("后续运行 python main.py 时会复用该浏览器 profile。")


if __name__ == "__main__":
    asyncio.run(main())
