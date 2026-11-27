from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


def normalize_text(value: str | None) -> str:
    value = value or ""
    return re.sub(r"\s+", " ", value).strip().lower()


def normalize_phone(value: str | None) -> str:
    value = value or ""
    digits = re.sub(r"\D+", "", value)
    return digits


def normalize_maps_url(value: str | None) -> str:
    if not value:
        return ""
    parts = urlsplit(value)
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def name_address_key(company_name: str | None, full_address: str | None) -> str:
    name = normalize_text(company_name)
    address = normalize_text(full_address)
    if not name or not address:
        return ""
    return f"{name}|{address}"


def merge_pipe_values(existing: str | None, new_value: str | None) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for raw in [existing or "", new_value or ""]:
        for part in raw.split("|"):
            value = part.strip()
            key = value.lower()
            if value and key not in seen:
                values.append(value)
                seen.add(key)
    return " | ".join(values)
