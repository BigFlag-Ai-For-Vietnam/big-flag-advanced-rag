"""Text mẫu cho PoC — trích text-layer thật từ `backend/docs/Biểu phí - 23.6.26.pdf`
(2 trang biểu phí thẻ tín dụng Sung Túc). Hardcode để PoC chạy lại được (reproducible),
không phụ thuộc pdfplumber/PDF gốc còn tồn tại hay không.

Chọn đúng dạng "bảng biểu phí" vì đây là ca dễ sinh noise nhất khi extract KG tự do:
rất nhiều số liệu/điều kiện gần giống nhau (15+ loại phí, mỗi loại 2 cột khách hàng có/
không đăng ký gói) — đúng kịch bản "John Doe, 45 vs John Doe, age 45" mà bài viết tham
khảo mô tả, chỉ khác là lặp trên loại phí thay vì tên người.
"""

SAMPLE_TEXT = """BIỂU PHÍ THẺ TÍN DỤNG SUNG TÚC

Biểu phí áp dụng cho Thẻ tín dụng Sung Túc do SHBFinance phát hành, áp dụng kể từ
ngày 26/06/2026.

1. Phí gói Sung Túc hàng năm: Khách hàng không đăng ký gói Sung Túc: NA (không áp dụng).
Khách hàng đăng ký sử dụng gói Sung Túc: 3% Hạn mức tín dụng.

2. Phí gói Sung Túc trọn đời: Khách hàng không đăng ký gói Sung Túc: NA. Khách hàng
đăng ký sử dụng gói Sung Túc: 7.5% Hạn mức tín dụng.

3. Phí phát hành lần đầu: Miễn phí cho cả hai nhóm khách hàng.

4. Phí cấp lại thẻ: Khách hàng không đăng ký gói Sung Túc: 110.000 VND/lần. Khách hàng
đăng ký gói Sung Túc: Miễn phí, trừ trường hợp thẻ bị lỗi hoặc lỗi thiết bị thì cũng
được miễn phí.

5. Phí quản lý hạn mức tín dụng: Khách hàng không đăng ký gói Sung Túc: 550.000 VND/năm.
Khách hàng đăng ký gói Sung Túc: Miễn phí.

6. Phí thông báo mất thẻ toàn cầu: Khách hàng không đăng ký gói Sung Túc: 220.000
VND/lần. Khách hàng đăng ký gói Sung Túc: Miễn phí.

7. Phí dịch vụ SMS: Khách hàng không đăng ký gói Sung Túc: 11.000 VND/tháng. Khách hàng
đăng ký gói Sung Túc: Miễn phí.

8. Phí rút tiền mặt tại ATM: Khách hàng không đăng ký gói Sung Túc: 11.000 VND/giao dịch.
Khách hàng đăng ký gói Sung Túc: Miễn phí cho 10 giao dịch đầu tiên.

9. Phí thường niên: Miễn phí cho cả hai nhóm khách hàng.

10. Phí gia hạn thẻ: Miễn phí cho cả hai nhóm khách hàng.

11. Phí đóng thẻ: Miễn phí cho cả hai nhóm khách hàng.

12. Phí tra soát khiếu nại sai: Khách hàng không đăng ký gói Sung Túc: 220.000
VND/giao dịch. Khách hàng đăng ký gói Sung Túc: Miễn phí.

13. Phí cung cấp giấy xác nhận bằng văn bản (dư nợ thẻ, tình trạng thẻ, sao kê): Khách
hàng không đăng ký gói Sung Túc: 100.000 VND/bảng. Khách hàng đăng ký gói Sung Túc:
Miễn phí.

14. Phí chậm thanh toán: áp dụng cho cả hai nhóm khách hàng, mức 4% số tiền chậm thanh
toán, tối thiểu 100.000 VND.

15. Phí vượt hạn mức: Miễn phí cho cả hai nhóm khách hàng.

16. Phí chuyển đổi ngoại tệ: Khách hàng không đăng ký gói Sung Túc: Miễn phí. Khách
hàng đăng ký gói Sung Túc: 3.3% Số tiền giao dịch.

17. Phí xử lý giao dịch: 12.000 VND/giao dịch, áp dụng cho cả hai nhóm khách hàng.

18. Phí ứng tiền mặt (không áp dụng với giao dịch rút tiền mặt tại ATM): Khách hàng
không đăng ký gói Sung Túc: 0.2% số tiền rút thành công, tối thiểu 20.000 VND, tối đa
60.000 VND/giao dịch. Khách hàng đăng ký gói Sung Túc: Miễn phí.

19. Lãi suất thẻ: mức lãi suất thông thường từ 29% đến 60%/năm, mức lãi suất cụ thể
được SHBFinance thông báo cho khách hàng tại thời điểm phê duyệt phát hành thẻ tín
dụng. Lãi suất ưu đãi áp dụng theo chính sách ưu đãi của SHBFinance triển khai từng
thời kỳ.

Ghi chú: Phí gói Sung Túc hàng năm là phí thu hàng năm, bắt đầu thu khi thẻ có phát
sinh giao dịch đầu tiên và được tự động tái tục hàng năm vào ngày thu lần đầu tiên.
Phí gói Sung Túc trọn đời là phí được thu 1 lần duy nhất theo hiệu lực thẻ. Biểu phí đã
bao gồm VAT."""
