"""图件共用数据读取。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "05_中间数据"
T = ROOT / "06_结果" / "tables"

P = pd.read_parquet(O / "panel_daily.parquet")
SC = pd.read_parquet(O / "stablecoin_daily.parquet")
TIC = pd.read_parquet(O / "tic_country_monthly.parquet")
TT = pd.read_csv(O / "tether_reserves_q.csv", parse_dates=["report_date"])
CC = pd.read_csv(O / "circle_reserves.csv", parse_dates=["report_date"])
LP = pd.read_csv(T / "local_projections.csv")
EVW = pd.read_csv(T / "event_study_window.csv", parse_dates=["date"])
EVS = pd.read_csv(T / "event_study_summary.csv")
EVP = pd.read_csv(T / "event_study_path.csv")
ML = pd.read_csv(T / "ml_counterfactual.csv", index_col=0, parse_dates=True)
MLI = pd.read_csv(T / "ml_importance.csv", index_col=0).iloc[:, 0]
OWN = pd.read_csv(T / "bill_ownership_monthly.csv", index_col=0, parse_dates=True)
FR = pd.read_csv(T / "foreign_holders_regressions.csv")
CR = pd.read_csv(T / "foreign_country_slopes.csv")
WK = pd.read_csv(T / "weekly_panel.csv", index_col=0, parse_dates=True)
EVENTS = pd.read_csv(ROOT / "04_原始数据/events/genius_events.csv", parse_dates=["date"])
RES = json.load(open(ROOT / "06_结果" / "results.json"))

SIGNED = pd.Timestamp("2025-07-18")
EV_IDS = ["E02", "E03", "E04", "E05", "E07", "E08", "E09", "E10", "E11", "E13"]
EV_SHORT = {"E02": "Senate", "E03": "House", "E04": "Signed", "E05": "Tsy ANPRM", "E07": "OCC NPRM", "E08": "OCC in FR",
            "E09": "Tsy state NPRM", "E10": "Tsy/OFAC AML", "E11": "FDIC NPRM", "E13": "Tsy issuance NPRM"}
EV_DATE = {r.event_id: r.date for r in EVENTS.itertuples()}


def bn(x):
    return x / 1e9
