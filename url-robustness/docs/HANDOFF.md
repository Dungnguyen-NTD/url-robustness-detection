# Hợp đồng bàn giao giữa các phần (Dũng = Phần B)

Nguyên tắc: **mỗi người sở hữu 1 phần; bàn giao đúng format dưới đây. Lỗi nằm ở phía NHẬN nếu
người giao đã đúng format, ở phía GIAO nếu sai format.** Khi bàn giao xong, nhắn trực tiếp cho người nhận.

---
## 1. Phúc (A5) → Dũng (B2, B3, B4): dữ liệu đã chia

Thư mục `data/processed/`, 3 file CSV **UTF-8, có header**:

| File | Nội dung |
|---|---|
| `train.csv` | 70% nguồn A (chia theo registered domain) |
| `val.csv` | 15% — chỉ dùng chọn ngưỡng/siêu tham số |
| `test_A.csv` | 15% test cùng nguồn |

Cột bắt buộc: `url` (đã chuẩn hóa ở A4), `label` (**0 = benign, 1 = malicious**).
Cột tùy chọn: `orig_class` (benign/phishing/malware/defacement/spam) — nếu có, code của Dũng tự loại
defacement/spam khỏi bài toán chính; `source`.

Checklist trước khi giao (Phúc tự chạy, không chờ ai kiểm hộ):
- [ ] giao của tập registered domain(train) và domain(test/val) **rỗng**
- [ ] không URL nào trùng nguyên văn giữa các tập
- [ ] `label` chỉ gồm 0/1, không NaN
- [ ] log số URL bị loại mỗi bước đã lưu (cần cho báo cáo)

Nếu `train_baselines.py` báo **F1 test_A > 0.995** → nghi rò rỉ domain → quay lại A5 trước tiên.

---
## 2. Dũng (B2, B3) → Phúc (A6): code trích feature cho nguồn B/C

Phúc **import lại**, không tự viết lại:

```python
from src.features.f1_lexical import build_f1_matrix
from src.features.f2_ngram import F2Vectorizer

vec = F2Vectorizer.load("models/f2_vectorizer.joblib")   # ĐÃ fit trên train A — TUYỆT ĐỐI không fit lại
XB_f1 = build_f1_matrix(source_b["url"])
XB_f2 = vec.transform(source_b["url"])
```
Số cột của B/C phải khớp A (`XB_f1.shape[1] == 15`, F2 khớp `vec.n_features`).
Cách đơn giản nhất: Phúc chỉ cần giao `test_B.csv`, `test_C.csv` (cột `url,label`) —
`URLDetector.score()` tự trích feature, không cần lưu ma trận.

---
## 3. Dũng (B4) → Nam (C2, C3, C4): giao diện tấn công HỘP ĐEN

Model đã train ở `models/*.joblib` (5 model: `lr_f1, rf_f1, xgb_f1, lr_f2, svm_f2`), threshold đã đặt
(chọn trên validation A, FPR≈1%). **Không train lại, không đổi threshold.**

```python
from src.models.detector import URLDetector
det = URLDetector.load("models/rf_f1.joblib")
scores = det.score(["http://example.com/a", "..."])   # np.ndarray [0,1], 1 = độc hại
det.threshold                                          # ngưỡng cố định
```
Ràng buộc threat model (mức 2 — hộp đen): tấn công tham lam **chỉ được gọi `det.score(...)`**.
Không được gọi `det.featurize`, `det.model`, đọc feature importance hay trọng số.
Mỗi lần gọi `score` = 1 query (đếm số query ở phía Nam).

Điểm SVM là `sigmoid(decision_function)` — đơn điệu nên thứ tự điểm giống hệt, dùng như xác suất tương đối.

---
## 4. Dũng (B4) → Hiếu (D1 metric, D3–D5 phòng thủ)

**Cắm D1 (chuẩn hóa đầu vào)** — không cần sửa code của Dũng:
```python
det = URLDetector.load("models/rf_f1.joblib")
det.preprocess = normalize_d1        # hàm str -> str của Hiếu (punycode, homoglyph, tracking param)
```
Lưu ý: khi cắm D1 mà **train lại**, tạo detector mới bằng `URLDetector(name, kind, model, preprocess=normalize_d1)`
và huấn luyện trên feature của URL đã qua `normalize_d1`. `det.threshold` phải **chọn lại trên validation A**
(model mới ⇒ phân phối điểm mới), rồi giữ cố định.

**Thêm feature D2 (cấu trúc domain):** viết hàm trích feature mới trả `DataFrame`, tạo detector mới
(mở rộng `feature_kind` trong `detector.py` hoặc bọc `URLDetector` — báo Dũng để thống nhất, đừng sửa im lặng).

**metric_common (D1):** `src/models/quick_metrics.py` chỉ là bản tạm của Dũng. Khi `src/eval/metric_common.py`
xong, mọi số liệu trong báo cáo phải chạy lại bằng bản của Hiếu. Hàm cần có tối thiểu:
`pick_threshold_at_fpr(y, s, 0.01)` và `evaluate(y, s, thr)` trả recall/precision/f1/fpr/pr_auc/roc_auc.

---
## 5. Ai chịu trách nhiệm khi lỗi

| Triệu chứng | Kiểm tra trước ở |
|---|---|
| F1 test_A ≈ 100% | A5 (Phúc): rò rỉ domain |
| Nguồn B/C báo thiếu/lệch cột | A6 (Phúc) → nếu A6 đúng thì B3 (Dũng) |
| Điểm `det.score` ngoài [0,1] / lỗi shape | B4 (Dũng) |
| Tấn công "né" quá dễ mà URL sau biến đổi vô nghĩa | C1 (Nam): validate_transform |
| Model D1+D2+D3 bị né dễ | D5 (Hiếu) — không phải lỗi của Nam |
