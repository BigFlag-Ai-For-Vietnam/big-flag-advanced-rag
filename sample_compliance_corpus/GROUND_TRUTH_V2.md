# GROUND_TRUTH_V2 — Corpus mở rộng (tài liệu 11–50)

> Đáp án + thiết kế cho **40 tài liệu mô phỏng bổ sung** vào bộ 10 tài liệu gốc (xem
> `GROUND_TRUTH.md` — toàn bộ đáp án v1 **vẫn giữ nguyên hiệu lực**). Mục tiêu: tăng
> **retrieval pressure** (≥ 50 tài liệu, ~500–1.000 chunks) để Dense top-k không còn "vô tình"
> lấy đủ evidence — thể hiện khác biệt của Advanced RAG (graph traversal, version/scope
> awareness, sufficiency check).
>
> Nguyên tắc thiết kế (theo yêu cầu):
> - Ground truth dựng **trước**, tài liệu sinh **sau** và phải khớp file này.
> - Mỗi chủ đề 2–4 phiên bản (gốc → sửa đổi → thay thế một phần → phụ lục còn hiệu lực).
> - Nhiều văn bản dùng cùng thuật ngữ nhưng khác phạm vi (nội bộ/từ xa, KHCN/KHDN,
>   thường/trọng yếu, toàn hàng/chi nhánh).
> - Có tài liệu nhiễu: hướng dẫn cũ, FAQ, biên bản họp, dự thảo, thông báo tạm thời,
>   quy trình chi nhánh.
> - Evidence một câu trả lời nằm ở 4–7 tài liệu; quan hệ 2–3 bước.
> - Chunk overlap tự nhiên, KHÔNG cố tình bẻ nhỏ để Raw RAG thất bại thiếu tự nhiên.

---

## 1. Catalog tài liệu 11–50

Ký hiệu vai trò: `STATE` văn bản Nhà nước · `INT` quyết định nội bộ · `NOISE` nhiễu có chủ đích
· `AMEND` văn bản sửa đổi · `SUPERSEDED` đã bị thay thế (một phần/toàn bộ).

### Nhóm A — Giao dịch điện tử & xác thực (chuỗi phiên bản chính)

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 11 | NĐ 52/2024/NĐ-CP | 05/06/2024 | STATE nền tầng 1 | Giao dịch điện tử tài chính–ngân hàng; chứng từ điện tử có giá trị pháp lý; lưu chứng từ điện tử **10 năm**; chữ ký điện tử an toàn |
| 12 | TT 35/2024/TT-NHNN | 01/01/2025 | STATE tầng 2 (căn cứ NĐ 52) | An toàn giao dịch trực tuyến; phân loại giao dịch nhóm I–IV; **sinh trắc học bắt buộc khi chuyển > 10 triệu/lần hoặc > 20 triệu/ngày**; SMS OTP chỉ nhóm I–II |
| 13 | QĐ 118/2021/QĐ-DDB | 15/03/2021 | INT · SUPERSEDED một phần | Ngân hàng điện tử v1. Đ7: SMS OTP đến **100 triệu/GD** (❌ hết hiệu lực). **Phụ lục 03 — Biểu hạn mức theo kênh CÒN HIỆU LỰC** (IB 3 tỷ/ngày, Mobile 1 tỷ/ngày, ATM theo QĐ thẻ) |
| 14 | QĐ 267/2023/QĐ-DDB | 10/08/2023 | INT · AMEND của 118 · SUPERSEDED | Sửa Đ7 QĐ 118: SMS OTP chỉ đến **50 triệu/GD**, trên đó dùng soft OTP (❌ hết hiệu lực cùng 118) |
| 15 | QĐ 385/2025/QĐ-DDB | 01/07/2025 | INT hiện hành (căn cứ TT 35) | Kênh số v2. **Thay thế QĐ 118 + QĐ 267, TRỪ Phụ lục 03 QĐ 118** (giữ đến khi có biểu mới). Soft OTP mặc định; SMS OTP chỉ ≤ **5 triệu** (nội bộ chặt hơn TT 35); sinh trắc theo TT 35 |
| 16 | TB 51/2025/TB-DDB | 20/06/2025 | INT · điều khoản chuyển tiếp | Triển khai QĐ 385: từ 01/07–30/09/2025 khách chưa đăng ký sinh trắc được dùng soft OTP đến **20 triệu/lần**; sau 30/09 bắt buộc sinh trắc |

