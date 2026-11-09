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
| **Alternative Paths:** | **A1 — Thay đổi thiết lập khi offline:** Dùng `Local_App_State`, lưu lựa chọn trên thiết bị mà không phụ thuộc API.<br><br>**A2 — Chọn ngôn ngữ nghe chưa có audio online:** Giữ preference, khi nghe online fallback tiếng Anh nếu có bản PUBLISHED hợp lệ; offline chỉ theo package đã tải.<br><br>**A3 — Tắt auto narration:** Dừng tracking không cần thiết, không tự kích hoạt audio mới; QR/manual vẫn hoạt động. |  |
| **Exception Paths:** | **E1 — Không có ngôn ngữ giao diện tương ứng:** Giữ UI fallback/default đã hỗ trợ; không đồng nhất fallback UI với English audio.<br><br>**E2 — Bật auto nhưng GPS/background permission không được cấp:** Không start tracking trái quyền; hướng dẫn cấp quyền và giữ thao tác thủ công.<br><br>**E3 — Local storage ghi thất bại hoặc bị reset:** Thông báo không lưu được; khôi phục giá trị đã lưu hoặc default, không nói thay đổi đã được giữ sau restart.<br><br>**E4 — Đổi ngôn ngữ nhưng package READY không đúng ngôn ngữ:** Không phát asset sai ngôn ngữ; báo cần tải package mới khi có mạng.<br><br>**E5 — Thiết bị hạn chế âm lượng/phát nền:** Tuân thủ OS; không bảo đảm chỉnh âm lượng ngoài quyền ứng dụng. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng truy cập Settings và thay đổi tùy chọn. |  |
| **Assumptions:** | Thiết lập người dùng được lưu cục bộ, không yêu cầu tài khoản Tourist. |  |
| **Preconditions:** | Ứng dụng đã khởi chạy và có khả năng đọc/ghi local settings. |  |
| **Post Conditions:** | Lựa chọn hợp lệ được lưu bền vững trong `Local_App_State` hoặc kho thiết lập local tương đương; các module liên quan cập nhật hành vi. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Kết nối:** Thay đổi Settings cơ bản phải hoạt động offline; Internet chỉ cần khi truy vấn danh mục mới hoặc tải package khác ngôn ngữ. Không coi permission của người dùng là đã được cấp chỉ vì chọn bật auto.


**BR-01, BR-05–06, BR-12:** Tourist không cần tài khoản; lựa chọn ngôn ngữ không làm thay đổi quy tắc fallback; auto chỉ chạy khi bật và đủ quyền.<br><br>**AC-M08-01:** US-M16 ngôn ngữ giao diện và thuyết minh là hai tùy chọn độc lập.<br><br>**AC-M08-02:** US-M17 tắt auto ngăn kích hoạt mới và chấm dứt theo dõi không còn cần thiết.<br><br>**AC-M08-03:** US-M18 chỉnh âm thanh, theme và duy trì trạng thái sau restart khi lưu thành công.<br><br>**AC-M08-04:** Thay ngôn ngữ không tự chuyển phiên phát đang chạy hoặc package offline hiện tại sang nội dung khác khi chưa xác minh.

## Activity Diagram

```mermaid
flowchart TD
 A([Mở Settings]) --> B[Đọc Local_App_State hoặc defaults]
 B --> C{Tùy chọn thay đổi}
 C -- Ngôn ngữ UI --> D{Có bản dịch UI?}
 D -- Không --> E[Giữ UI fallback] --> J[Lưu lựa chọn hợp lệ]
 D -- Có --> J
 C -- Ngôn ngữ narration --> F[Chọn ngôn ngữ; không tự đổi audio đang phát]
 F --> G{Offline package đúng ngôn ngữ READY?}
 G -- Không --> H[Thông báo cần tải package khi online] --> J
 G -- Có --> J
 C -- Auto narration --> I{Bật auto?}
 I -- Không --> K[Dừng location tracking] --> J
 I -- Có --> L{Có quyền vị trí cần thiết?}
 L -- Không --> M[Hướng dẫn cấp quyền; không theo dõi] --> J
 L -- Có --> N[Cho FT-M05/06 theo dõi đúng quyền] --> J
 C -- Âm thanh/Theme --> O[Áp dụng trong giới hạn OS] --> J
 J --> P{Ghi local thành công?}
 P -- Có --> Q[Khôi phục thiết lập ở lần mở sau] --> R([Kết thúc])
 P -- Không --> S[Báo lỗi; giữ giá trị đã lưu trước đó]
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Languages` (danh mục ngôn ngữ khả dụng), `Local_App_State`; không yêu cầu `Manager_Users` cho du khách.
- **Liên kết:** Dependencies / Notes
- Liên kết FT-M03, FT-M05, FT-M06, FT-M07; không yêu cầu Tourist login.
- Danh sách giá trị mặc định UI/audio và chính sách quyền nền cần được xác nhận khi đặc tả ứng dụng cụ thể.
- Nguồn: PRD.md FR-M06, US-M16–18, BR-01/05–06/12; `docs/database-design.md` §2.5.3, §3.2.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
