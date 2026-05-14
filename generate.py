"""
每日早報生成腳本
由 GitHub Actions 在台灣時間每天早上 8:00 自動執行
"""

import anthropic
import json
import os
import re
from datetime import datetime, timezone, timedelta

# 台灣時區 UTC+8
TW_TZ = timezone(timedelta(hours=8))

# 早報生成提示詞
PROMPT_TEMPLATE = """你是 Moss 的 AI 助理，服務於「隅室設計顧問工作室」。
今天台灣時間是 {today}，請幫我生成今日設計產業早報。

請搜尋以下內容（48 小時內）：

【Step 1】Jenny Wen（Anthropic 首席設計師）的最新文章、演講、採訪或社群動態。

【Step 2】Product Design / UX 的最新長文
主題：UX design、product design、design systems、user research、product strategy、AI 與設計
優先來源：UX Collective、Nielsen Norman Group、Figma Blog、Smashing Magazine、uxdesign.cc、A List Apart
語言：英文、繁體中文、日文

【Step 3】Brand / 視覺識別 的最新長文
主題：brand identity、visual identity、brand strategy、typography、art direction、品牌設計
優先來源：It's Nice That、Brand New (Under Consideration)、Dezeen、Creative Review、Design Week
語言：英文、繁體中文、日文

【Step 4】Lenny's Podcast 是否有新集數

篩選規則：
- 48 小時內；多個來源都提到的排名提升
- 長文、有論點優先 > 純新聞；廣告軟文排除
- 接案 / 設計工作室相關的內容排名 ×1.5
- Product 取 5 篇，Brand 取 5 篇

請嚴格以 JSON 格式回傳，不要加任何其他文字或 markdown：
{{
  "jenny_wen": {{
    "has_content": true 或 false,
    "title": "文章標題原文（沒有內容時填空字串）",
    "url": "連結（沒有時填空字串）",
    "summary": "2-3 句繁體中文摘要（沒有內容時填空字串）"
  }},
  "lenny": {{
    "has_content": true 或 false,
    "title": "集數標題（沒有時填空字串）",
    "url": "連結（沒有時填空字串）",
    "summary": "一句話說明主題，繁體中文（沒有時填空字串）"
  }},
  "product": {{
    "articles": [
      {{
        "title": "文章標題原文",
        "url": "連結",
        "source": "來源媒體名稱",
        "lang": "EN 或 繁中 或 日文",
        "studio_related": true 或 false,
        "summary": "一句話白話文摘要，繁體中文"
      }}
    ],
    "buzz": "2-3 句話總結 Product Design 圈這 48 小時在討論的主題，繁體中文"
  }},
  "brand": {{
    "articles": [
      {{
        "title": "文章標題原文",
        "url": "連結",
        "source": "來源媒體名稱",
        "lang": "EN 或 繁中 或 日文",
        "studio_related": true 或 false,
        "summary": "一句話白話文摘要，繁體中文"
      }}
    ],
    "buzz": "2-3 句話總結 Brand 圈這 48 小時在討論的主題，繁體中文"
  }}
}}"""


def generate_briefing():
    """呼叫 Claude API 生成今日早報"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now(TW_TZ).strftime("%Y 年 %m 月 %d 日")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 8
        }],
        messages=[{
            "role": "user",
            "content": PROMPT_TEMPLATE.format(today=today)
        }]
    )

    # 從回應中取出最後一個文字區塊（工具呼叫完成後的最終回答）
    json_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            json_text = block.text  # 取最後一個 text block

    # 清除可能的 markdown code block 包裝
    json_text = json_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_text)
    if match:
        json_text = match.group(1)

    return json.loads(json_text)


def main():
    print("生成今日早報中…")
    data = generate_briefing()

    # 加入日期
    data["date"] = datetime.now(TW_TZ).strftime("%Y-%m-%d")

    # 讀取現有紀錄
    briefings_path = "briefings.json"
    if os.path.exists(briefings_path):
        with open(briefings_path, "r", encoding="utf-8") as f:
            briefings = json.load(f)
    else:
        briefings = []

    # 插入今日，只保留最近 3 天
    briefings.insert(0, data)
    briefings = briefings[:3]

    with open(briefings_path, "w", encoding="utf-8") as f:
        json.dump(briefings, f, ensure_ascii=False, indent=2)

    print(f"✓ 早報已更新：{data['date']}")


if __name__ == "__main__":
    main()
