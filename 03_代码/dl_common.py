"""下载安全层：强制直连、重试、哈希账本、容量守卫。

所有正式数据下载只经本模块；requests.Session 设置 trust_env=False，
不读取 HTTP/HTTPS/SOCKS 或系统代理，直连失败即停止，绝不回退代理。
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "04_原始数据"
LEDGER = ROOT / "07_文献与日志" / "download_ledger.jsonl"
CAP_BYTES = 20 * 1024**3  # 项目目录硬上限 20 GiB
STOP_BYTES = 16 * 1024**3  # 16 GiB 停止新增下载

UA = "Mozilla/5.0 (research data collection; stablecoin-shadow-treasury project)"


def session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False  # 忽略一切代理环境变量
    s.proxies = {}
    s.headers.update({"User-Agent": UA})
    return s


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def capacity_guard() -> None:
    used = dir_size(ROOT)
    if used >= STOP_BYTES:
        raise RuntimeError(f"容量守卫：项目已用 {used/1024**3:.2f} GiB，达到停止线")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log(record: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    record["ts_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def fetch(url: str, dest: Path, *, params: dict | None = None, tries: int = 4,
          timeout: int = 120, source: str = "", sess: requests.Session | None = None,
          must_contain: bytes | None = None) -> Path:
    """下载到 dest 并记账。must_contain 用于识别"200 但内容是错误页"的情形。"""
    capacity_guard()
    dest.parent.mkdir(parents=True, exist_ok=True)
    s = sess or session()
    last = None
    for i in range(1, tries + 1):
        try:
            r = s.get(url, params=params, timeout=(15, timeout))
            if r.status_code == 200 and r.content and (must_contain is None or must_contain in r.content[:4000]):
                dest.write_bytes(r.content)
                log({"source": source, "url": r.url, "file": str(dest.relative_to(ROOT)),
                     "bytes": len(r.content), "sha256": sha256(dest), "status": 200})
                return dest
            last = f"HTTP {r.status_code}, {len(r.content)}B"
        except requests.RequestException as e:  # 直连失败即重试，不回退代理
            last = repr(e)
        time.sleep(1.5 * i)
    log({"source": source, "url": url, "file": str(dest.relative_to(ROOT)), "status": "FAILED", "error": last})
    raise RuntimeError(f"下载失败 {url}: {last}")