### Nhóm B — Hạ tầng CNTT & sự cố

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 17 | QĐ 173/2023/QĐ-DDB | 12/05/2023 | INT | Phân loại hệ thống CNTT 3 mức (thông thường/quan trọng/trọng yếu); **danh mục hệ thống trọng yếu áp dụng theo Phụ lục 02 QĐ 215/2022** (dẫn chiếu chéo → hop) |
| 18 | QĐ 356/2024/QĐ-DDB | 20/09/2024 | INT | Sao lưu & khôi phục. Bảng: trọng yếu **RPO ≤ 15 phút / RTO ≤ 2 giờ**; quan trọng 4h/8h; thông thường 24h/72h |
| 19 | QĐ 428/2025/QĐ-DDB | 15/02/2025 | INT | Sự cố CNTT mức 1–3; **báo cáo nội bộ Trung tâm CNTT trong 02 giờ** (mức ≥ 2); mức 3 kích hoạt DR theo QĐ 356 |
| 20 | QĐ 445/2025/QĐ-DDB | 10/03/2025 | INT (căn cứ TT 09 + TT 50) | **Báo cáo NHNN trong 24 giờ** sự cố nghiêm trọng/lộ dữ liệu; nhắc nghĩa vụ **72h thông báo chủ thể dữ liệu** theo NĐ 88 Đ13 |
| 21 | HD 12/2023/HD-DDB | 01/11/2023 | NOISE version-trap | Hướng dẫn vận hành TTDL viết theo **QĐ 215/2022** (chưa cập nhật); nhắc "mật khẩu tối thiểu 8 ký tự theo QĐ 215" ❌ |
| 22 | TT 50/2025/TT-NHNN | 15/04/2025 | STATE · AMEND của TT 09 | Sửa Đ11 TT 09: thời hạn báo cáo sự cố NHNN **72h → 24 giờ**; bổ sung diễn tập DR ≥ 1 lần/năm |

### Nhóm C — Dữ liệu cá nhân & marketing

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 23 | QĐ 133/2022/QĐ-DDB | 10/06/2022 | INT · SUPERSEDED một phần | Quản lý TTKH v1 — bị **QĐ 455/2025 thay thế TRỪ Phụ lục 01 (Mẫu văn bản đồng ý — còn dùng)**. Giá trị cũ: lưu hồ sơ 7 năm ❌ |
| 24 | QĐ 476/2025/QĐ-DDB | 05/05/2025 | INT | Tiếp thị số: consent riêng; tối đa **4 tin/tháng**; opt-out xử lý **72 giờ**; cá nhân hóa từ dữ liệu giao dịch = mục đích khác → cần đồng ý mới (NĐ 88 Đ5.2, QĐ 455) |
| 25 | CV 88/2025/CV-DDB | 12/06/2025 | INT · công văn (không phải QĐ) | Giải đáp chia sẻ dữ liệu với đối tác bảo hiểm: cần DPA + consent; chỉ diễn giải, không tạo quy định mới |
| 26 | QĐ 512/2025/QĐ-DDB | 20/05/2025 | INT | Chuyển DLCN ra nước ngoài: đánh giá tác động trước; nước bảo vệ tương đương/cam kết hợp đồng; dẫn mức phạt NĐ 88 (200–300tr) |

### Nhóm D — KYC & PCRT mở rộng

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 27 | QĐ 301/2023/QĐ-DDB | 15/04/2023 | INT · SUPERSEDED **toàn bộ** bởi 480 | KYC v1: ngưỡng giám sát tiền mặt **200tr** ❌ (mới 300tr); cập nhật thông tin 3 năm/lần ❌ |
| 28 | QĐ 517/2025/QĐ-DDB | 25/05/2025 | INT scope KHDN | KYC tổ chức: xác minh **chủ sở hữu hưởng lợi ≥ 25% vốn**; hồ sơ pháp lý; bổ sung (không thay thế) QĐ 480 |
| 29 | HD 04/2024/HD-DDB | 20/08/2024 | INT guidance | Nhận biết giao dịch đáng ngờ tại quầy — tình huống ví dụ cho GDV; text tương đồng TT 20 (nhiễu BM25 tốt) |

### Nhóm E — Rủi ro hoạt động & thuê ngoài

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 30 | TT 41/2024/TT-NHNN | 10/12/2024 | STATE | Rủi ro hoạt động & thuê ngoài CNTT: đánh giá NCC trước ký; quyền kiểm toán; cấm thuê ngoài toàn bộ chức năng kiểm soát |
| 31 | QĐ 468/2025/QĐ-DDB | 15/04/2025 | INT (căn cứ TT 41 + NĐ 88) | Bên thứ ba: phân loại NCC 3 mức; NCC xử lý DLCN phải ký **DPA**; đánh giá lại hằng năm; sự cố tại NCC → báo cáo như sự cố nội bộ (dẫn 428/445) |
| 32 | NQ 09/2025/NQ-HĐQT-DDB | 05/01/2025 | INT tầng HĐQT | Khung quản trị ATTT & dữ liệu: khẩu vị rủi ro; mô hình AI rủi ro cao phải trình HĐQT; giao TGĐ ban hành quy định chi tiết |

