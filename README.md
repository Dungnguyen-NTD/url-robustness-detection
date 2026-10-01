# Malicious URL Detection — Robustness dưới đổi nguồn & tấn công đối kháng

AIC211 · Đề tài 2 · Nhóm 4

**Câu hỏi nghiên cứu chính (RQ1):** với cùng một phishing/malware URL detector, hiệu năng giảm bao nhiêu khi
(a) test trên nguồn dữ liệu khác nguồn train và (b) URL bị biến đổi đối kháng hợp lệ; kỹ thuật phòng thủ nào
thu hẹp mức giảm đó với chi phí thấp nhất trên dữ liệu sạch?
Câu hỏi phụ: **RQ2** feature nào (lexical vs char n-gram) bền hơn; **RQ3** model ~100% trên ISCX-URL2016 dựa vào
feature nào và có phải artifact của nguồn thu thập không.

> An toàn: toàn bộ đề tài chỉ xử lý **chuỗi ký tự**. Không mở/crawl URL độc hại.

## Thành viên & phần phụ trách

| Phần | Người | Thư mục chính |
|---|---|---|
| A — Dữ liệu | Hồ Nguyên Phúc | `src/preprocess/`, `data/` |
| B — Feature & Model (leader) | Nguyễn Tấn Dũng | `src/features/`, `src/models/`, `src/analysis/` |
| C — Tấn công | Đỗ Hoài Nam | `src/attack/` |
| D — Phòng thủ & Đánh giá | Nguyễn Trung Hiếu | `src/defense/`, `src/eval/` |

Hợp đồng bàn giao giữa các phần: [`docs/HANDOFF.md`](docs/HANDOFF.md).
**Mỗi người commit code phần mình dưới đúng tên GitHub của mình** (bằng chứng đóng góp cá nhân theo yêu cầu môn).

## Cài đặt

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                              # 13 test phần B phải pass
```

## Cấu trúc

```
data/raw/            dữ liệu thô (KHÔNG commit — xem mục Dữ liệu)
data/processed/      train.csv, val.csv, test_A.csv, test_B.csv, test_C.csv (url,label)
models/              *.joblib (KHÔNG commit)
reports/             bảng/biểu đồ kết quả
src/features/        f1_lexical.py, f2_ngram.py            (B2, B3)
src/models/          detector.py, train_baselines.py       (B4)
src/analysis/        e1_artifact_shap.py                   (B5)
src/preprocess/  src/attack/  src/defense/  src/eval/      (A, C, D)
tests/               test tự động + sinh dữ liệu giả để chạy thử
docs/                HANDOFF.md, proposal_draft.md
```

## Chạy phần B

```bash
# 0) (chỉ để thử code khi chưa có dữ liệu thật) — dữ liệu GIẢ, không dùng số liệu này trong báo cáo
python -m tests.make_synthetic_data --out data/processed_synth

# 1) B4: train 5 model, chọn ngưỡng FPR≈1% trên val_A, đánh giá val/test_A/(B)
python -m src.models.train_baselines --data-dir data/processed --out-dir models \
       --report-dir reports --source-b data/processed/test_B.csv --seed 42

# 2) B5: E1 — chia ngẫu nhiên vs domain, SHAP, bỏ dần feature quan trọng
python -m src.analysis.e1_artifact_shap --data-dir data/processed --report-dir reports [--probe-format-flags]
```

## Quy tắc bắt buộc (tránh "kết quả tốt giả")

1. Chia theo **registered domain** (tldextract); F1 test ≈ 100% ⇒ nghi rò rỉ domain, kiểm tra A5 trước.
2. Ngưỡng chọn **một lần** trên validation nguồn A (FPR≈1%), giữ nguyên ở mọi nơi. Nguồn B/C chỉ để test.
3. Vectorizer F2 chỉ `fit` trên **train**. Không fit lại trên val/test/B/C.
4. Tấn công hộp đen chỉ gọi `detector.score()`; kiểm tra phòng thủ bằng tấn công **tham lam**, không chỉ biến đổi đã train.
5. Cố định seed (`--seed`), ghi hyperparameter (`reports/hyperparameters.json`). Chạy E3/E4 ≥ 3 seed.
6. Mất cân bằng lớp: ghi trong `reports/imbalance_note.txt` (sinh tự động bởi B4).

## Dữ liệu

| Nguồn | Vai trò | Ghi chú |
|---|---|---|
| A — ISCX-URL2016 | train/val/test cùng nguồn | defacement/spam chỉ dùng cho E1 |
| B — bộ phishing 2025 [6] / PhiUSIIL | test khác nguồn | PhiUSIIL chỉ lấy cột URL |
| C — OpenPhish/PhishTank gần đây + Tranco (benign có path thật) | test "hiện tại" | chỉ lưu chuỗi URL |

TODO (Phúc): điền link tải/ngày tải từng nguồn và số URL mỗi lớp vào bảng này.

## Khai báo sử dụng AI

TODO (Dũng, khi nộp): liệt kê công cụ AI đã dùng (Claude...) và phần nào được hỗ trợ; mỗi thành viên tự
xác nhận đã hiểu và chạy lại được phần code của mình.

## Tài liệu tham khảo

TODO (B7): [6], [8], [9] — đối chiếu số liệu với bản gốc trước khi nộp; trích nguồn ISCX-URL2016,
PhishTank, OpenPhish, Tranco, PhiUSIIL.
