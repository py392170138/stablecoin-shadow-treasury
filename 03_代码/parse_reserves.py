"""把 Tether（季度）与 Circle（月度）储备报告 PDF 解析为结构化面板。

规则解析（正则），不调用大模型。统一文本规范化：字母与标点之间的空白全部删除，
数字边界处的空白保留为单个空格，因此所有标签都用"无空格紧凑形式"书写，对不同年份的
PDF 抽取差异（有无词间空格）不敏感。金额单位：美元。解析失败写入 parse_failures.csv。
"""
from __future__ import annotations

import re
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "04_原始数据" / "issuer_reports"
OUT = ROOT / "05_中间数据"
OUT.mkdir(exist_ok=True)

_LET = r"[A-Za-z.&,;:'’\-–/ﬁﬂ]"
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
AMT = r"\(?\$?\s*([0-9]{1,3}(?:,[0-9]{3}){2,})\)?"


def text_of(pdf: Path, maxpages: int = 30) -> str:
    r = PdfReader(str(pdf))
    t = "\n".join((p.extract_text() or "") for p in r.pages[:maxpages])
    t = t.replace("ﬁ", "fi").replace("ﬀ", "ff")
    t = re.sub(rf"(?<={_LET})\s+(?={_LET})", "", t)
    return re.sub(r"\s+", " ", t)


def num(s: str) -> float:
    return float(s.replace(",", ""))


def grab(txt: str, label: str, window: int = 70, nth: int = 0, neg_ok: bool = True):
    """紧凑标签之后第一个带至少两组千分位的金额；括号视为负数。"""
    hits = [m.end() for m in re.finditer(label, txt, flags=re.I)]
    if len(hits) <= nth:
        return None
    seg = txt[hits[nth]: hits[nth] + window]
    m = re.search(AMT, seg)
    if not m:
        return None
    v = num(m.group(1))
    return -v if (neg_ok and m.group(0).strip().startswith("(")) else v


def first(txt, labels, **kw):
    for lb in labels:
        v = grab(txt, lb, **kw)
        if v is not None:
            return v
    return None


# ---------------------------------------------------------------- Tether
def parse_tether():
    rows, fails = [], []
    for pdf in sorted((RAW / "tether").glob("*.pdf")):
        d = re.search(r"(\d{4}-\d{2}-\d{2})", pdf.name).group(1)
        try:
            t = text_of(pdf)
            rec = {"report_date": d, "file": pdf.name}
            rec["us_tbills"] = first(t, [r"U\.S\.TreasuryBills\d{0,2} ", r"U\.S\.TreasuryBills", r"(?<!Non-)TreasuryBills\d{0,2} "])
            rec["on_rrp"] = first(t, [r"OvernightReverse-?RepurchaseAgreements\d{0,2} "])
            rec["term_rrp"] = first(t, [r"TermReverse-?RepurchaseAgreements\d{0,2} "])
            rec["reverse_repo_other"] = first(t, [r"ReverseRepoNotes\d{0,2} "]) if rec["on_rrp"] is None else None
            rec["cash_bank"] = first(t, [r"Cash&BankDeposits\d{0,2} "])
            rec["commercial_paper"] = first(t, [r"CommercialPaperandCertificatesofDeposit\d{0,2} ", r"CommercialPaper&CertificatesofDeposit\d{0,2} "])
            rec["money_market_funds"] = first(t, [r"MoneyMarketFunds\d{0,2} "])
            rec["precious_metals"] = first(t, [r"PreciousMetals\d{0,2} "])
            rec["bitcoin"] = first(t, [r"Bitcoins?\d{0,2} "])
            rec["secured_loans"] = first(t, [r"SecuredLoans(?:\(nonetoaffiliatedentities\))?\d{0,2} "])
            rec["total_assets"] = first(t, [r"TotalAssets\(1\+2[^)]*\)", r"Total\(1\+2[^)]*\)", r"consolidatedtotalassetsamountto(?:atleast)?(?:US)?\$?\s?"], window=60)
            rec["total_liabilities"] = first(t, [r"consolidatedtotalliabilitiesamounttoUS?\$?\s?"], window=60)
            rows.append(rec)
        except Exception as e:  # noqa: BLE001
            fails.append((pdf.name, repr(e)))
    return pd.DataFrame(rows).sort_values("report_date"), fails


# ---------------------------------------------------------------- Circle
def parse_circle():
    rows, fails = [], []
    for pdf in sorted((RAW / "circle_usdc").rglob("*.pdf")):
        try:
            t = text_of(pdf)
            marks = []
            for m in re.finditer(rf"CIRCLERESERVEFUNDASSETSASOF ?({MONTHS}) ?(\d{{1,2}}) ?,? ?(\d{{4}})", t, flags=re.I):
                marks.append((m.start(), datetime.strptime(f"{m.group(1).title()} {m.group(2)} {m.group(3)}", "%B %d %Y").date()))
            seen = set()
            for i, (pos, dt) in enumerate(marks):
                if dt in seen:
                    continue
                end = marks[i + 1][0] if i + 1 < len(marks) else len(t)
                seg = t[pos:end]
                rec = {"report_date": dt.isoformat(), "file": pdf.name}
                rec["treasuries"] = grab(seg, r"TOTALU\.S\.TREASURY(?:SECURITIES|BILLS)")
                rec["repo"] = grab(seg, r"U\.S\.TreasuryRepurchaseAgreements\d? ")
                rec["cash_fund"] = grab(seg, r"CashheldinCircleReserveFund")
                rec["fund_total"] = grab(seg, r"TOTALCIRCLERESERVEFUNDASSETS\d? ")
                rec["cash_banks"] = grab(seg, r"Cashheldat(?:U\.S\.)?regulatedfinancialinstitutions\d? ")
                rec["total_reserve"] = grab(seg, r"TOTALUSDCRESERVEASSETS(?:ASOF[A-Z]+\d{1,2},?\d{4})? ")
                if rec["total_reserve"] is None:
                    rec["total_reserve"] = grab(seg, r"TOTALUSDCRESERVEASSETS")
                if rec["treasuries"] is None and rec["fund_total"] is not None and rec["repo"] is not None:
                    rec["treasuries"] = 0.0  # 该日基金无国库券持仓（全部为回购与现金）
                if rec["treasuries"] is not None or rec["repo"] is not None:
                    rows.append(rec)
                    seen.add(dt)
            if not seen:
                fails.append((pdf.name, "no Circle Reserve Fund block (pre-2023 format has no composition table)"))
        except Exception as e:  # noqa: BLE001
            fails.append((pdf.name, repr(e)))
    return pd.DataFrame(rows).drop_duplicates("report_date").sort_values("report_date"), fails


if __name__ == "__main__":
    tdf, tf = parse_tether()
    cdf, cf = parse_circle()
    tdf.to_csv(OUT / "tether_reserves_q.csv", index=False)
    cdf.to_csv(OUT / "circle_reserves.csv", index=False)
    pd.DataFrame(tf + cf, columns=["file", "error"]).to_csv(OUT / "parse_failures.csv", index=False)
    print("tether", tdf.shape, "circle", cdf.shape, "failures", len(tf), len(cf))
    pd.set_option("display.width", 250)
    print((tdf.set_index("report_date")[["total_assets", "us_tbills", "on_rrp", "term_rrp", "reverse_repo_other", "cash_bank", "commercial_paper", "money_market_funds"]] / 1e9).round(2).to_string())
    print((cdf.set_index("report_date")[["treasuries", "repo", "cash_fund", "cash_banks", "total_reserve"]] / 1e9).round(2).to_string())
