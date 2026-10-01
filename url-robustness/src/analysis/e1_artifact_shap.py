"""Task B5 — E1: phân tích artifact bằng SHAP (owner: Dũng). Trả lời RQ3 và H1.

Làm 3 việc, giữ cố định model = Random Forest trên F1:
  1) So sánh chia NGẪU NHIÊN vs chia THEO registered domain (kiểm chứng rò rỉ domain, H1).
  2) SHAP feature importance của RF (chia theo domain).
  3) Bỏ dần các feature quan trọng nhất, đo lại Recall@FPR1% / F1 (tìm feature "artifact").
Tùy chọn --probe-format-flags: thêm has_https/has_www để xem model có ăn gian bằng định dạng nguồn.

Chạy:
    python -m src.analysis.e1_artifact_shap --data-dir data/processed --report-dir reports
Kết quả trung thực: nếu KHÔNG thấy artifact thì vẫn ghi nhận đúng như vậy.
"""
from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import tldextract
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from src.features.f1_lexical import build_f1_matrix
from src.models.quick_metrics import evaluate, pick_threshold_at_fpr

_EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)  # offline: dùng snapshot đóng gói sẵn


def registered_domain(url: str) -> str:
    u = url if "://" in url else "http://" + url
    e = _EXTRACT(u)
    # tldextract >=5.3: top_domain_under_public_suffix; bản cũ hơn: registered_domain
    dom = getattr(e, "top_domain_under_public_suffix", None) or getattr(e, "registered_domain", "")
    return dom or e.domain or u


def _rf(seed):
    return RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample",
                                  n_jobs=-1, random_state=seed)


def fit_eval(Xtr, ytr, Xva, yva, Xte, yte, seed):
    """Train RF, chọn ngưỡng trên val (FPR≈1%), đánh giá trên test."""
    m = _rf(seed).fit(Xtr, ytr)
    thr = pick_threshold_at_fpr(yva, m.predict_proba(Xva)[:, 1], 0.01)
    r = evaluate(yte, m.predict_proba(Xte)[:, 1], thr)
    return m, r


def split_random(df, seed):
    tr, rest = train_test_split(df, test_size=0.30, stratify=df["label"], random_state=seed)
    va, te = train_test_split(rest, test_size=0.50, stratify=rest["label"], random_state=seed)
    return tr, va, te


def split_domain(df, seed):
    """70/15/15 theo registered domain (mỗi domain chỉ ở 1 tập)."""
    g = df["domain"].values
    gss = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=seed)
    tr_idx, rest_idx = next(gss.split(df, groups=g))
    rest = df.iloc[rest_idx]
    gss2 = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=seed)
    va_i, te_i = next(gss2.split(rest, groups=rest["domain"].values))
    return df.iloc[tr_idx], rest.iloc[va_i], rest.iloc[te_i]