### Nhóm F — Truy cập & thiết bị

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 33 | QĐ 361/2024/QĐ-DDB | 25/10/2024 | INT scope đặc quyền | Truy cập đặc quyền: mật khẩu **≥ 16 ký tự, đổi 90 ngày** (khác 12/180 của QĐ 342 — phạm vi tài khoản đặc quyền); ghi hình phiên; JIT access |
| 34 | QĐ 412/2025/QĐ-DDB | 30/01/2025 | INT scope BYOD | Thiết bị cá nhân: **khóa màn hình di động sau 05 phút**; MDM bắt buộc; cấm lưu DLKH trên thiết bị cá nhân |
| 35 | HD 03/2025/HD-DDB | 10/02/2025 | INT guidance kỹ thuật | Phân quyền core banking: ma trận vai trò, nguyên tắc bốn mắt — thuật ngữ trùng QĐ 361 (nhiễu) |
| 36 | QĐ 296/2024/QĐ-DDB | 15/08/2024 | INT | Vòng đời tài khoản người dùng: thu hồi trong **24 giờ** khi nghỉ việc; rà soát quyền 6 tháng/lần; độ dài mật khẩu "**theo Quy chế ATTT hiện hành**" (→ hop tới QĐ 342) |

### Nhóm G — Nhiễu có chủ đích

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 37 | QT 07/2024/QT-CN-HT | 05/07/2024 | NOISE scope chi nhánh | Quy trình sự cố **chỉ áp dụng CN Hà Thành**: báo Giám đốc CN trong **04 giờ** — bổ sung, KHÔNG thay thế nghĩa vụ 02 giờ toàn hàng (QĐ 428) |
| 38 | BB 15/2025/BB-UBATTT | 18/05/2025 | NOISE đề xuất chưa duyệt | Biên bản họp UB ATTT: **đề xuất** nâng khóa phiên nội bộ 15→**20 phút** — CHƯA phê duyệt, không có hiệu lực |
| 39 | DT-QĐ-ATTT-v3/2025 | (dự thảo 01/06/2025) | NOISE dự thảo | **DỰ THẢO** Quy chế ATTT v3 lấy ý kiến: mật khẩu **14 ký tự**, khóa phiên **10 phút** — CHƯA HIỆU LỰC |
| 40 | FAQ 02/2025/PC-DDB | 10/03/2025 | NOISE trả lời thiếu | Hỏi đáp ATTT: có câu "khóa phiên 15 phút áp dụng cho **mọi** trường hợp" — bỏ sót ngoại lệ từ xa 30 phút (đúng một phần) |
| 41 | TB 44/2025/TB-DDB | 22/04/2025 (hết 22/05/2025) | NOISE temporal | Tăng cường chống phishing **tạm thời 30 ngày**: giảm hạn mức soft OTP còn 10tr — ĐÃ HẾT HIỆU LỰC theo thời gian |

### Nhóm H — Thẻ & thanh toán

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 42 | TT 18/2024/TT-NHNN | 05/09/2024 | STATE | Hoạt động thẻ: yêu cầu hạn mức theo loại thẻ; tra soát tối đa **45 ngày** (nội địa) |
| 43 | QĐ 205/2022/QĐ-DDB | 20/02/2022 | INT · SUPERSEDED **toàn bộ** bởi 490 | Thẻ v1: rút ATM **50tr/ngày** ❌ (trap) |
| 44 | QĐ 490/2025/QĐ-DDB | 15/04/2025 | INT hiện hành (căn cứ TT 18) | Thẻ v2 (thay thế toàn bộ 205): rút ATM **30tr/ngày** thẻ ghi nợ chuẩn, **100tr/ngày** thẻ bạch kim; khóa thẻ khẩn cấp 24/7 |
| 45 | QĐ 521/2025/QĐ-DDB | 30/05/2025 | INT cross-chain | Tra soát khiếu nại thẻ + kênh số: tiếp nhận 24h; nội địa **45 ngày** (theo TT 18), quốc tế **60 ngày**; tạm ứng khi lỗi hệ thống ≤ 5 ngày |

### Nhóm I — AI mở rộng

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 46 | QĐ 530/2025/QĐ-DDB | 10/06/2025 | INT (căn cứ TT 04, QĐ 455, QĐ 502) | Chatbot KH: không tự quyết định tín dụng; lưu hội thoại **2 năm**; dùng hội thoại để cải thiện mô hình → phải **ẩn danh theo QĐ 502 Đ6** VÀ xem xét **đồng ý riêng theo QĐ 455 Đ5** (nối cả hai bên conflict AI) |
| 47 | HD 09/2025/HD-DDB | 20/06/2025 | INT guidance | Đánh giá rủi ro mô hình AI theo TT 04: 3 mức; mức cao → trình HĐQT (theo NQ 09); hồ sơ mô hình, kiểm định trước triển khai |

### Nhóm J — Lưu trữ & mật mã

