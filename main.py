"""自然语言 UI 测试入口。"""

import asyncio

from src.agent import run_agent

# DEFAULT_TASK = (
#     "打开https://vip.yaozh.com，点击研发，点击品种筛选系统，打开列表-按品种浏览，"
#     "在药品名称输入框录入{尼卡利单抗注射液}并勾选精确，点击搜索，"
#     "记录首条检索结果的全部信息"
# )
DEFAULT_TASK = (
    "打开https://vip.yaozh.com，点击研发，点击品种筛选系统，打开列表-打开列表-按品牌浏览"
    "在企业名称输入框录入{沈阳兴齐眼药股份有限公司}，并勾选精确，点击搜索"
    "记录首条检索结果的前5条信息"

)

async def main() -> None:
    await run_agent(DEFAULT_TASK)


if __name__ == "__main__":
    asyncio.run(main())
