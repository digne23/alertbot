import re


class BaseParser:
    """Base interface for provider-specific email parsers."""

    provider_name = "Generic"
    sender_domains: list[str] = []

    @classmethod
    def matches(cls, sender: str) -> bool:
        sender = (sender or "").lower()
        return any(domain in sender for domain in cls.sender_domains)

    @classmethod
    def parse(cls, sender: str, subject: str, body: str) -> dict:
        raise NotImplementedError

    @staticmethod
    def find_first(patterns: list[str], text: str, default: str = "Unknown") -> str:
        text = text or ""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return default
