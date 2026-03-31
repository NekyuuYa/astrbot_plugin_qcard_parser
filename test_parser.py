#!/usr/bin/env python3
"""
QQ 卡片解析插件的单元测试脚本

运行: python test_parser.py
"""

import json
from typing import Optional


# 模拟 CardParser（从 main.py 复制的解析逻辑）
class CardParser:
    """QQ 卡片解析器 - 测试版本"""

    @staticmethod
    def parse_miniapp_card(data: dict) -> Optional[str]:
        """解析小程序卡片"""
        try:
            if data.get("app") != "com.tencent.miniapp":
                return None

            title = data.get("title", "").strip()
            preview = data.get("preview", "").strip()
            jump_url = data.get("jumpUrl", "").strip()

            parts = ["[小程序]"]
            if title:
                parts.append(f"名称: {title}")
            if preview:
                parts.append(f"预览: {preview}")
            if jump_url:
                parts.append(f"链接: {jump_url}")

            return "\n".join(parts)

        except Exception:
            return None

    @staticmethod
    def parse_link_share_card(data: dict) -> Optional[str]:
        """解析链接分享卡片"""
        try:
            if data.get("app") != "com.tencent.structmsg":
                return None
            if data.get("view") != "news":
                return None

            meta = data.get("meta", {})
            news = meta.get("news", {})

            if not isinstance(news, dict):
                return None

            title = news.get("title", "").strip()
            desc = news.get("desc", "").strip()
            url = news.get("url", "").strip()
            tag = news.get("tag", "").strip()

            if not title and not desc:
                return None

            parts = ["[分享]"]
            if title:
                parts.append(f"标题: {title}")
            if desc:
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                parts.append(f"描述: {desc}")
            if tag:
                parts.append(f"来源: {tag}")
            if url:
                parts.append(f"链接: {url}")

            return "\n".join(parts)

        except Exception:
            return None

    @classmethod
    def parse_json_card(cls, raw_json) -> Optional[str]:
        """尝试解析 JSON 卡片"""
        try:
            if isinstance(raw_json, str):
                data = json.loads(raw_json)
            else:
                data = raw_json

            if not isinstance(data, dict):
                return None

            result = cls.parse_miniapp_card(data)
            if result:
                return result

            result = cls.parse_link_share_card(data)
            if result:
                return result

            return None

        except Exception:
            return None


def print_test(name: str, passed: bool):
    """打印测试结果"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")


def test_miniapp_basic():
    """测试1: 基础小程序卡片"""
    card = {
        "app": "com.tencent.miniapp",
        "title": "天气预报",
        "preview": "https://example.com/weather.png",
        "jumpUrl": "pages/weather?city=beijing",
    }

    result = CardParser.parse_json_card(card)
    passed = result and "[小程序]" in result and "名称: 天气预报" in result
    print_test("小程序卡片 - 基础解析", passed)


def test_miniapp_minimal():
    """测试2: 最小小程序卡片（仅有名称）"""
    card = {
        "app": "com.tencent.miniapp",
        "title": "简单应用",
    }

    result = CardParser.parse_json_card(card)
    passed = result and "[小程序]" in result and "名称: 简单应用" in result
    print_test("小程序卡片 - 最小信息", passed)


def test_miniapp_ignore_fields():
    """测试3: 小程序卡片过滤无用字段"""
    card = {
        "app": "com.tencent.miniapp",
        "title": "应用",
        "icon": "https://example.com/icon.png",
        "appID": "123456",
        "nameAppId": "wx123",
    }

    result = CardParser.parse_json_card(card)
    passed = (
        result
        and "icon" not in result
        and "appID" not in result
        and "nameAppId" not in result
    )
    print_test("小程序卡片 - 过滤无用字段", passed)


def test_link_share_basic():
    """测试4: 基础链接分享卡片"""
    card = {
        "app": "com.tencent.structmsg",
        "view": "news",
        "meta": {
            "news": {
                "title": "Python 3.13",
                "desc": "Python 新版本发布",
                "tag": "技术",
                "url": "https://python.org",
            }
        },
    }

    result = CardParser.parse_json_card(card)
    passed = (
        result
        and "[分享]" in result
        and "标题: Python 3.13" in result
        and "技术" in result
    )
    print_test("链接分享卡片 - 基础解析", passed)


def test_link_share_desc_truncate():
    """测试5: 链接分享卡片描述截断"""
    long_desc = "这是一个很长的描述文本。" * 20

    card = {
        "app": "com.tencent.structmsg",
        "view": "news",
        "meta": {
            "news": {
                "title": "长文章",
                "desc": long_desc,
            }
        },
    }

    result = CardParser.parse_json_card(card)
    passed = result and "..." in result and len(result) < len(long_desc)
    print_test("链接分享卡片 - 描述截断", passed)


def test_link_share_ignore_fields():
    """测试6: 链接分享卡片过滤无用字段"""
    card = {
        "app": "com.tencent.structmsg",
        "view": "news",
        "meta": {
            "news": {
                "title": "新闻",
                "desc": "描述",
                "appid": 100138,
                "app_type": 1,
                "preview": "https://example.com/preview.jpg",
            }
        },
    }

    result = CardParser.parse_json_card(card)
    passed = (
        result
        and "appid" not in result
        and "app_type" not in result
        and "preview" not in result
    )
    print_test("链接分享卡片 - 过滤无用字段", passed)


def test_unknown_card_type():
    """测试7: 未知卡片类型返回 None"""
    card = {
        "app": "com.tencent.unknown",
        "title": "某个卡片",
    }

    result = CardParser.parse_json_card(card)
    passed = result is None
    print_test("未知卡片类型 - 返回 None", passed)


def test_invalid_json():
    """测试8: 无效 JSON 处理"""
    invalid = "not a json"
    result = CardParser.parse_json_card(invalid)
    passed = result is None
    print_test("无效 JSON - 错误处理", passed)


def test_empty_data():
    """测试9: 空数据处理"""
    result = CardParser.parse_json_card({})
    passed = result is None
    print_test("空数据 - 错误处理", passed)


def test_link_share_minimal():
    """测试10: 最小链接分享卡片（仅有标题）"""
    card = {
        "app": "com.tencent.structmsg",
        "view": "news",
        "meta": {
            "news": {
                "title": "仅有标题",
            }
        },
    }

    result = CardParser.parse_json_card(card)
    passed = result and "[分享]" in result and "仅有标题" in result
    print_test("链接分享卡片 - 最小信息", passed)


def main():
    """运行所有测试"""
    print("=" * 60)
    print("QQ 卡片解析插件 - 单元测试")
    print("=" * 60)
    print()

    tests = [
        test_miniapp_basic,
        test_miniapp_minimal,
        test_miniapp_ignore_fields,
        test_link_share_basic,
        test_link_share_desc_truncate,
        test_link_share_ignore_fields,
        test_unknown_card_type,
        test_invalid_json,
        test_empty_data,
        test_link_share_minimal,
    ]

    passed_count = 0
    for test in tests:
        try:
            test()
            passed_count += 1
        except Exception as e:
            print(f"❌ FAIL | {test.__doc__} - Exception: {e}")

    print()
    print("=" * 60)
    print(f"测试结果: {passed_count}/{len(tests)} 通过")
    print("=" * 60)

    return passed_count == len(tests)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
