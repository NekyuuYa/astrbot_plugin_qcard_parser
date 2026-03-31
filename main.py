"""
QQ 卡片消息解析插件 - 独立版本

支持解析:
1. 小程序卡片 (app="com.tencent.miniapp")
2. 链接分享卡片 (app="com.tencent.structmsg", view="news")

将卡片转换为易读的结构化文本，便于 LLM 理解。
"""

import json
from sys import maxsize
from typing import Optional

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star


class CardParser:
    """QQ 卡片消息解析器
    
    支持的卡片类型:
    - 小程序卡片 (com.tencent.miniapp)
    - 链接分享卡片 (com.tencent.structmsg + view=news)
    """

    @staticmethod
    def parse_miniapp_card(data: dict) -> Optional[str]:
        """解析小程序卡片
        
        提取关键字段:
        - title: 应用名称
        - preview: 预览图链接
        - jumpUrl: 跳转链接
        
        Args:
            data: JSON 卡片数据字典
            
        Returns:
            易读的文本内容，如果不是小程序卡片返回 None
        """
        try:
            # 验证是否为小程序卡片
            if data.get("app") != "com.tencent.miniapp":
                return None

            # 提取关键字段（忽略 icon, appID 等无用参数）
            title = data.get("title", "").strip()
            preview = data.get("preview", "").strip()
            jump_url = data.get("jumpUrl", "").strip()

            # 构造易读文本
            parts = ["[小程序]"]

            if title:
                parts.append(f"名称: {title}")

            if preview:
                parts.append(f"预览: {preview}")

            if jump_url:
                parts.append(f"链接: {jump_url}")

            return "\n".join(parts)

        except Exception as e:
            logger.debug(f"Failed to parse miniapp card: {e}")
            return None

    @staticmethod
    def parse_link_share_card(data: dict) -> Optional[str]:
        """解析链接分享卡片
        
        提取关键字段:
        - meta.news.title: 网页标题
        - meta.news.desc: 网页描述
        - meta.news.tag: 来源标签
        - meta.news.url: 目标链接
        
        Args:
            data: JSON 卡片数据字典
            
        Returns:
            易读的文本内容，如果不是链接分享卡片返回 None
        """
        try:
            # 验证是否为链接分享卡片
            if data.get("app") != "com.tencent.structmsg":
                return None
            if data.get("view") != "news":
                return None

            # 提取 meta.news 下的内容
            meta = data.get("meta", {})
            news = meta.get("news", {})

            if not isinstance(news, dict):
                return None

            # 提取关键字段（忽略 appid, preview, source_icon 等无用参数）
            title = news.get("title", "").strip()
            desc = news.get("desc", "").strip()
            url = news.get("url", "").strip()
            tag = news.get("tag", "").strip()

            # 如果没有有用的信息，返回 None
            if not title and not desc:
                return None

            # 构造易读文本
            parts = ["[分享]"]

            if title:
                parts.append(f"标题: {title}")

            if desc:
                # 如果描述很长，截断处理（防止 LLM 处理困难）
                if len(desc) > 100:
                    desc = desc[:100] + "..."
                parts.append(f"描述: {desc}")

            if tag:
                parts.append(f"来源: {tag}")

            if url:
                parts.append(f"链接: {url}")

            return "\n".join(parts)

        except Exception as e:
            logger.debug(f"Failed to parse link share card: {e}")
            return None

    @classmethod
    def parse_json_card(cls, raw_json) -> Optional[str]:
        """尝试解析 JSON 卡片
        
        按优先级尝试不同类型的卡片解析器:
        1. 小程序卡片
        2. 链接分享卡片
        
        Args:
            raw_json: 原始 JSON 字符串或字典
            
        Returns:
            易读的文本内容，如果无法识别返回 None
        """
        try:
            if isinstance(raw_json, str):
                data = json.loads(raw_json)
            else:
                data = raw_json

            if not isinstance(data, dict):
                return None

            # 尝试小程序卡片
            result = cls.parse_miniapp_card(data)
            if result:
                return result

            # 尝试链接分享卡片
            result = cls.parse_link_share_card(data)
            if result:
                return result

            # 无法识别的卡片类型
            return None

        except Exception as e:
            logger.debug(f"Failed to parse JSON card: {e}")
            return None


