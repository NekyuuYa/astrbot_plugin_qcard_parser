from dataclasses import dataclass

from astrbot.api import AstrBotConfig
from astrbot.api.star import Context


@dataclass
class PluginSettings:
    verbose: bool = False
    debug_echo_raw_json: bool = False
    debug_echo_max_chars: int = 2000
    parse_command_use_forward: bool = True
    parse_command_forward_threshold: int = 1500

    @classmethod
    def load(cls, context: Context, config: AstrBotConfig | None) -> "PluginSettings":
        if config:
            settings = cls(
                verbose=bool(config.get("verbose", False)),
                debug_echo_raw_json=bool(config.get("debug_echo_raw_json", False)),
                debug_echo_max_chars=int(config.get("debug_echo_max_chars", 2000)),
                parse_command_use_forward=bool(config.get("parse_command_use_forward", True)),
                parse_command_forward_threshold=int(config.get("parse_command_forward_threshold", 1500)),
            )
        else:
            cfg = context.get_config()
            provider_settings = cfg.get("provider_settings", {})
            qcard_settings = provider_settings.get("qcard_parser", {})
            settings = cls(
                verbose=bool(qcard_settings.get("verbose", False)),
                debug_echo_raw_json=bool(qcard_settings.get("debug_echo_raw_json", False)),
                debug_echo_max_chars=int(qcard_settings.get("debug_echo_max_chars", 2000)),
                parse_command_use_forward=bool(qcard_settings.get("parse_command_use_forward", True)),
                parse_command_forward_threshold=int(qcard_settings.get("parse_command_forward_threshold", 1500)),
            )

        if settings.debug_echo_max_chars < 200:
            settings.debug_echo_max_chars = 200
        if settings.parse_command_forward_threshold < 200:
            settings.parse_command_forward_threshold = 200
        return settings
