"""Smoke test phần B (Dũng). Chạy:  pytest -q"""
import numpy as np
import pandas as pd
import pytest

from src.features.f1_lexical import (F1_FEATURE_NAMES, build_f1_matrix, extract_f1,
                                     is_ip_host, shannon_entropy)
from src.features.f2_ngram import F2Vectorizer, split_host_path
from src.models.detector import URLDetector
from src.models.quick_metrics import evaluate, pick_threshold_at_fpr

BENIGN = ["https://www.wikipedia.org/wiki/Python", "github.com/torvalds/linux", "http://news.bbc.co.uk/sport/tennis"]
PHISH = ["http://secure-login-paypal.verify-account.example.tk/webscr?cmd=login&id=99812",
         "http://192.168.10.5/bank/update/confirm/password.php"]


def test_f1_shape_and_no_nan():
    df = build_f1_matrix(BENIGN + PHISH)
    assert list(df.columns) == F1_FEATURE_NAMES
    assert df.shape == (5, len(F1_FEATURE_NAMES))
    assert not df.isna().any().any()
    assert (df >= 0).all().all()


def test_f1_sanity_phish_looks_more_suspicious():
    b = extract_f1(BENIGN[1]); p = extract_f1(PHISH[0])
    assert p["n_suspicious_kw"] > b["n_suspicious_kw"]
    assert p["n_hyphens"] > b["n_hyphens"]
    assert p["url_len"] > b["url_len"]


def test_f1_ip_detection_and_scheme_agnostic():
    assert extract_f1(PHISH[1])["has_ip"] == 1
    assert is_ip_host("3232235777") and not is_ip_host("example.com")
    # thiếu scheme vẫn parse ra cùng host_len
    assert extract_f1("github.com/x")["host_len"] == extract_f1("https://github.com/x")["host_len"]


def test_f1_format_flags_only_on_request():
    assert "has_https" not in extract_f1(BENIGN[0])
    f = extract_f1(BENIGN[0], with_format_flags=True)
    assert f["has_https"] == 1 and f["has_www"] == 1


def test_f1_handles_garbage():
    for u in ["", None, "not a url", "http://", "%%%%", "a" * 5000]:
        extract_f1(u)   # không được raise


def test_entropy():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") == pytest.approx(2.0)


def test_f2_requires_fit_and_columns_consistent():
    train = BENIGN * 5 + PHISH * 5
    v = F2Vectorizer(min_df=1)
    with pytest.raises(RuntimeError):
        v.transform(train)
    v.fit(train)
    a = v.transform(train); b = v.transform(["http://totally-new-host.org/abc"])
    assert a.shape[1] == b.shape[1]            # cột không đổi khi transform tập khác (không fit lại)
    h, p = split_host_path("http://Sub.Example.com/A/b?x=1")
    assert h == "sub.example.com" and p == "/a/b?x=1"


def _tiny_detector(kind="f1"):
    from sklearn.linear_model import LogisticRegression
    urls = BENIGN * 20 + PHISH * 20
    y = np.array([0] * (len(BENIGN) * 20) + [1] * (len(PHISH) * 20))
    if kind == "f1":
        m = LogisticRegression(max_iter=500).fit(build_f1_matrix(urls), y)
        return URLDetector("t", "f1", m, threshold=0.5)
    v = F2Vectorizer(min_df=1).fit(urls)
    m = LogisticRegression(max_iter=500).fit(v.transform(urls), y)
    return URLDetector("t", "f2", m, f2_vectorizer=v, threshold=0.5)


@pytest.mark.parametrize("kind", ["f1", "f2"])
def test_detector_api(kind, tmp_path):
    d = _tiny_detector(kind)
    s = d.score(BENIGN + PHISH)
    assert s.shape == (5,) and ((s >= 0) & (s <= 1)).all()
    assert d.predict(PHISH).tolist() == [1, 1]
    p = tmp_path / "d.joblib"; d.save(str(p))
    d2 = URLDetector.load(str(p))
    np.testing.assert_allclose(d2.score(PHISH), d.score(PHISH))


def test_detector_preprocess_hook_is_applied():
    d = _tiny_detector("f1")
    base = d.score(["http://x.com/a"])[0]
    d.preprocess = lambda u: "http://secure-login-paypal.verify-account.example.tk/webscr?cmd=login"
    assert d.score(["http://x.com/a"])[0] > base     # D1 của Hiếu cắm được qua hook


def test_detector_requires_threshold_for_predict():
    d = _tiny_detector("f1"); d.threshold = None
    with pytest.raises(RuntimeError):
        d.predict(BENIGN)


def test_threshold_respects_fpr():
    rng = np.random.default_rng(0)
    y = np.array([0] * 2000 + [1] * 2000)
    s = np.concatenate([rng.normal(0.3, 0.15, 2000), rng.normal(0.7, 0.15, 2000)])
    thr = pick_threshold_at_fpr(y, s, 0.01)
    r = evaluate(y, s, thr)
    assert r["fpr"] <= 0.0105
    assert r["recall"] > 0.5


def test_metrics_random_model_auc_half():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 5000); s = rng.random(5000)
    assert evaluate(y, s, 0.5)["roc_auc"] == pytest.approx(0.5, abs=0.03)