def shap_importance(model, X: pd.DataFrame, max_rows=2000, seed=0):
    Xs = X.sample(min(max_rows, len(X)), random_state=seed)
    sv = shap.TreeExplainer(model).shap_values(Xs)
    if isinstance(sv, list):
        sv = sv[1]
    elif getattr(sv, "ndim", 2) == 3:
        sv = sv[:, :, 1]
    imp = pd.Series(np.abs(sv).mean(axis=0), index=X.columns).sort_values(ascending=False)
    return imp, sv, Xs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/processed")
    ap.add_argument("--report-dir", default="reports")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--top-k", type=int, default=5, help="số feature top bị bỏ dần")
    ap.add_argument("--probe-format-flags", action="store_true",
                    help="thêm has_https/has_www để dò artifact định dạng")
    args = ap.parse_args(argv)
    os.makedirs(args.report_dir, exist_ok=True)

    # gộp toàn bộ nguồn A đã chia sẵn rồi CHIA LẠI 2 cách để so sánh
    parts = [pd.read_csv(os.path.join(args.data_dir, f)) for f in ("train.csv", "val.csv", "test_A.csv")]
    df = pd.concat(parts, ignore_index=True)
    if "orig_class" in df.columns:
        df = df[~df["orig_class"].astype(str).str.lower().isin({"defacement", "spam"})]
    df = df.drop_duplicates(subset="url").reset_index(drop=True)
    df["domain"] = df["url"].map(registered_domain)
    print(f"Nguồn A gộp: {len(df)} URL, {df['domain'].nunique()} registered domain")

    flags = args.probe_format_flags
    X_all = build_f1_matrix(df["url"], with_format_flags=flags)
    y_all = df["label"].values

    # ---------- (1) chia ngẫu nhiên vs chia theo domain ----------
    rows = []
    models = {}
    for scheme, fn in (("random_split", split_random), ("domain_split", split_domain)):
        tr, va, te = fn(df, args.seed)
        m, r = fit_eval(X_all.loc[tr.index], tr["label"], X_all.loc[va.index], va["label"],
                        X_all.loc[te.index], te["label"], args.seed)
        r.update(scheme=scheme, n_train=len(tr), n_test=len(te),
                 domain_overlap_train_test=len(set(tr["domain"]) & set(te["domain"])))
        rows.append(r)
        models[scheme] = (m, tr, va, te)
    cmp_df = pd.DataFrame(rows)[["scheme", "recall", "precision", "f1", "fpr", "pr_auc",
                                 "domain_overlap_train_test", "n_train", "n_test"]]
    cmp_df.to_csv(os.path.join(args.report_dir, "e1_random_vs_domain.csv"), index=False)
    print("\n(1) Chia ngẫu nhiên vs chia domain (H1 — rò rỉ domain):")
    print(cmp_df.round(4).to_string(index=False))
    gap = cmp_df.set_index("scheme").loc["random_split", "f1"] - cmp_df.set_index("scheme").loc["domain_split", "f1"]
    print(f"   -> chênh F1 (random - domain) = {gap:+.4f}. "
          f"{'Có dấu hiệu rò rỉ domain.' if gap > 0.01 else 'Chưa thấy rò rỉ rõ rệt — ghi nhận trung thực.'}")

    # ---------- (2) SHAP trên chia theo domain ----------
    m, tr, va, te = models["domain_split"]
    imp, sv, Xs = shap_importance(m, X_all.loc[te.index], seed=args.seed)
    imp.to_csv(os.path.join(args.report_dir, "e1_shap_importance.csv"), header=["mean_abs_shap"])
    print("\n(2) SHAP — top feature (chia theo domain):")
    print(imp.head(10).round(4).to_string())
    plt.figure(figsize=(7, 5))
    shap.summary_plot(sv, Xs, show=False, plot_size=None)
    plt.tight_layout()
    plt.savefig(os.path.join(args.report_dir, "e1_shap_summary.png"), dpi=150)
    plt.close()

    # ---------- (3) bỏ dần feature quan trọng nhất ----------
    order = list(imp.index)
    abl = []
    for k in range(0, min(args.top_k, len(order) - 1) + 1):
        keep = [c for c in X_all.columns if c not in order[:k]]
        _, r = fit_eval(X_all.loc[tr.index, keep], tr["label"], X_all.loc[va.index, keep], va["label"],
                        X_all.loc[te.index, keep], te["label"], args.seed)
        abl.append({"n_removed": k, "removed": ",".join(order[:k]) or "-",
                    "recall": r["recall"], "f1": r["f1"], "fpr": r["fpr"], "pr_auc": r["pr_auc"]})
    abl_df = pd.DataFrame(abl)
    abl_df.to_csv(os.path.join(args.report_dir, "e1_ablation.csv"), index=False)
    print("\n(3) Bỏ dần feature quan trọng nhất (chia theo domain):")
    print(abl_df.round(4).to_string(index=False))
    plt.figure(figsize=(6, 4))
    plt.plot(abl_df["n_removed"], abl_df["f1"], marker="o", label="F1")
    plt.plot(abl_df["n_removed"], abl_df["recall"], marker="s", label="Recall@FPR1%")
    plt.xlabel("số feature quan trọng nhất đã bỏ"); plt.ylabel("điểm"); plt.legend(); plt.grid(alpha=.3)
    plt.tight_layout(); plt.savefig(os.path.join(args.report_dir, "e1_ablation.png"), dpi=150); plt.close()

    # ---------- gợi ý artifact ----------
    fmt = [c for c in imp.index[:5] if c in ("has_https", "has_www")]
    drop_first = abl_df.loc[1, "f1"] - abl_df.loc[0, "f1"] if len(abl_df) > 1 else 0
    print("\nKết luận sơ bộ (cần người đọc và xác nhận, không tự kết luận thay bạn):")
    print(f" - Feature định dạng nằm trong top-5 SHAP: {fmt or 'không'}")
    print(f" - Bỏ feature #1 ({order[0]}) làm F1 đổi {drop_first:+.4f}")
    print(" - Nếu top feature là 'has_https'/'has_www' hoặc F1 sụp mạnh khi bỏ 1 feature định dạng "
          "=> nghi artifact nguồn; nếu không, ghi nhận 'chưa thấy artifact' (vẫn là kết quả hợp lệ).")


if __name__ == "__main__":
    main()
