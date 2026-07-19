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
    id: "demo-1-time-aware",
    title: "Demo 1 · Time-aware hiệu lực",
    category: "Hiệu lực theo thời gian",
    question: "Thời gian khóa phiên làm việc?",
    painPoint:
      "Một khái niệm có 5 nguồn với 4 trạng thái hiệu lực khác nhau: bản hiện hành, bản đã bị thay thế, dự thảo chưa hiệu lực và đề xuất trong biên bản họp chưa thành quyết định.",
    expected:
      "15 phút với máy trạm trong mạng nội bộ (QĐ342 — hiện hành) và 30 phút với thiết bị làm việc từ xa (QĐ401). Đề xuất nâng lên 20 phút tại họp UB ATTT quý II/2025 chưa thành quyết định nên 15 phút áp dụng nguyên trạng; dự thảo ATTT v3.0 (10 phút) chưa có hiệu lực; QĐ215 (15 phút) đã bị thay thế.",
  },
  {
    id: "demo-2-multi-facet",
    title: "Demo 2 · Multi-facet",
    category: "Bao phủ đa khía cạnh",
    question:
      "Một nhân viên DDB làm việc từ xa dùng công cụ AI nội bộ để phân tích hồ sơ KYC khách hàng: phiên làm việc từ xa tự động khóa sau bao nhiêu phút; dùng dữ liệu khách hàng huấn luyện AI cần điều kiện gì; hồ sơ KYC lưu trữ bao lâu; rò rỉ dữ liệu cá nhân phải báo cáo NHNN trong bao lâu; và mức phạt chuyển dữ liệu cá nhân ra nước ngoài trái phép?",
    painPoint:
      "5 khía cạnh trải trên 4 mảng nghiệp vụ và hơn 6 văn bản — vượt sức chứa một lần top-k; RAG thường dễ thay đáp án đúng bằng giá trị na ná từ văn bản sai.",
    expected:
      "Khóa phiên từ xa 30 phút (QĐ401); huấn luyện AI cần sự đồng ý riêng (QĐ455) hoặc dữ liệu đã ẩn danh, lưu tối đa 24 tháng (QĐ502); hồ sơ KYC lưu 10 năm (QĐ480/TT20 — thay cho 5 năm của QĐ455 vì pháp luật chuyên ngành); báo cáo NHNN sự cố nghiêm trọng trong 04 giờ (TT09, phân biệt với 72 giờ thông báo chủ thể dữ liệu theo NĐ88); phạt 200–300 triệu đồng (NĐ88 Đ14).",
  },
  {
    id: "demo-3-reference-chain",
    title: "Demo 3 · Chuỗi dẫn chiếu",
    category: "Truy vết đa văn bản",
    question:
      "Hệ thống Core Banking gặp thảm họa phải khôi phục trong bao lâu, và căn cứ nào xác định nó là hệ thống trọng yếu?",
    painPoint:
      "Con số nằm ở văn bản đầu chuỗi nhưng vế \"căn cứ\" phải đi qua hai văn bản nữa mới tới danh mục gốc — RAG thường thấy tên văn bản được dẫn chiếu mà không có nội dung để đi tiếp.",
    expected:
      "RTO tối đa 02 giờ, RPO 15 phút cho hệ thống trọng yếu (QĐ356). Căn cứ xác định trọng yếu: QĐ173/2023 (tiêu chí phân loại, trỏ danh mục) dẫn về Phụ lục 02 QĐ215/2022 (Core Banking T24 — Cấp độ 4), đối chiếu TT09/2024 (hệ thống Cấp độ 3 trở lên là trọng yếu).",
  },
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
