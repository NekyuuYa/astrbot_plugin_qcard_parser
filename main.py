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
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star


class CardParser:
    """QQ 卡片消息解析器
    
    支持的卡片类型:
    - 小程序卡片 (com.tencent.miniapp)
    - 链接分享卡片 (com.tencent.structmsg + view=news)
    """

    @staticmethod
    def _pick_str_by_paths(data: dict, paths: list[tuple[str, ...]]) -> str:
        """按路径列表提取第一个非空字符串值。"""
        for path in paths:
            current = data
            ok = True
            for key in path:
                if not isinstance(current, dict) or key not in current:
                    ok = False
                    break
                current = current[key]
            if ok and isinstance(current, str):
                value = current.strip()
                if value:
                    return value
        return ""

    @staticmethod
    def _strip_prompt_prefix(prompt: str) -> str:
        text = prompt.strip()
        for prefix in ("[QQ小程序]", "[小程序]", "[分享]", "[链接]", "[网页]"):
            if text.startswith(prefix):
                return text[len(prefix) :].strip()
        return text

    @staticmethod
    def parse_miniapp_card(data: dict) -> Optional[str]:
        """解析小程序卡片
        
        提取关键字段:
        - title: 应用名称
        - prompt: 卡片提示文本
        - jumpUrl: 跳转链接
        
        Args:
            data: JSON 卡片数据字典
            
        Returns:
            易读的文本内容，如果不是小程序卡片返回 None
        """
        try:
            app = str(data.get("app", ""))
            prompt = str(data.get("prompt", "")).strip()

            # 兼容：部分 QQ 小程序卡片没有 app 字段，只能通过 prompt 识别
            is_miniapp = app == "com.tencent.miniapp" or prompt.startswith(
                ("[QQ小程序]", "[小程序]"),
            )
            if not is_miniapp:
                return None

            # 提取关键字段（忽略 icon, appID 等无用参数）
            title = CardParser._pick_str_by_paths(
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
                title = CardParser._strip_prompt_prefix(prompt)

            jump_url = CardParser._pick_str_by_paths(
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

            # 构造易读文本
            parts = []

            if prompt:
                prompt_text = CardParser._strip_prompt_prefix(prompt)
                parts.append(f"标题: {prompt_text}")

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
            app = str(data.get("app", ""))
            view = str(data.get("view", ""))
            prompt = str(data.get("prompt", "")).strip()

            # 宽松识别：支持结构消息卡片、第三方平台分享卡片
            is_share = (
                (app == "com.tencent.structmsg" and view == "news")
                or app.startswith("com.tencent.tuwen")
                or prompt.startswith(("[分享]", "[链接]", "[网页]"))
            )
            if not is_share:
                return None

            # 提取 meta.news 下的内容
            meta = data.get("meta", {})
            news = meta.get("news", {})

            # 提取关键字段（忽略 appid, preview, source_icon 等无用参数）
            title = CardParser._pick_str_by_paths(
                data,
                [
                    ("meta", "news", "title"),
                    ("meta", "detail_1", "title"),
                    ("meta", "detail", "title"),
                    ("title",),
                ],
            )
            if not title and prompt:
                title = CardParser._strip_prompt_prefix(prompt)

            desc = CardParser._pick_str_by_paths(
                data,
                [
                    ("meta", "news", "desc"),
                    ("meta", "detail_1", "desc"),
                    ("meta", "detail", "desc"),
                    ("desc",),
                ],
            )
            url = CardParser._pick_str_by_paths(
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
            tag = CardParser._pick_str_by_paths(
                data,
                [
                    ("meta", "news", "tag"),
                    ("meta", "detail_1", "tag"),
                    ("meta", "detail", "tag"),
                    ("source",),
                ],
            )

            # 如果没有有用的信息，返回 None
            if not title and not desc and not url:
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
        self.debug_echo_raw_json = False
        self.debug_echo_max_chars = 2000
        self.parse_command_use_forward = True
        self.parse_command_forward_threshold = 1500
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
                self.debug_echo_raw_json = bool(
                    self.config.get("debug_echo_raw_json", False),
                )
                self.debug_echo_max_chars = int(
                    self.config.get("debug_echo_max_chars", 2000),
                )
                self.parse_command_use_forward = bool(
                    self.config.get("parse_command_use_forward", True),
                )
                self.parse_command_forward_threshold = int(
                    self.config.get("parse_command_forward_threshold", 1500),
                )
            else:
                cfg = self.context.get_config()
                provider_settings = cfg.get("provider_settings", {})
                qcard_settings = provider_settings.get("qcard_parser", {})
                self.verbose = bool(qcard_settings.get("verbose", False))
                self.debug_echo_raw_json = bool(
                    qcard_settings.get("debug_echo_raw_json", False),
                )
                self.debug_echo_max_chars = int(
                    qcard_settings.get("debug_echo_max_chars", 2000),
                )
                self.parse_command_use_forward = bool(
                    qcard_settings.get("parse_command_use_forward", True),
                )
                self.parse_command_forward_threshold = int(
                    qcard_settings.get("parse_command_forward_threshold", 1500),
                )

            if self.debug_echo_max_chars < 200:
                self.debug_echo_max_chars = 200

            if self.parse_command_forward_threshold < 200:
                self.parse_command_forward_threshold = 200

            if self.verbose:
                logger.info("[QCard Parser] 详尽日志已启用")
        except Exception as e:
            logger.debug(f"[QCard Parser] 加载配置失败: {e}，使用默认配置")
            self.verbose = False

    def _augment_reply_chain(self, reply: Comp.Reply) -> list[str]:
        """将 Reply 链中的 Json 卡片解析为 Plain 文本，便于引用链路读取。"""
        chain = getattr(reply, "chain", None)
        if not isinstance(chain, list) or not chain:
            return []

        parsed_texts: list[str] = []
        for seg in chain:
            if not isinstance(seg, Comp.Json):
                continue
            parsed_text = self.parser.parse_json_card(seg.data)
            if parsed_text:
                parsed_texts.append(parsed_text)

        if not parsed_texts:
            return []

        # 注入 Plain 到 reply.chain，供 quoted_message 解析器读取
        for text in parsed_texts:
            chain.append(Comp.Plain(text=f"\n{text}"))

        # 同步 reply.message_str，部分路径会直接读取该字段
        existing = (getattr(reply, "message_str", "") or "").strip()
        merged = "\n\n".join(parsed_texts)
        reply.message_str = f"{existing}\n\n{merged}".strip() if existing else merged
        return parsed_texts

    def _parse_cards_from_chain(self, chain: list[object] | None) -> list[str]:
        """从消息链中提取并解析 Json 卡片文本。"""
        if not isinstance(chain, list) or not chain:
            return []

        parsed_texts: list[str] = []
        for seg in chain:
            if isinstance(seg, Comp.Json):
                parsed_text = self.parser.parse_json_card(seg.data)
                if parsed_text:
                    parsed_texts.append(parsed_text)
        return parsed_texts

    async def _send_parse_result(
        self,
        event: AstrMessageEvent,
        parsed_texts: list[str],
    ) -> None:
        """按长度条件发送解析结果：过长时使用合并转发。"""
        if len(parsed_texts) == 1:
            plain_result = parsed_texts[0]
        else:
            plain_result = "\n\n".join(
                [
                    f"[解析结果 {idx}]\n{text}"
                    for idx, text in enumerate(parsed_texts, 1)
                ],
            )

        threshold = self.parse_command_forward_threshold
        use_forward = (
            self.parse_command_use_forward
            and threshold > 0
            and event.get_platform_name() == "aiocqhttp"
            and len(plain_result) > threshold
        )

        if not use_forward:
            await event.send(MessageChain().message(plain_result))
            return

        bot_name = event.get_self_id() or "AstrBot"
        nodes: list[Comp.Node] = []
        for idx, text in enumerate(parsed_texts, 1):
            content = text if len(parsed_texts) == 1 else f"[解析结果 {idx}]\n{text}"
            nodes.append(
                Comp.Node(
                    uin=event.get_self_id(),
                    name=str(bot_name),
                    content=[Comp.Plain(text=content)],
                ),
            )

        await event.send(MessageChain([Comp.Nodes(nodes=nodes)]))

    @filter.command("解析卡片")
    async def parse_card_command(self, event: AstrMessageEvent) -> None:
        """解析被引用消息中的 QQ 卡片。使用方式：引用消息并发送 /解析卡片"""
        reply_components = [
            comp for comp in event.message_obj.message if isinstance(comp, Comp.Reply)
        ]

        if not reply_components:
            await event.send(
                MessageChain().message("请先引用一条卡片消息，再发送 /解析卡片"),
            )
            return

        all_parsed_texts: list[str] = []
        for reply in reply_components:
            # 优先从 reply.chain 解析
            parsed_texts = self._parse_cards_from_chain(getattr(reply, "chain", None))
            if parsed_texts:
                all_parsed_texts.extend(parsed_texts)
                continue

            # 若 chain 不可用，尝试从已有 message_str 返回提示
            reply_text = (getattr(reply, "message_str", "") or "").strip()
            if reply_text and ("[小程序]" in reply_text or "[分享]" in reply_text):
                all_parsed_texts.append(reply_text)

        if not all_parsed_texts:
            await event.send(
                MessageChain().message(
                    "未在引用消息中找到可解析的卡片 Json。"
                    "\n提示：请引用 OneBot 下发的卡片消息（Json 组件）。",
                ),
            )
            return

        await self._send_parse_result(event, all_parsed_texts)

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
                    # 处理引用链中的 Json 卡片
                    if isinstance(component, Comp.Reply):
                        reply_parsed = self._augment_reply_chain(component)
                        if reply_parsed and self.verbose:
                            logger.info(
                                "[QCard Parser] 已为引用消息注入解析文本，条数: "
                                f"{len(reply_parsed)}"
                            )
                        elif self.verbose and getattr(component, "id", None):
                            logger.info(
                                "[QCard Parser] 引用消息未含可解析 Json 链，"
                                "若仅 reply_id 无 chain，插件层无法补全"
                            )
                    continue
                if self.verbose:
                    logger.info(f"[QCard Parser] 检测到 Json 组件: {str(component.data)[:100]}...")

                if self.debug_echo_raw_json:
                    try:
                        if isinstance(component.data, dict):
                            raw_json_text = json.dumps(
                                component.data,
                                ensure_ascii=False,
                                indent=2,
                            )
                        else:
                            raw_json_text = str(component.data)
                        if len(raw_json_text) > self.debug_echo_max_chars:
                            raw_json_text = (
                                raw_json_text[: self.debug_echo_max_chars]
                                + "\n... (truncated)"
                            )
                        await event.send(
                            MessageChain().message(
                                "[QCard Debug] 收到原始 Json:\n" + raw_json_text,
                            ),
                        )
                    except Exception as e:
                        logger.warning(f"[QCard Parser] 回显原始 Json 失败: {e}")


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
                        logger.info(f"[QCard Parser] 解析结果:\n{parsed_text}")
                    else:
                        logger.debug(f"[QCard Parser] 成功解析卡片: {parsed_text[:50]}...")
                elif self.verbose:
                    logger.info("[QCard Parser] 未识别为可解析卡片，已跳过")

            # 如果成功解析了卡片，将其注入消息
            if parsed_cards:
                # 构造卡片文本摘要
                card_summary = "\n\n".join(parsed_cards)

                # 同步附加到 event.message_str 与 message_obj.message_str。
                # Main Agent 构建请求时读取的是 event.message_str。
                if event.message_str:
                    event.message_str += f"\n\n{card_summary}"
                else:
                    event.message_str = card_summary

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
