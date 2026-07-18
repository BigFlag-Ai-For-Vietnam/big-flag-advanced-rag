export interface ShowcasePreset {
  id: string;
  title: string;
  category: string;
  question: string;
  painPoint: string;
  expected: string;
}

export const SHOWCASE_PRESETS: ShowcasePreset[] = [
  {
    id: "password-priority",
    title: "Quy tắc ưu tiên",
    category: "Phiên bản & xung đột",
    question: "Mật khẩu đăng nhập hệ thống nội bộ tối thiểu bao nhiêu ký tự?",
    painPoint: "Cần phân biệt bản hiện hành, bản đã thay thế và điều khoản ưu tiên giữa hai quy định.",
    expected:
      "Tối thiểu 12 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt. Quy định làm việc từ xa nêu 8 ký tự nhưng đồng thời yêu cầu ưu tiên Quy chế ATTT hiện hành (QĐ342); QĐ215 là phiên bản cũ đã bị thay thế.",
  },
  {
    id: "critical-systems",
    title: "Thay thế một phần",
    category: "Hiệu lực văn bản",
    question: "Danh mục hệ thống thông tin trọng yếu của DDB gồm những gì?",
    painPoint: "Văn bản chính đã bị thay thế nhưng một phụ lục của nó vẫn tiếp tục có hiệu lực.",
    expected:
      "Có 4 hệ thống: Core Banking T24 (cấp độ 4), thanh toán liên ngân hàng (cấp độ 4), eKYC (cấp độ 3), và hệ thống thẻ/ATM (cấp độ 3). Phụ lục 02 của QĐ215 vẫn có hiệu lực cho đến khi có danh mục thay thế.",
  },
  {
    id: "session-timeout",
    title: "Xung đột theo phạm vi",
    category: "Đối chiếu đa văn bản",
    question: "Phiên làm việc tự động khóa sau bao nhiêu phút?",
    painPoint: "Không được chọn một con số duy nhất; phải nhận ra hai phạm vi áp dụng khác nhau.",
    expected:
      "15 phút đối với máy trạm trong mạng nội bộ và 30 phút đối với thiết bị làm việc từ xa. Cần nêu cả hai giá trị kèm đúng phạm vi, không tự coi một quy định thay thế quy định còn lại.",
  },
  {
    id: "ai-training",
    title: "Consent và ẩn danh",
    category: "Tổng hợp chính sách",
    question: "DDB có được dùng dữ liệu khách hàng để huấn luyện AI không?",
    painPoint: "Cần tổng hợp điều kiện từ quy định dữ liệu cá nhân, AI nội bộ và quản trị rủi ro AI.",
    expected:
      "Có, nhưng phải có sự đồng ý riêng của khách hàng hoặc dữ liệu đã được ẩn danh/phi định danh đúng quy trình và không thể truy ngược. Dữ liệu ẩn danh dùng cho AI nội bộ tối đa 24 tháng; cấm đưa dữ liệu nhạy cảm lên AI công cộng hoặc huấn luyện bằng dữ liệu chưa ẩn danh.",
  },
  {
    id: "kyc-retention",
    title: "Ngoại lệ chuyên ngành",
    category: "Carve-out pháp lý",
    question: "Hồ sơ nhận biết khách hàng (KYC) phải lưu trữ bao lâu?",
    painPoint: "Mốc 10 năm trông mâu thuẫn với mốc 5 năm nhưng là ngoại lệ hợp lệ của pháp luật chuyên ngành.",
    expected:
      "Tối thiểu 10 năm kể từ ngày đóng tài khoản hoặc hoàn thành giao dịch. Đây là thời hạn chuyên ngành phòng, chống rửa tiền và được áp dụng thay cho thời hạn lưu dữ liệu cá nhân chung 5 năm.",
  },
  {
    id: "active-security-policy",
    title: "Văn bản hiện hành",
    category: "Versioning",
    question: "Quy chế An toàn thông tin nào đang có hiệu lực?",
    painPoint: "Cần theo chuỗi thay thế nhưng vẫn bảo toàn ngoại lệ của phụ lục còn hiệu lực.",
    expected:
      "Quy chế ATTT phiên bản 2.0 ban hành kèm QĐ342/2024/QĐ-DDB đang có hiệu lực từ 01/09/2024. QĐ215/2022 đã bị thay thế, riêng Phụ lục 02 tiếp tục có hiệu lực đến khi có danh mục mới.",
  },
];