| # | Số hiệu | Ngày hl | Vai trò | Nội dung then chốt |
|---|---------|---------|---------|--------------------|
| 48 | QĐ 260/2023/QĐ-DDB | 15/09/2023 | INT tổng hợp | Bảng lưu trữ tổng hợp: chứng từ kế toán 10 năm; hồ sơ tín dụng **15 năm** sau tất toán; DLCN theo NĐ 88/QĐ 455 (5 năm); hồ sơ PCRT 10 năm (TT 20) — carve-out tổng hợp, KHÔNG phải xung đột |
| 49 | QĐ 535/2025/QĐ-DDB | 25/06/2025 | INT | Khóa mật mã & chứng thư số: **AES-256** cho dữ liệu nhạy cảm (NĐ 88); khóa hệ thống trọng yếu lưu trong **HSM** (danh mục trọng yếu → QĐ 173 → PL02 QĐ 215); rotate khóa **12 tháng** |
| 50 | HD 15/2024/HD-DDB | 05/12/2024 | INT guidance | Xử lý yêu cầu quyền chủ thể dữ liệu (NĐ 88 Đ12 + QĐ 455): xác nhận **72 giờ**, giải quyết **15 ngày**; dùng **Mẫu PL01 QĐ 133** (phần còn hiệu lực) |
| 51 | QĐ 540/2025/QĐ-DDB | 30/06/2025 | INT · nguồn khai báo hiệu lực | **Công bố Danh mục văn bản hết hiệu lực toàn bộ/một phần**: 215 (giữ PL02), 118 (giữ PL03), 267 (toàn bộ), 133 (giữ PL01), 301 (toàn bộ), 205 (toàn bộ) + văn bản thay thế tương ứng — nguồn tập trung cho các cạnh THAY_THE |

---

## 2. Ma trận quan hệ mới (graph edges kỳ vọng)

### 2.1 Thay thế / sửa đổi (THAY_THE / SUA_DOI)

| Nguồn | Đích | Loại | Ghi chú |
|-------|------|------|---------|
| QĐ 385/2025 | QĐ 118/2021 | THAY_THE (partial) | **giữ Phụ lục 03** đến khi có biểu hạn mức mới |
| QĐ 385/2025 | QĐ 267/2023 | THAY_THE (full) | văn bản sửa đổi chết theo văn bản gốc |
| QĐ 267/2023 | QĐ 118/2021 | SUA_DOI | sửa Điều 7 (hạn mức SMS OTP) |
| TT 50/2025 | TT 09/2024 | SUA_DOI | sửa Đ11: 72h → 24h báo cáo NHNN |
| QĐ 455/2025 | QĐ 133/2022 | THAY_THE (partial) | **giữ Phụ lục 01** (mẫu đồng ý) — khai báo tại QĐ 540/2025 |
| QĐ 480/2025 | QĐ 301/2023 | THAY_THE (full) | KYC v1 chết toàn bộ — khai báo tại QĐ 540/2025 |
| QĐ 490/2025 | QĐ 205/2022 | THAY_THE (full) | Thẻ v1 chết toàn bộ — khai báo tại Đ12 QĐ 490 và QĐ 540/2025 |

> Lưu ý thiết kế: quan hệ 455→133 và 480→301 KHÔNG được tuyên bố trong chính văn bản 455/480
> (hai PDF v1 giữ nguyên, không regenerate); nguồn khai báo tập trung là **QĐ 540/2025 —
> Danh mục văn bản hết hiệu lực** (tài liệu 51). Đây cũng là một bài test thực tế: hệ thống
> phải nhặt quan hệ thay thế từ văn bản danh mục, không chỉ từ điều khoản thi hành.

### 2.2 Căn cứ / tuân thủ (CAN_CU) — chuỗi 3 tầng mới

```text
NĐ 52/2024 ← TT 35/2024 ← QĐ 385/2025          (kênh số)
NĐ 88/2024 ← TT 09/2024 (+TT 50 sửa đổi) ← QĐ 342/2024, QĐ 445/2025   (ATTT — v1 + nhánh mới)
TT 41/2024 + NĐ 88 ← QĐ 468/2025               (thuê ngoài)
TT 18/2024 ← QĐ 490/2025 ← QĐ 521/2025         (thẻ)
TT 04/2025 + QĐ 455 + QĐ 502 ← QĐ 530/2025     (chatbot — hội tụ 3 nguồn)
TT 20/2024 ← QĐ 480/2025 ← QĐ 517/2025         (KYC)
NQ 09/2025 (HĐQT) → giao TGĐ ban hành → các QĐ nội bộ (tầng quản trị)
```

### 2.3 Dẫn chiếu chéo quan trọng (THAM_CHIEU)

- QĐ 173 → **Phụ lục 02 QĐ 215** (danh mục trọng yếu — phụ lục của văn bản đã bị thay thế một phần).
- QĐ 356 → QĐ 173 (phân loại quyết định RTO/RPO).
- QĐ 535 → QĐ 173 (khóa hệ thống trọng yếu → HSM).
- QĐ 296 → "Quy chế ATTT hiện hành" (không nêu số → resolver phải map về QĐ 342).
- QĐ 445 → NĐ 88 Đ13 (72h chủ thể) + TT 50 (24h NHNN).
- QĐ 521 → QĐ 490 (thẻ) + QĐ 385 (kênh số).
- TB 51 → QĐ 385 (chuyển tiếp).
- HD 12 → QĐ 215 (❌ văn bản nền đã bị thay thế — hướng dẫn lỗi thời).

---

## 3. Ma trận giá trị theo chủ đề (để đối chiếu conflict/scope)

### 3.1 "Mật khẩu" — 1 khái niệm, 4+ nguồn giá trị

