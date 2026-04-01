import astrbot.api.message_components as Comp
from astrbot.api.event import AstrMessageEvent, MessageChain


class ParseResultSender:
    def __init__(self, use_forward: bool, forward_threshold: int) -> None:
        self.use_forward = use_forward
        self.forward_threshold = forward_threshold

    @staticmethod
    def format_result(parsed_texts: list[str]) -> str:
        if len(parsed_texts) == 1:
            return parsed_texts[0]
        return "\n\n".join(
            [f"[解析结果 {idx}]\n{text}" for idx, text in enumerate(parsed_texts, 1)],
        )

    def should_use_forward(self, event: AstrMessageEvent, plain_result: str) -> bool:
        return (
            self.use_forward
            and self.forward_threshold > 0
            and event.get_platform_name() == "aiocqhttp"
            and len(plain_result) > self.forward_threshold
        )

    @staticmethod
    def build_forward_nodes(event: AstrMessageEvent, parsed_texts: list[str]) -> list[Comp.Node]:
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
        return nodes

    async def send(self, event: AstrMessageEvent, parsed_texts: list[str]) -> None:
        plain_result = self.format_result(parsed_texts)
        if not self.should_use_forward(event, plain_result):
            await event.send(MessageChain().message(plain_result))
            return
        await event.send(
            MessageChain([Comp.Nodes(nodes=self.build_forward_nodes(event, parsed_texts))]),
        )
