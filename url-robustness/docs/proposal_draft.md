# Proposal / Project Charter — bản nháp (Dũng)

> Điền theo template 3.1–3.13 của môn. Mục có `TODO` cần bổ sung trước khi nộp.
> Nguồn nội dung: tài liệu hướng dẫn hướng nghiên cứu Đề tài 2 + `AIC211_Project_Template_and_Rubric.docx`.

## 3.1 Tên đề tài
Malicious URL Detection: đánh giá độ bền của bộ phát hiện phishing/malware URL trước đổi nguồn dữ liệu và
biến đổi đối kháng, cùng ablation các lớp phòng thủ.

## 3.2 Thành viên, MSSV, vai trò
| Họ tên | MSSV | Vai trò |
|---|---|---|
| Nguyễn Tấn Dũng (leader) | TODO | Feature & Model; tổng hợp báo cáo, nộp bài |
| Hồ Nguyên Phúc | TODO | Dữ liệu |
| Đỗ Hoài Nam | TODO | Tấn công đối kháng |
| Nguyễn Trung Hiếu | TODO | Phòng thủ & Đánh giá |

## 3.3 Vấn đề an ninh mạng
Phishing/malware URL là vector tấn công phổ biến qua email và web. Detector dựa trên chuỗi URL chạy được ngay tại
trình duyệt/email gateway (không cần WHOIS hay tải trang), nhưng các nghiên cứu thường báo cáo độ chính xác ~100%
trên ISCX-URL2016 mà không kiểm tra (i) chuyển sang nguồn dữ liệu khác và (ii) kẻ tấn công chủ động biến đổi URL.

## 3.4 Mục tiêu
- Bảo mật: đo detector còn chặn được bao nhiêu URL độc khi chỉ chấp nhận chặn nhầm 1% URL lành (Recall@FPR=1%).
- Kỹ thuật: (1) đo gap đổi nguồn A→B, A→C; (2) đo mức giảm dưới tấn công có threat model (T1–T7, ngẫu nhiên và
  tham lam hộp đen); (3) đánh giá ablation phòng thủ D1 (chuẩn hóa), D2 (feature cấu trúc), D3 (huấn luyện đối kháng)
  kèm chi phí trên dữ liệu sạch.
- Trả lời RQ1–RQ3 và kiểm chứng giả thuyết H1–H3 (xem README).

## 3.5 Loại bài toán ML
Phân loại nhị phân có giám sát (benign vs malicious = phishing + malware), dữ liệu văn bản ngắn (chuỗi URL).

## 3.6 Dataset dự kiến
| Nguồn | Nội dung | Vai trò | Rủi ro dữ liệu |
|---|---|---|---|
| A — ISCX-URL2016 | benign, phishing, malware (+ defacement, spam cho E1) | train/val/test cùng nguồn | rò rỉ domain; artifact định dạng |
| B — bộ phishing URL 2025 [6] / PhiUSIIL (2024) | benign + phishing | test khác nguồn | benign có thể trùng danh sách với A |
| C — OpenPhish/PhishTank gần đây + Tranco | malicious "hiện tại" + benign có path thật | test "hiện tại" (drift) | ít URL; benign khác phân phối A |

Gán nhãn: theo nhãn có sẵn của dataset công khai / feed; chỉ lưu chuỗi URL, không truy cập. TODO: số URL mỗi lớp.

## 3.7 Baseline
Logistic Regression trên F1 (lexical handcrafted: độ dài, số dấu chấm/gạch/chữ số/ký tự đặc biệt, có IP,
từ khóa đáng ngờ, entropy) — dễ giải thích.

## 3.8 Model chính
Random Forest, XGBoost trên F1; Logistic Regression, Linear SVM trên F2 (char n-gram TF-IDF 3–5, host/path riêng).
"Model cải tiến" là detector bền hơn: D1+D2+D3 (không phải chỉ đổi thuật toán). Tùy chọn: char-CNN nhỏ (bonus so sánh DL).

## 3.9 Kế hoạch đánh giá
- Chia nguồn A 70/15/15 **theo registered domain** (tldextract); loại URL trùng; nguồn B/C chỉ để test.
- Ngưỡng chọn trên validation A để FPR≈1%, giữ nguyên ở mọi nơi.
- Metric chính: Recall@FPR=1%, attack success rate, gap đổi nguồn; phụ: Precision, F1, confusion matrix,
  ROC-AUC, PR-AUC, thời gian dự đoán/URL, số truy vấn của tấn công tham lam.
- So sánh với baseline; xử lý mất cân bằng lớp bằng `class_weight`/`scale_pos_weight`, không resample val/test.
- E1 artifact (SHAP) → E2 đổi nguồn → E3 tấn công → E4 phòng thủ; E3/E4 chạy ≥ 3 seed (mean ± std).

## 3.10 Công cụ & môi trường
Python 3.10+, scikit-learn, xgboost, shap, tldextract, idna, rapidfuzz, pandas/numpy/scipy, matplotlib, Jupyter,
Git/GitHub. Chạy được trên CPU (không cần GPU). Repo: TODO link.

## 3.11 Kế hoạch theo tuần
Xem sheet `Weekly_Plan_De_Xuat` trong file Excel kế hoạch (bản dịch 10 tuần từ sơ đồ phụ thuộc):
T1 thu thập + chuẩn hóa + chia domain (A), viết bộ biến đổi (C), metric chung (D) · T2 trích F1/F2 + **baseline (mốc)** ·
T3 tấn công + đánh giá đổi nguồn + SHAP · T4 phòng thủ D1/D2, phân tích FP nguồn C · T5 D3 + tấn công lại + demo ·
T6 E4 + 3 seed · T7 viết phần Defense/Security/Deployment/Drift/Privacy · T8 hoàn thiện bản nháp từng phần ·
T9 ráp báo cáo · T10 slide, Q&A, nộp.

## 3.12 Rủi ro & giảm thiểu
| Rủi ro | Giảm thiểu |
|---|---|
| Rò rỉ domain → kết quả tốt giả | chia theo registered domain; báo cáo cả hai cách chia trong E1 |
| Model học định dạng nguồn (scheme, www) | chuẩn hóa trước khi trích feature; kiểm tra bằng SHAP |
| Benign nguồn C khác nguồn A | lấy benign có path thật; phân tích 20 lỗi; báo cáo trung thực |
| Biến đổi tạo URL vô nghĩa | kiểm tra hợp lệ tự động; in 20 mẫu/loại vào phụ lục |
| Phòng thủ chỉ "học thuộc" biến đổi | đánh giá bằng tấn công tham lam; giữ 1 loại biến đổi không dùng khi train |
| Nguồn B/C ít URL | dùng PhiUSIIL/bộ [6] làm B chính; C là tùy chọn |
| An toàn | không mở/crawl URL độc hại; chỉ xử lý chuỗi ký tự |

## 3.13 Sản phẩm cuối cam kết
Proposal · source repo (README, requirements, hướng dẫn chạy) · final report (8–15 trang) ·
slide 10–15 trang · file kết quả (bảng metric, confusion matrix, biểu đồ, log) · demo/video ·
khai báo sử dụng công cụ AI.