| Nguồn | Giá trị | Phạm vi | Hiệu lực |
|-------|---------|---------|----------|
| QĐ 342 Đ2 | **12 ký tự**, 180 ngày | người dùng nội bộ (chuẩn) | ✅ hiện hành |
| QĐ 401 Đ4 | 8 ký tự | từ xa — nhưng Đ4.2 nhường QĐ 342 | ✅ (nhường) |
| QĐ 361 | **16 ký tự**, 90 ngày | tài khoản đặc quyền | ✅ scope riêng |
| QĐ 215 Đ2 | 8 ký tự | (cũ) | ❌ bị thay thế |
| HD 12/2023 | nhắc "8 ký tự theo QĐ 215" | TTDL | ❌ lỗi thời |
| DT v3 | 14 ký tự | (dự thảo) | ❌ chưa hiệu lực |

**Đáp án đúng:** thường **12**; đặc quyền **16**; không dùng 8/14.

### 3.2 "Khóa phiên / khóa màn hình"

| Nguồn | Giá trị | Phạm vi | Hiệu lực |
|-------|---------|---------|----------|
| QĐ 342 Đ5 | **15 phút** | phiên hệ thống nội bộ | ✅ |
| QĐ 401 Đ5 | **30 phút** | phiên làm việc từ xa | ✅ (không có tuyên bố ưu tiên — cảnh báo scope, xem GT v1) |
| QĐ 412 | **05 phút** | khóa màn hình thiết bị di động BYOD | ✅ scope riêng |
| BB 15/2025 | 20 phút | đề xuất | ❌ chưa duyệt |
| DT v3 | 10 phút | dự thảo | ❌ chưa hiệu lực |
| FAQ 02 | "15 phút mọi trường hợp" | — | ⚠️ đúng một phần (bỏ sót từ xa/BYOD) |

### 3.3 "Hạn mức xác thực giao dịch số" (chuỗi version + temporal)

| Nguồn | Giá trị | Hiệu lực |
|-------|---------|----------|
| QĐ 118/2021 Đ7 | SMS OTP đến 100tr | ❌ bị sửa rồi bị thay thế |
| QĐ 267/2023 | SMS OTP đến 50tr | ❌ bị thay thế |
| TT 35/2024 | sinh trắc bắt buộc > 10tr/lần, > 20tr/ngày | ✅ |
| QĐ 385/2025 | SMS OTP ≤ **5tr**; soft OTP mặc định; sinh trắc theo TT 35 | ✅ hiện hành |
| TB 51/2025 | chuyển tiếp: chưa sinh trắc → soft OTP ≤ 20tr/lần (đến 30/09/2025) | ✅ trong khung thời gian |
| TB 44/2025 | soft OTP tạm còn 10tr | ❌ hết hạn 30 ngày (22/05/2025) |
| PL 03 QĐ 118 | hạn mức kênh: IB 3 tỷ/ngày, Mobile 1 tỷ/ngày | ✅ CÒN hiệu lực (giữ lại) |

### 3.4 "Báo cáo sự cố" — 4 nghĩa vụ song song, khác đích đến

| Nguồn | Thời hạn | Báo cho ai | Hiệu lực |
|-------|----------|-----------|----------|
| QĐ 428 | **02 giờ** | Trung tâm CNTT (nội bộ, mức ≥ 2) | ✅ |
| QĐ 445 (theo TT 50 sửa TT 09) | **24 giờ** | NHNN (sự cố nghiêm trọng) | ✅ |
| NĐ 88 Đ13 | **72 giờ** | chủ thể dữ liệu + NHNN (vi phạm DLCN) | ✅ |
| QT 07 CN-HT | 04 giờ | Giám đốc CN (chỉ CN Hà Thành, bổ sung) | ✅ scope hẹp |
| TT 09 Đ11 (nguyên bản) | 72 giờ NHNN | — | ❌ đã bị TT 50 sửa thành 24h |

### 3.5 "Thời hạn lưu trữ" (carve-out tổng hợp — KHÔNG báo xung đột giả)

| Loại hồ sơ | Thời hạn | Nguồn |
|-----------|----------|-------|
| DLCN sau chấm dứt quan hệ | 5 năm | NĐ 88 Đ8, QĐ 455 |
| Hồ sơ KYC/PCRT | 10 năm | TT 20 Đ10, QĐ 480 Đ8 (chuyên ngành thắng) |
| Chứng từ điện tử | 10 năm | NĐ 52 |
| Hồ sơ tín dụng | 15 năm sau tất toán | QĐ 260 |
| Hội thoại chatbot | 2 năm | QĐ 530 |
| Nhật ký truy cập DLCN | 2 năm | NĐ 88 |
| Hồ sơ TTKH (cũ) | 7 năm | ❌ QĐ 133 — bị thay thế |

---

## 4. Test cases V2 (mỗi case: kết luận đúng + evidence bắt buộc + traversal + bẫy + lỗi cần phát hiện)

> Format từng case:
> **KL** = kết luận đúng · **EV** = documents/chunks bắt buộc (đủ mới tính Evidence Coverage 100%)
> · **TRAV** = quan hệ cần đi · **TRAP** = tài liệu nhiễu dễ retrieve nhầm · **FAIL** = lỗi chấm điểm.

