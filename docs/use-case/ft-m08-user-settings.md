# UC-MOBILE-08 — Tùy chỉnh trải nghiệm người dùng

| Use case number: | UC-MOBILE-08 |  |
| :---- | :---- | :---- |
| **Use case name:** | Tùy chỉnh trải nghiệm người dùng |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Cho phép người dùng tự chọn ngôn ngữ giao diện/nghe, bật tắt tự phát theo vị trí, cấu hình âm lượng và giao diện sáng/tối; duy trì lựa chọn qua các lần sử dụng không cần tài khoản. **Traceability:** Epic: EP-M04 — Offline Content and Preferences; Feature / Requirement: FT-M08 / FR-M06; User Stories: US-M16, US-M17, US-M18; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách mở màn hình Settings. |  |
|  |  | 2\. Ứng dụng đọc thiết lập đã lưu; nếu lần đầu, sử dụng cấu hình mặc định đã xác định cho client. |
|  | 3\. Người dùng chọn ngôn ngữ giao diện; ứng dụng cập nhật chuỗi UI nếu bản dịch có sẵn. |  |
|  | 4\. Người dùng chọn ngôn ngữ thuyết minh; FT-M03 sử dụng lựa chọn này cho lần phát tiếp theo; FT-M07 lọc package offline theo ngôn ngữ yêu cầu. |  |
|  | 5\. Người dùng bật/tắt auto narration; FT-M05 và FT-M06 đăng ký/dừng cơ chế theo dõi theo quyền thực tế. |  |
|  | 6\. Người dùng chỉnh âm lượng (trong giới hạn API player/OS) và chọn giao diện sáng/tối. |  |
|  |  | 7\. Ứng dụng xác thực các lựa chọn, ghi bền vững và hiển thị thiết lập cập nhật khi mở lại. |
| **Alternative Paths:** | **A1 — Ngôn ngữ UI chưa có bản dịch:** Thông báo hoặc sử dụng ngôn ngữ giao diện mặc định; không đồng nhất với fallback narration online.<br><br>**A2 — Ngôn ngữ nghe không có bản PUBLISHED online:** FT-M03 áp dụng fallback tiếng Anh theo BR-05; giữ lựa chọn người dùng.<br><br>**A3 — Không có package offline theo ngôn ngữ mới:** Thông báo cần tải đúng package; không tự xem package ngôn ngữ khác là hợp lệ. |  |
| **Exception Paths:** | **E1 — Ngôn ngữ UI chưa có bản dịch:** Thông báo hoặc sử dụng ngôn ngữ giao diện mặc định; không đồng nhất với fallback narration online.<br><br>**E2 — Ngôn ngữ nghe không có bản PUBLISHED online:** FT-M03 áp dụng fallback tiếng Anh theo BR-05; giữ lựa chọn người dùng.<br><br>**E3 — Không có package offline theo ngôn ngữ mới:** Thông báo cần tải đúng package; không tự xem package ngôn ngữ khác là hợp lệ.<br><br>**E4 — Bật auto nhưng chưa cấp quyền GPS/background:** Yêu cầu quyền cần thiết; nếu từ chối, không tự trigger.<br><br>**E5 — Lỗi ghi thiết lập local:** Hiển thị lỗi; không tuyên bố đã lưu vĩnh viễn.<br><br>**E6 — Thay đổi âm lượng bị OS giới hạn:** Tuân thủ giới hạn nền tảng; không vượt chính sách thiết bị. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng truy cập Settings và thay đổi tùy chọn. |  |
| **Assumptions:** | Thiết lập người dùng được lưu cục bộ, không yêu cầu tài khoản Tourist. |  |
| **Preconditions:** | Ứng dụng đã khởi chạy và có khả năng đọc/ghi local settings. |  |
| **Post Conditions:** | Lựa chọn hợp lệ được lưu bền vững trong `Local_App_State` hoặc kho thiết lập local tương đương; các module liên quan cập nhật hành vi. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**BR-01, BR-05–06, BR-12:** Tourist không cần tài khoản; lựa chọn ngôn ngữ không làm thay đổi quy tắc fallback; auto chỉ chạy khi bật và đủ quyền.<br><br>**AC-M08-01:** US-M16 ngôn ngữ giao diện và thuyết minh là hai tùy chọn độc lập.<br><br>**AC-M08-02:** US-M17 tắt auto ngăn kích hoạt mới và chấm dứt theo dõi không còn cần thiết.<br><br>**AC-M08-03:** US-M18 chỉnh âm thanh, theme và duy trì trạng thái sau restart khi lưu thành công.<br><br>**AC-M08-04:** Thay ngôn ngữ không tự chuyển phiên phát đang chạy hoặc package offline hiện tại sang nội dung khác khi chưa xác minh.

## Activity Diagram

Activity Diagram

```mermaid
flowchart TD
    A([Mở Settings]) --> B[Đọc thiết lập local]
    B --> C[Hiển thị tùy chọn]
    C --> D{Người dùng thay đổi gì?}
    D -- Ngôn ngữ --> E[Kiểm tra ngôn ngữ khả dụng]
    D -- Auto narration --> F{Bật?}
    F -- Có --> G[Kiểm tra quyền vị trí] --> H[Thông báo trạng thái auto]
    F -- Không --> I[Dừng auto detection]
    D -- Âm thanh/giao diện --> J[Áp dụng tùy chọn hợp lệ]
    E --> K[Lưu thiết lập local]
    H --> K
    I --> K
    J --> K
    K --> L{Lưu thành công?}
    L -- Có --> M[Hiển thị trạng thái mới] --> N([Kết thúc])
    L -- Không --> O[Thông báo lưu thất bại]
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Languages` (danh mục ngôn ngữ khả dụng), `Local_App_State`; không yêu cầu `Manager_Users` cho du khách.
- **Liên kết:** Dependencies / Notes
- Liên kết FT-M03, FT-M05, FT-M06, FT-M07; không yêu cầu Tourist login.
- Danh sách giá trị mặc định UI/audio và chính sách quyền nền cần được xác nhận khi đặc tả ứng dụng cụ thể.
- Nguồn: PRD.md FR-M06, US-M16–18, BR-01/05–06/12; `docs/database-design.md` §2.5.3, §3.2.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
