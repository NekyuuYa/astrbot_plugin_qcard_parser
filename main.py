"""
QQ card parser plugin.
"""

import json
from sys import maxsize
from typing import Optional

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star

from .card_parser import CardParser
from .link_text_utils import append_summary
from .plugin_settings import PluginSettings
from .result_sender import ParseResultSender


class Main(Star):
    """QQ card parser plugin."""

    def __init__(
        self,
        context: Context,
        config: AstrBotConfig | None = None,
    ) -> None:
        super().__init__(context)
        self.context = context
        self.config = config
        self.parser = CardParser()
        self.settings = PluginSettings()
        self.result_sender = ParseResultSender(True, 1500)

        self.verbose = False
        self.debug_echo_raw_json = False
        self.debug_echo_max_chars = 2000
        self.parse_command_use_forward = True
        self.parse_command_forward_threshold = 1500

        self._load_config()
        logger.info("QQ Card Parser plugin loaded")

    def _load_config(self) -> None:
        try:
            self.settings = PluginSettings.load(self.context, self.config)
            self.verbose = self.settings.verbose
            self.debug_echo_raw_json = self.settings.debug_echo_raw_json
            self.debug_echo_max_chars = self.settings.debug_echo_max_chars
            self.parse_command_use_forward = self.settings.parse_command_use_forward
            self.parse_command_forward_threshold = (
                self.settings.parse_command_forward_threshold
            )
            self.result_sender = ParseResultSender(
                use_forward=self.parse_command_use_forward,
                forward_threshold=self.parse_command_forward_threshold,
            )

            if self.verbose:
                logger.info("[QCard Parser] verbose logging enabled")
        except Exception as e:
            logger.debug(f"[QCard Parser] failed to load config: {e}, fallback to defaults")
            self.verbose = False

    @staticmethod
    def _is_self_message(event: AstrMessageEvent) -> bool:
        """Skip processing bot's own messages to avoid re-entrancy side effects."""
        try:
            sender_id = str(event.get_sender_id() or "")
            self_id = str(event.get_self_id() or "")
            return bool(sender_id and self_id and sender_id == self_id)
        except Exception:
            return False

    def _augment_reply_chain(self, reply: Comp.Reply) -> list[str]:
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

        for text in parsed_texts:
            chain.append(Comp.Plain(text=f"\n{text}"))

        existing = (getattr(reply, "message_str", "") or "").strip()
        merged = "\n\n".join(parsed_texts)
        reply.message_str = f"{existing}\n\n{merged}".strip() if existing else merged
        return parsed_texts

    def _parse_cards_from_chain(self, chain: list[object] | None) -> list[str]:
        if not isinstance(chain, list) or not chain:
            return []

        parsed_texts: list[str] = []
        for seg in chain:
            if isinstance(seg, Comp.Json):
                parsed_text = self.parser.parse_json_card(seg.data)
                if parsed_text:
                    parsed_texts.append(parsed_text)
        return parsed_texts

    def _collect_parsed_from_replies(self, replies: list[Comp.Reply]) -> list[str]:
        all_parsed_texts: list[str] = []
        for reply in replies:
            parsed_texts = self._parse_cards_from_chain(getattr(reply, "chain", None))
            if parsed_texts:
                all_parsed_texts.extend(parsed_texts)
                continue

            reply_text = (getattr(reply, "message_str", "") or "").strip()
            if reply_text and ("[小程序]" in reply_text or "[分享]" in reply_text):
                all_parsed_texts.append(reply_text)
        return all_parsed_texts

    async def _echo_raw_json_if_needed(
        self,
        event: AstrMessageEvent,
        component: Comp.Json,
    ) -> None:
        if not self.debug_echo_raw_json:
            return

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
                    raw_json_text[: self.debug_echo_max_chars] + "\n... (truncated)"
                )

            await event.send(
                MessageChain().message("[QCard Debug] 收到原始 Json:\n" + raw_json_text),
            )
        except Exception as e:
            logger.warning(f"[QCard Parser] failed to echo raw Json: {e}")

    def _inject_parsed_cards_to_event(
        self,
        event: AstrMessageEvent,
        parsed_cards: list[str],
    ) -> None:
        card_summary = "\n\n".join(parsed_cards)
        event.message_str = append_summary(event.message_str, card_summary)
        event.message_obj.message_str = append_summary(
            event.message_obj.message_str,
            card_summary,
        )

        if self.verbose:
            logger.info(
                f"[QCard Parser] injected {len(parsed_cards)} parsed cards:\n{card_summary}"
            )
        else:
            logger.debug(f"[QCard Parser] injected {len(parsed_cards)} parsed cards")

    def _parse_json_component(self, component: Comp.Json) -> Optional[str]:
        raw_data = component.data
        if isinstance(raw_data, dict):
            return self.parser.parse_json_card(raw_data)
        if isinstance(raw_data, str):
            return self.parser.parse_json_card(raw_data)
        return None

    async def _send_parse_result(
        self,
        event: AstrMessageEvent,
        parsed_texts: list[str],
    ) -> None:
        await self.result_sender.send(event, parsed_texts)

    @filter.command("解析卡片")
    async def parse_card_command(self, event: AstrMessageEvent) -> None:
        if self._is_self_message(event):
            return

        reply_components = [
            comp for comp in event.message_obj.message if isinstance(comp, Comp.Reply)
        ]

        if not reply_components:
            await event.send(
                MessageChain().message("请先引用一条卡片消息，再发送 /解析卡片"),
            )
            return

        all_parsed_texts = self._collect_parsed_from_replies(reply_components)

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
        try:
            if self._is_self_message(event):
                return

            message_chain = event.message_obj.message
            if not message_chain:
                return

            parsed_cards = []

            for component in message_chain:
                if not isinstance(component, Comp.Json):
                    if isinstance(component, Comp.Reply):
                        reply_parsed = self._augment_reply_chain(component)
                        if reply_parsed and self.verbose:
                            logger.info(
                                "[QCard Parser] parsed cards injected into reply chain, count: "
                                f"{len(reply_parsed)}"
                            )
                        elif self.verbose and getattr(component, "id", None):
                            logger.info(
                                "[QCard Parser] reply has no parsable Json chain; "
                                "plugin cannot fetch content with only reply_id"
                            )
                    continue

                if self.verbose:
                    logger.info(
                        f"[QCard Parser] detected Json component: {str(component.data)[:100]}..."
                    )

                await self._echo_raw_json_if_needed(event, component)
                parsed_text = self._parse_json_component(component)

                if parsed_text:
                    parsed_cards.append(parsed_text)
                    if self.verbose:
                        logger.info(f"[QCard Parser] parsed result:\n{parsed_text}")
                    else:
                        logger.debug(f"[QCard Parser] parse success: {parsed_text[:50]}...")
                elif self.verbose:
                    logger.info("[QCard Parser] Json is not a supported card type, skipped")

            if parsed_cards:
                self._inject_parsed_cards_to_event(event, parsed_cards)

        except Exception as e:
            logger.error(f"[QCard Parser] failed to handle message: {e}", exc_info=True)

    async def terminate(self) -> None:
        logger.info("[QCard Parser] plugin unloaded")