### Nhóm 1 — Thay đổi theo thời gian

**V2-01.** *"Chuyển khoản 60 triệu trên Internet Banking cần xác thực bằng gì? Hạn mức ngày của kênh này?"*
- **KL:** Sinh trắc học (60tr > 10tr/lần theo TT 35; QĐ 385 áp dụng TT 35). Hạn mức kênh IB: 3 tỷ/ngày theo **Phụ lục 03 QĐ 118 còn hiệu lực**.
- **EV:** QĐ 385 (Đ xác thực + Đ điều khoản thi hành giữ PL03) · TT 35 (ngưỡng 10tr) · PL03 QĐ 118 (3 tỷ). 3–4 docs.
- **TRAV:** QĐ 385 —CAN_CU→ TT 35; QĐ 385 —THAY_THE(partial, giữ PL03)→ QĐ 118.
- **TRAP:** QĐ 118 Đ7 (100tr SMS), QĐ 267 (50tr), TB 44 (10tr hết hạn), DT nếu retrieve nhầm.
- **FAIL:** dùng giá trị 100tr/50tr (version); bỏ sót PL03 (coverage); dùng TB 44 (temporal).

**V2-02.** *"Trong tháng 8/2025, khách chưa đăng ký sinh trắc học có chuyển được 15 triệu trên app không?"*
- **KL:** Được — trong giai đoạn chuyển tiếp 01/07–30/09/2025, soft OTP được phép đến 20tr/lần (TB 51). Sau 30/09 thì không.
- **EV:** TB 51 (chuyển tiếp) · QĐ 385 (quy định gốc) · TT 35 (ngưỡng sinh trắc).
- **TRAV:** TB 51 —THAM_CHIEU→ QĐ 385.
- **TRAP:** trả lời "không được vì > 10tr" (bỏ sót điều khoản chuyển tiếp).
- **FAIL:** thiếu evidence chuyển tiếp; kết luận tuyệt đối không điều kiện thời gian.

**V2-03.** *"Hạn mức rút ATM của thẻ ghi nợ chuẩn là bao nhiêu?"*
- **KL:** **30 triệu/ngày** (QĐ 490/2025 — hiện hành).
- **EV:** QĐ 490 (bảng hạn mức). 1–2 docs (câu tra cứu, nhưng có bẫy version).
- **TRAP:** QĐ 205/2022 (50tr — bị thay thế **toàn bộ**).
- **FAIL:** Current-version Accuracy — trả lời 50tr.

**V2-04.** *"Báo cáo sự cố ATTT nghiêm trọng lên NHNN trong bao lâu?"*
- **KL:** **24 giờ** — TT 09 Đ11 quy định 72h nhưng **đã bị TT 50/2025 sửa thành 24h**; QĐ 445 nội bộ hóa 24h.
- **EV:** TT 50 (điều sửa đổi) · TT 09 (điều gốc bị sửa) · QĐ 445.
- **TRAV:** TT 50 —SUA_DOI→ TT 09; QĐ 445 —CAN_CU→ TT 09 + TT 50.
- **TRAP:** TT 09 nguyên bản (72h) — chunk rất dễ được retrieve vì đúng chủ đề.
- **FAIL:** trả lời 72h = dùng văn bản đã bị sửa đổi (đây là **state-level amendment** — khó hơn v1).

### Nhóm 2 — Chồng lấn & ngoại lệ

**V2-05.** *"Mật khẩu đăng nhập tối thiểu bao nhiêu ký tự? Với quản trị viên hệ thống thì sao?"*
- **KL:** Người dùng thường **12** (QĐ 342 Đ2); tài khoản đặc quyền **16, đổi 90 ngày** (QĐ 361). QĐ 401 (8) tự nhường; các giá trị 8/14 khác không hiệu lực.
- **EV:** QĐ 342 · QĐ 361 · (QĐ 401 Đ4.2 để giải thích nhường).
- **TRAP:** DT v3 (14), HD 12 (8 theo 215), QĐ 215 (8), FAQ 02.
- **FAIL:** thiếu vế đặc quyền (coverage); dùng 14/8 (version); không phân biệt scope.

**V2-06.** *"Thiết bị làm việc tự khóa sau bao nhiêu phút khi không thao tác?"*
- **KL:** Phân theo phạm vi: phiên nội bộ **15'** (342), phiên từ xa **30'** (401 — không có ưu tiên, cảnh báo như GT v1), màn hình thiết bị di động BYOD **5'** (412). Đề xuất 20' (BB 15) và dự thảo 10' (DT v3) không có hiệu lực.
- **EV:** QĐ 342 · QĐ 401 · QĐ 412 (3 giá trị hiện hành, 3 docs bắt buộc).
- **TRAP:** BB 15, DT v3, FAQ 02 ("mọi trường hợp").
- **FAIL:** Unsupported Conclusion nếu lấy 20'/10'; thiếu 1 trong 3 scope (coverage); chọn 1 giá trị duy nhất (conflict detection).

