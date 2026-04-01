def pick_first_str_by_paths(data: dict, paths: list[tuple[str, ...]]) -> str:
    """Pick the first non-empty string by nested key paths."""
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


def strip_prompt_prefix(prompt: str) -> str:
    """Strip known card prompt prefixes."""
    text = prompt.strip()
    for prefix in ("[QQ小程序]", "[小程序]", "[分享]", "[链接]", "[网页]"):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def clean_music_url(url: str) -> str:
    """Normalize music links while preserving usability."""
    if not url:
        return ""

    if "y.qq.com" in url or "i.y.qq.com" in url:
        if "?" in url:
            query_str = url.split("?", 1)[1]
            for param in query_str.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key.lower() == "songmid" and value:
                        return f"https://y.qq.com/n/ryqq_v2/songDetail/{value}"
        return url

    if "music.163.com" in url:
        if "?" not in url:
            return url
        parts = url.split("?", 1)
        base_url = parts[0]
        query_str = parts[1] if len(parts) > 1 else ""
        if "/song" in base_url:
            for param in query_str.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    if key.lower() == "id" and value:
                        return f"{base_url}?id={value}"
        return base_url

    return url


def truncate_text(text: str, max_len: int, suffix: str = "...") -> str:
    """Truncate text to max_len with suffix."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + suffix


def append_summary(existing: str | None, summary: str) -> str:
    """Append summary to existing text with blank line separator."""
    if existing:
        return f"{existing}\n\n{summary}"
    return summary