class Main(Star):
    """QQ 卡片消息解析插件 - 独立版本
    
    自动解析 QQ 卡片消息（小程序、链接分享等），
    将其转换为易读的文本，使 LLM 能够理解卡片内容。
    """

    def __init__(
        self,
        context: Context,
        config: AstrBotConfig | None = None,
    ) -> None:
        super().__init__(context)
        self.parser = CardParser()
        self.context = context
        self.config = config
        self.verbose = False
        self._load_config()
        logger.info("QQ Card Parser plugin loaded")
    
    def _load_config(self) -> None:
        """加载插件配置。

        优先级：
        1. 插件 schema 注入配置（self.config）
        2. 全局 provider_settings.qcard_parser（回退兼容）
        """
        try:
            if self.config:
                self.verbose = bool(self.config.get("verbose", False))
            else:
                cfg = self.context.get_config()
                provider_settings = cfg.get("provider_settings", {})
                qcard_settings = provider_settings.get("qcard_parser", {})
                self.verbose = bool(qcard_settings.get("verbose", False))

            if self.verbose:
                logger.info("[QCard Parser] 详尽日志已启用")
        except Exception as e:
            logger.debug(f"[QCard Parser] 加载配置失败: {e}，使用默认配置")
            self.verbose = False

    @filter.event_message_type(filter.EventMessageType.ALL, priority=maxsize - 2)
    async def parse_qq_cards(self, event: AstrMessageEvent) -> None:
        """高优先级处理消息中的 QQ 卡片
        
        在消息被发送给 LLM 前进行解析，确保 LLM 能够理解卡片内容。
        
        Args:
            event: 消息事件
        """
        try:
            # 检查消息链是否存在
            message_chain = event.message_obj.message
            if not message_chain:
                return

            parsed_cards = []

            # 遍历消息链中的所有组件
            for component in message_chain:
                # 只处理 Json 组件（卡片消息）
                if not isinstance(component, Comp.Json):
                    continue
                if self.verbose:
                    logger.info(f"[QCard Parser] 检测到 Json 组件: {str(component.data)[:100]}...")


                # 尝试解析 JSON 卡片
                raw_data = component.data
                parsed_text = None

                if isinstance(raw_data, dict):
                    parsed_text = self.parser.parse_json_card(raw_data)
                elif isinstance(raw_data, str):
                    # 某些情况下 data 可能是字符串
                    parsed_text = self.parser.parse_json_card(raw_data)

                if parsed_text:
                    parsed_cards.append(parsed_text)
                    if self.verbose:
                        logger.info(f"[QCard Parser] 解析结果:\\n{parsed_text}")
                    else:
                        logger.debug(f"[QCard Parser] 成功解析卡片: {parsed_text[:50]}...")
                elif self.verbose:
                    logger.info("[QCard Parser] 未识别为可解析卡片，已跳过")

            # 如果成功解析了卡片，将其注入消息
            if parsed_cards:
                # 构造卡片文本摘要
                card_summary = "\n\n".join(parsed_cards)

                # 附加到 message_str，使 LLM 能够接收
                if event.message_obj.message_str:
                    event.message_obj.message_str += f"\n\n{card_summary}"
                else:
                    event.message_obj.message_str = card_summary

                if self.verbose:
                    logger.info(
                        f"[QCard Parser] 已注入 {len(parsed_cards)} 个卡片到消息:\n{card_summary}"
                    )
                else:
                    logger.debug(
                        f"[QCard Parser] 已注入 {len(parsed_cards)} 个卡片到消息"
                    )

        except Exception as e:
            logger.error(f"[QCard Parser] 处理消息时出错: {e}", exc_info=True)
            # 不中断事件流，安全继续处理
    
    async def terminate(self) -> None:
        """插件卸载时调用"""
        logger.info("[QCard Parser] 插件已卸载")
