from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

_FM_RE = re.compile(r"\A---\r?\n(?:(.*?)\r?\n)?---\r?\n?", re.DOTALL)
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"


def _without_timestamp_resolver(base):
    cls = type(base.__name__ + "NoTs", (base,), {})
    cls.yaml_implicit_resolvers = {
        key: [(tag, regexp) for (tag, regexp) in resolvers if tag != _TIMESTAMP_TAG]
        for key, resolvers in base.yaml_implicit_resolvers.items()
    }
    return cls


_Loader = _without_timestamp_resolver(yaml.SafeLoader)
_Dumper = _without_timestamp_resolver(yaml.SafeDumper)


@dataclass
class Document:
    meta: dict
    body: str


def parse(text: str) -> Document:
    m = _FM_RE.match(text)
    if not m:
        return Document({}, text)
    meta = yaml.load(m.group(1) or "", Loader=_Loader) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter is not a mapping")
    return Document(meta, text[m.end():])


def dump(doc: Document) -> str:
    if not doc.meta:
        return doc.body
    meta = yaml.dump(
        doc.meta, Dumper=_Dumper, sort_keys=False, allow_unicode=True, default_flow_style=False,
        width=float("inf"),
    ).rstrip("\n")
    return f"---\n{meta}\n---\n{doc.body}"


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read(path: Path) -> Document:
    return parse(path.read_text(encoding="utf-8"))


def write(path: Path, doc: Document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(doc), encoding="utf-8")
