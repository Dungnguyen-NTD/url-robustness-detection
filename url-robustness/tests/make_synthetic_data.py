"""Dữ liệu GIẢ chỉ để kiểm tra code chạy end-to-end khi chưa có dữ liệu thật của Phúc.

⚠ KHÔNG BAO GIỜ dùng số liệu từ dữ liệu này trong báo cáo.
Chia theo domain giống hệt quy tắc A5: mỗi domain chỉ nằm ở 1 tập.

    python -m tests.make_synthetic_data --out data/processed_synth
"""
from __future__ import annotations

import argparse
import os
import random

import pandas as pd

WORDS = ["shop", "news", "blog", "mail", "cloud", "game", "travel", "food", "music", "photo",
         "tech", "health", "book", "sport", "movie", "learn", "market", "home", "art", "code"]
TLDS = ["com", "net", "org", "io", "info", "co.uk"]
BAIT = ["login", "verify", "secure", "account", "update", "signin", "paypal", "bank", "confirm"]


def _rand_word(rng): return rng.choice(WORDS) + rng.choice(WORDS)


def make_domain(rng, malicious: bool) -> str:
    if malicious:
        parts = [_rand_word(rng), rng.choice(BAIT)] if rng.random() < 0.7 else [_rand_word(rng)]
        d = "-".join(parts) + (str(rng.randint(1, 999)) if rng.random() < 0.5 else "")
        sub = "" if rng.random() < 0.5 else rng.choice(BAIT) + "." + rng.choice(WORDS) + "."
    else:
        d = _rand_word(rng)
        sub = "www." if rng.random() < 0.4 else ""
    return f"{sub}{d}.{rng.choice(TLDS)}"


def make_urls(rng, domain: str, malicious: bool, k: int):
    urls = []
    for _ in range(k):
        segs = [rng.choice(WORDS + (BAIT if malicious and rng.random() < 0.6 else []))
                for _ in range(rng.randint(0, 4))]
        path = "/" + "/".join(segs)
        if rng.random() < (0.5 if malicious else 0.2):
            path += f"?id={rng.randint(1000, 999999)}&ref={rng.choice(WORDS)}"
        urls.append(domain + path)
    return urls


def build(n_domains: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for i in range(n_domains):
        mal = rng.random() < 0.3          # lệch lớp 70/30 để thử xử lý imbalance
        dom = make_domain(rng, mal)   # trùng domain giữa các vòng lặp là vô hại: chia theo domain xử lý
        for u in make_urls(rng, dom, mal, rng.randint(3, 8)):
            rows.append({"url": u, "label": int(mal), "domain": dom})
    return pd.DataFrame(rows)


def split_by_domain(df: pd.DataFrame, seed: int, frac=(0.7, 0.15, 0.15)):
    doms = sorted(df["domain"].unique())
    random.Random(seed).shuffle(doms)
    n = len(doms)
    a, b = int(n * frac[0]), int(n * (frac[0] + frac[1]))
    sets = {"train": set(doms[:a]), "val": set(doms[a:b]), "test_A": set(doms[b:])}
    return {k: df[df["domain"].isin(v)].drop(columns="domain").reset_index(drop=True)
            for k, v in sets.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/processed_synth")
    ap.add_argument("--n-domains", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    df = build(args.n_domains, args.seed)
    df = df.drop_duplicates(subset="url")
    parts = split_by_domain(df, args.seed)
    for k, v in parts.items():
        v.to_csv(os.path.join(args.out, f"{k}.csv"), index=False)
        print(k, len(v), "malicious%=", round(v.label.mean() * 100, 1))
    # 'nguồn B' giả với seed khác để thử luồng test khác nguồn
    b = build(400, args.seed + 99).drop(columns="domain").drop_duplicates(subset="url")
    b.to_csv(os.path.join(args.out, "test_B.csv"), index=False)
    print("test_B", len(b))


if __name__ == "__main__":
    main()