**V2-07.** *"Có được dùng lịch sử giao dịch của khách để gửi ưu đãi cá nhân hóa không?"*
- **KL:** Chỉ khi có **đồng ý mới** — cá nhân hóa từ dữ liệu giao dịch là mục đích khác mục đích thu thập (NĐ 88 Đ5.2 + Đ9; QĐ 455; QĐ 476). Tần suất tối đa 4 tin/tháng, opt-out 72h (476).
- **EV:** QĐ 476 · QĐ 455 · NĐ 88 (Đ5.2/Đ9). CV 88 hỗ trợ diễn giải.
- **TRAV:** QĐ 476 —CAN_CU→ QĐ 455 —CAN_CU→ NĐ 88.
- **FAIL:** trả lời "được vì đã là khách hàng" (unsupported); thiếu điều kiện consent mới.

**V2-08.** *"Hồ sơ của khách hàng đóng tài khoản được lưu bao lâu?"* (carve-out tổng hợp)
- **KL:** Phân theo **loại hồ sơ**: DLCN 5 năm (NĐ 88/455) · KYC-PCRT 10 năm (TT 20/480) · chứng từ điện tử 10 năm (NĐ 52) · hồ sơ tín dụng 15 năm (260). Đây KHÔNG phải xung đột — pháp luật chuyên ngành/loại hồ sơ khác nhau.
- **EV:** QĐ 260 (bảng tổng hợp) · NĐ 88 Đ8 · TT 20 Đ10/QĐ 480 Đ8. 3–4 docs.
- **TRAP:** QĐ 133 (7 năm — hết hiệu lực); báo "xung đột 5 vs 10 vs 15 năm".
- **FAIL:** **False conflict alarm** (chấm Conflict Detection — precision); dùng 7 năm.

### Nhóm 3 — Suy luận đa văn bản

**V2-09.** *"Hệ thống core banking gặp thảm họa phải khôi phục trong bao lâu, và căn cứ nào xác định nó là hệ thống trọng yếu?"*
- **KL:** RTO ≤ **2 giờ**, RPO ≤ 15 phút (QĐ 356 — mức trọng yếu). Core banking thuộc danh mục trọng yếu vì QĐ 173 phân loại theo **Phụ lục 02 QĐ 215/2022 — phụ lục còn hiệu lực dù QĐ 215 đã bị thay thế một phần**.
- **EV:** QĐ 356 (bảng RTO/RPO) · QĐ 173 (phân loại + dẫn PL02) · PL02 QĐ 215 (danh mục) · (QĐ 342 Đ về giữ PL02). **3 hop, 3–4 docs — case chủ lực.**
- **TRAV:** QĐ 356 —THAM_CHIEU→ QĐ 173 —THAM_CHIEU→ PL02 QĐ 215; QĐ 342 —THAY_THE(partial)→ QĐ 215.
- **TRAP:** cho rằng QĐ 215 hết hiệu lực toàn bộ → mất căn cứ danh mục.
- **FAIL:** thiếu mắt xích 173 hoặc PL02 (coverage); kết luận RTO không kèm căn cứ trọng yếu.

**V2-10.** *"Nhân viên chi nhánh Hà Thành phát hiện sự cố CNTT mức 2 phải báo cho ai, trong bao lâu?"*
- **KL:** **Hai nghĩa vụ song song**: báo Trung tâm CNTT toàn hàng trong **02 giờ** (QĐ 428) VÀ báo Giám đốc CN trong 04 giờ theo quy trình riêng của CN (QT 07 — bổ sung, không thay thế). Nếu nghiêm trọng → ngân hàng báo NHNN 24h (445).
- **EV:** QĐ 428 · QT 07 · (QĐ 445 cho vế mở rộng).
- **TRAP:** chỉ trả lời 4h theo QT 07 (scope trap — quy trình chi nhánh không thay thế quy định toàn hàng).
- **FAIL:** thiếu 1 trong 2 nghĩa vụ; đảo ưu tiên.

**V2-11.** *"Có được dùng nội dung hội thoại của khách với chatbot để huấn luyện lại mô hình không?"*
- **KL:** Có điều kiện: phải **ẩn danh hóa theo QĐ 502 Đ6** (lưu ≤ 24 tháng) VÀ xem xét yêu cầu **đồng ý riêng theo QĐ 455 Đ5**; hai văn bản không tuyên bố ưu tiên → nêu cả hai + mấu chốt "ẩn danh còn là DLCN không" (NĐ 88 Đ2), rủi ro mô hình đánh giá theo TT 04/HD 09; QĐ 530 yêu cầu quy trình ẩn danh trước khi đưa vào huấn luyện.
- **EV:** QĐ 530 · QĐ 502 Đ6 · QĐ 455 Đ5 · NĐ 88 Đ2 · (TT 04/HD 09). **5–6 docs — case dày nhất.**
- **TRAV:** QĐ 530 —CAN_CU→ {TT 04, QĐ 455, QĐ 502}; QĐ 455/502 —(conflict im lặng, GT v1)→.
- **FAIL:** kết luận một chiều; bỏ NĐ 88 định nghĩa; không cảnh báo điểm chưa rõ.

