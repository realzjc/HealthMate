from semantic_kernel.functions import kernel_function
import asyncio
from collections import defaultdict
from playwright.async_api import async_playwright
import json
import re
import chainlit as cl

# 1. 简单问题直接回答
# 2. 3. 获取肌肉名称，性别，如果有的话，从写定好的网站上，抓取视频

class FitnessPlugin:

    @kernel_function(
        name="get_supported_muscles",
        description="Return a list of supported muscle names for training video search."
    )
    async def get_supported_muscles(self) -> str:
        async with cl.Step(name="Analyzing user intent...", type="function"):
            pass
        return json.dumps([
            "Chest", "Back", "Shoulders", "Biceps", "Triceps", 
            "Quadriceps", "Hamstrings", "Glutes", "Calves", "Abs", 
            "Forearms", "Neck", "Traps", "Obliques"
        ])

    @kernel_function(
        name="get_exercises_by_muscle",
        description="Return a list of exercises (with video URLs) for a specific muscle and gender."
    )
    async def get_exercises_by_muscle(self, muscle: str, gender: str) -> str:
        async with cl.Step(name="Searching for resources of " + muscle, type="function"):
            pass
        base_url = f"https://musclewiki.com/exercises/{gender.lower()}/{muscle.lower()}/"
        urls = await self.scrape_video_urls(base_url)

        video_dict = defaultdict(dict)
        for url in urls:
            clean_url = url.split("#")[0]
            filename = clean_url.split("/")[-1].split(".mp4")[0]
            match = re.match(r"[\w]+-[\w]+-(.*)-(side|front)(_[\w]+)?$", filename)
            if match:
                name_key_raw, view, _ = match.groups()
                name_key = name_key_raw.lower()
                readable_name = name_key.replace("-", " ").title()
                if view == "side":
                    video_dict[name_key]["sideUrl"] = clean_url
                    video_dict[name_key]["name"] = readable_name
                elif view == "front":
                    video_dict[name_key]["frontUrl"] = clean_url
                    video_dict[name_key]["name"] = readable_name

        exercises = []
        for name_key, data in video_dict.items():
            if "sideUrl" in data and "frontUrl" in data:
                exercises.append({
                    "name": data["name"],
                    "sideUrl": data["sideUrl"],
                    "frontUrl": data["frontUrl"],
                    "notes": " ",  # Placeholder, can be filled later
                    "tips": " "
                })

        return json.dumps({
            "muscle": muscle,
            "exercises": exercises
        })
        # 整理对应的格式

    async def scrape_video_urls(self, url: str) -> list[str]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                # headless=True,
                headless=False,
                args=[
                    "--window-position=100,100",
                    "--window-size=1200,800"
                ]
            )
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_load_state("networkidle")
            # 使用 networkidle 等待所有网络请求结束（类似于页面“完全加载完”）

            seen_sources = set()
            scroll_step = 500
            max_scrolls = 8
            no_new_count = 0
            max_no_new = 2
            # seen_sources = set()    # 存储已抓取的唯一 src 链接
            # scroll_step = 500       # 每次向下滚动 500px
            # max_scrolls = 8         # 最多滚动 8 次
            # no_new_count = 0        # 连续几次未发现新视频
            # max_no_new = 2          # 最多允许 2 次无新资源就停止

            for _ in range(max_scrolls):
                video_elems = await page.query_selector_all("video")
                new_found = 0

                for video in video_elems:
                    source = await video.query_selector("source")
                    if source:
                        src = await source.get_attribute("src")
                        if src and src not in seen_sources:
                            seen_sources.add(src)
                            new_found += 1

                if new_found == 0:
                    no_new_count += 1
                    if no_new_count >= max_no_new:
                        break
                else:
                    no_new_count = 0
                # 如果连续 2 次未找到新视频，就提前退出循环（节省资源）

                await page.evaluate(f"window.scrollBy(0, {scroll_step})")
                await asyncio.sleep(0.3)

            await browser.close()
            return list(seen_sources)

    # 注册为kernel function，供llm调用，给出对应格式
    @kernel_function(
        name="get_format",
        description="Return the JSON output format"
    )
    async def get__format(self) -> str:
        async with cl.Step(name="Summarizing exercise notes format...", type="function"):
            pass
        return json.dumps({
            "render": [
                {
                    "type": "video_block",
                    "title": "<exercise name>",
                    "props": {
                        "sideUrl": "<side view video URL>",
                        "frontUrl": "<front view video URL>"
                    }
                },
                {
                    "type": "text_block",
                    "title": "<content_title>",
                    "props": {
                        "content": "<content>"
                    }
                }
            ]
        })
