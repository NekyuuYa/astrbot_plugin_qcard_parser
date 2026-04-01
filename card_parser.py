import json
from typing import Optional

from astrbot.api import logger

from link_text_utils import clean_music_url, pick_first_str_by_paths, strip_prompt_prefix, truncate_text


class CardParser:
    """QQ card message parser."""

    @staticmethod
    def parse_miniapp_card(data: dict) -> Optional[str]:
        try:
            app = str(data.get("app", ""))
            prompt = str(data.get("prompt", "")).strip()

            is_miniapp = app == "com.tencent.miniapp" or prompt.startswith(
                ("[QQ小程序]", "[小程序]"),
            )
            if not is_miniapp:
                return None

            title = pick_first_str_by_paths(
                data,
                [
                    ("title",),
                    ("meta", "detail_1", "title"),
                    ("meta", "detail", "title"),
                    ("meta", "news", "title"),
                    ("desc",),
                ],
            )
            if not title and prompt:
                title = strip_prompt_prefix(prompt)

            jump_url = pick_first_str_by_paths(
                data,
                [
                    ("meta", "detail_1", "qqdocurl"),
                    ("meta", "detail", "qqdocurl"),
                    ("meta", "news", "jumpUrl"),
                    ("jumpUrl",),
                    ("url",),
                    ("meta", "detail_1", "url"),
                    ("meta", "detail", "url"),
                    ("meta", "news", "url"),
                ],
            )

            parts = []
            if prompt:
                parts.append(f"标题: {strip_prompt_prefix(prompt)}")
            if title:
                parts.append(f"来源: {title}")
            if jump_url:
                parts.append(f"链接: {jump_url}")
            return "\n".join(parts)
        except Exception as e:
            logger.debug(f"Failed to parse miniapp card: {e}")
            return None

    @staticmethod
    def parse_link_share_card(data: dict) -> Optional[str]:
        try:
            app = str(data.get("app", ""))
            view = str(data.get("view", ""))
            prompt = str(data.get("prompt", "")).strip()

            is_share = (
                (app == "com.tencent.structmsg" and view == "news")
                or app.startswith("com.tencent.tuwen")
                or prompt.startswith(("[分享]", "[链接]", "[网页]"))
            )
            if not is_share:
                return None

            title = pick_first_str_by_paths(
                data,
                [
                    ("meta", "news", "title"),
                    ("meta", "detail_1", "title"),
                    ("meta", "detail", "title"),
                    ("title",),
                ],
            )
            if not title and prompt:
                title = strip_prompt_prefix(prompt)

            desc = pick_first_str_by_paths(
                data,
                [
                    ("meta", "news", "desc"),
                    ("meta", "detail_1", "desc"),
                    ("meta", "detail", "desc"),
                    ("desc",),
                ],
            )
            url = pick_first_str_by_paths(
                data,
                [
                    ("meta", "news", "qqdocurl"),
                    ("meta", "detail_1", "qqdocurl"),
                    ("meta", "detail", "qqdocurl"),
                    ("meta", "news", "jumpUrl"),
                    ("meta", "detail_1", "jumpUrl"),
                    ("meta", "news", "url"),
                    ("meta", "detail_1", "url"),
                    ("meta", "detail", "url"),
                    ("jumpUrl",),
                    ("url",),
                ],
            )
            tag = pick_first_str_by_paths(
                data,
                [
                    ("meta", "news", "tag"),
                    ("meta", "detail_1", "tag"),
                    ("meta", "detail", "tag"),
                    ("source",),
                ],
            )

            if not title and not desc and not url:
                return None

            parts = ["[分享]"]
            if title:
                parts.append(f"标题: {title}")
            if desc:
                parts.append(f"描述: {truncate_text(desc, 100)}")
            if tag:
                parts.append(f"来源: {tag}")
            if url:
                parts.append(f"链接: {url}")
            return "\n".join(parts)
        except Exception as e:
            logger.debug(f"Failed to parse link share card: {e}")
            return None

    @staticmethod
    def parse_music_card(data: dict) -> Optional[str]:
        try:
            app = str(data.get("app", ""))
            view = str(data.get("view", ""))
            prompt = str(data.get("prompt", "")).strip()

            is_music = (app.startswith("com.tencent.music") and view == "music") or prompt.startswith("[分享]")
            if not is_music:
                return None

            music = data.get("meta", {}).get("music", {})
            if not music:
                return None

            title = pick_first_str_by_paths(music, [("title",)])
            artist = pick_first_str_by_paths(music, [("desc",)])
            url = pick_first_str_by_paths(music, [("jumpUrl",), ("musicUrl",), ("url",)])
            if url:
                url = clean_music_url(url)
            tag = pick_first_str_by_paths(music, [("tag",), ("source",)])

            if not title:
                return None

            parts = ["[音乐]"]
            parts.append(f"歌曲: {title}")
            if artist:
                parts.append(f"艺术家: {artist}")
            if tag:
                parts.append(f"来源: {tag}")
            if url:
                parts.append(f"链接: {url}")
            return "\n".join(parts)
        except Exception as e:
            logger.debug(f"Failed to parse music card: {e}")
            return None

    @classmethod
    def parse_json_card(cls, raw_json) -> Optional[str]:
        try:
            data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            if not isinstance(data, dict):
                return None

            for parser in (cls.parse_miniapp_card, cls.parse_music_card, cls.parse_link_share_card):
                result = parser(data)
                if result:
                    return result
            return None
        except Exception as e:
            logger.debug(f"Failed to parse JSON card: {e}")
            return None