**V2-12.** *"Thuê công ty ngoài phân tích dữ liệu khách hàng cần đáp ứng điều kiện gì?"*
- **KL:** NCC xử lý DLCN phải ký **DPA** + đánh giá trước khi ký và hằng năm (QĐ 468, TT 41); dữ liệu chia sẻ tuân thủ NĐ 88 (bên xử lý dữ liệu, Đ2.5) + QĐ 455; nếu chuyển ra nước ngoài → thêm QĐ 512 (đánh giá tác động); sự cố tại NCC báo cáo như nội bộ (428/445).
- **EV:** QĐ 468 · TT 41 · NĐ 88 · QĐ 455 · (QĐ 512 nếu offshore). 4–5 docs.
- **TRAV:** QĐ 468 —CAN_CU→ TT 41 + NĐ 88.
- **FAIL:** bỏ DPA; bỏ nhánh offshore khi câu hỏi có yếu tố nước ngoài.

**V2-13.** *"Một mô hình AI chấm điểm tín dụng tự động cần những phê duyệt nào trước khi triển khai?"*
- **KL:** Đánh giá rủi ro theo TT 04 + HD 09 (3 mức); chấm điểm tín dụng tự động = rủi ro cao → **trình HĐQT theo NQ 09**; dữ liệu huấn luyện tuân thủ QĐ 455/502 (consent/ẩn danh — dẫn V2-11); hồ sơ mô hình + kiểm định trước triển khai (HD 09).
- **EV:** HD 09 · TT 04 · NQ 09 · QĐ 455/502. 4–5 docs, có tầng quản trị.
- **TRAV:** HD 09 —CAN_CU→ TT 04; HD 09 —THAM_CHIEU→ NQ 09.
- **FAIL:** thiếu tầng HĐQT; thiếu nhánh dữ liệu.

### Nhóm 0 — Đối chứng công bằng (Raw RAG phải làm tốt ngang)

**V2-14.** *"Mức phạt chuyển dữ liệu cá nhân ra nước ngoài trái phép?"* → 200–300tr (NĐ 88 bảng Đ14). 1 doc.
**V2-15.** *"Mỗi tháng được gửi tối đa bao nhiêu tin tiếp thị cho một khách hàng?"* → 4 tin/tháng (QĐ 476). 1 doc.
**V2-16.** *"Khóa mật mã phải rotate bao lâu một lần?"* → 12 tháng (QĐ 535). 1 doc.

---

## 5. Metrics bổ sung khi đánh giá (ngoài Context Precision/Recall)

| Metric | Định nghĩa | Cách chấm trên bộ case |
|--------|-----------|------------------------|
| **Evidence Coverage** | % khía cạnh bắt buộc (mục EV của case) có ít nhất 1 chunk/graph-fact đúng trong context cuối | đếm theo checklist EV từng case |
| **Current-version Accuracy** | % câu trả lời không dùng giá trị từ văn bản hết hiệu lực / bị sửa đổi / dự thảo / đề xuất / hết hạn temporal | bẫy: 215, 118, 267, 133, 301, 205, TT09-Đ11-cũ, DT v3, BB 15, TB 44, HD 12 |
| **Conflict Detection Rate** | recall: % case có conflict thật (V2-06, V2-11 + v1) được cảnh báo; precision: KHÔNG báo giả trên case carve-out (V2-08, KYC 10 vs 5 năm v1) | cả hai chiều đều tính |
| **Unsupported Conclusion Rate** | % kết luận vượt quá evidence (chọn 1 giá trị khi chưa có ưu tiên; dùng đề xuất/dự thảo như quy định) | càng thấp càng tốt |

**Kỳ vọng công bằng:** nhóm 0 (V2-14→16) Raw RAG ≈ BigRAG; khác biệt phải đến từ nhóm 1–3
(coverage, version, scope, traversal) — không phải từ việc corpus "gài" Raw RAG một cách
thiếu tự nhiên.

---

## 6. Quy ước sinh tài liệu (cho `_generator/docs_content_v2.py`)

- Giữ nguyên universe DDB, watermark mô phỏng lề trên/dưới như v1.
- Mỗi văn bản 3–6 trang; QĐ nội bộ có đủ: căn cứ → chương/điều → bảng giá trị (nếu có) →
  tổ chức thực hiện → hiệu lực thi hành (ghi rõ thay thế/sửa đổi gì) → ký + nơi nhận.
- Điều khoản then chốt phải khớp **đúng số liệu** trong file này; boilerplate (phạm vi, giải
  thích từ ngữ, trách nhiệm, kiểm tra) được phép tái sử dụng có biến thể — trùng lặp boilerplate
  giữa các văn bản là **tự nhiên và có chủ đích** (tăng nhiễu cho dense/BM25).
- Văn bản NOISE phải ghi rõ bản chất trong chính nội dung (dự thảo/biên bản/thông báo tạm thời/
  chỉ áp dụng chi nhánh) — bẫy nằm ở chỗ retrieval bỏ qua metadata đó, không phải ở việc giấu nó.
