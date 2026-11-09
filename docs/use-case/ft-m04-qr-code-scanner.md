# UC-MOBILE-04 — Quét QR Code để truy cập điểm tham quan

| Use case number: | UC-MOBILE-04 |  |
| :---- | :---- | :---- |
| **Use case name:** | Quét QR Code để truy cập điểm tham quan |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Định danh POI bằng QR Code và mở nhanh thông tin/thuyết minh, không phụ thuộc GPS; QR phải tham chiếu POI hợp lệ. **Traceability:** Epic: EP-M02 — Narration Playback and QR Access; Feature / Requirement: FT-M04 / FR-M04; User Story: US-M09; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách mở màn hình QR Scanner. |  |
|  |  | 2\. Ứng dụng xin quyền camera; nếu không được cấp, hướng dẫn tìm POI thủ công. **E1** |
|  |  | 3\. Đọc QR, validate định dạng và chặn xử lý lặp. **E2, E6** |
|  |  | 4\. Khi online API phản hồi: kiểm tra POI ACTIVE; không dùng snapshot cũ để vượt quyết định INACTIVE của server. **A1, E5** |
|  |  | 5\. Khi offline hoặc API không phản hồi: tìm poi_qr_code trong Local_POIs thuộc package READY. **A2, E3, E4** |
|  |  | 6\. Mở đúng POI Detail, không cần GPS. **A3** |
|  | 7\. Du khách bấm phát thuyết minh. |  |
|  |  | 8\. Gọi FT-M03 với trigger_type QR_CODE; chỉ phát audio VERIFIED offline hoặc PUBLISHED online. |
| **Alternative Paths:** | **A1 — QR hợp lệ khi online:** Tra POI ACTIVE từ backend, mở detail; yêu cầu nghe chuyển tới FT-M03.<br><br>**A2 — QR hợp lệ khi offline, local package READY có POI:** Tra `poi_qr_code` trong snapshot local, mở detail; nghe nếu asset VERIFIED cùng ngôn ngữ có sẵn.<br><br>**A3 — Không cấp GPS:** QR vẫn hoạt động vì không yêu cầu GPS. |  |
| **Exception Paths:** | **E1 — Không cấp camera hoặc camera không sẵn sàng:** Thông báo quyền/thiết bị, cung cấp cách tìm POI thủ công.<br><br>**E2 — QR sai định dạng, URL lạ hoặc không map POI:** Không điều hướng; báo QR không hợp lệ và cho quét lại.<br><br>**E3 — Online API timeout/5xx hoặc mất mạng trong tra cứu:** Thử local package READY; nếu POI không có, báo cần kết nối.<br><br>**E4 — Offline không có package READY hoặc QR không thuộc snapshot:** Không mở POI/không phát audio; giải thích cần tải dữ liệu khi online.<br><br>**E5 — POI INACTIVE hoặc đã bị xóa trên server:** Từ chối điều hướng với dữ liệu online; snapshot offline chỉ biết trạng thái tại lần tải trước.<br><br>**E6 — Quét cùng mã nhiều lần liên tiếp:** Chặn xử lý trùng trước khi hoàn thành điều hướng. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng chọn chức năng quét QR Code. |  |
| **Assumptions:** | Mã QR nhận diện POI theo dữ liệu đã công bố; không phụ thuộc GPS. |  |
| **Preconditions:** | Ứng dụng có màn hình quét và có thể yêu cầu quyền camera; có nguồn tra cứu POI online hoặc snapshot offline đã tải. |  |
| **Post Conditions:** | QR hợp lệ điều hướng đúng `poi_id`; QR không hợp lệ không tạo thao tác phát. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Phân biệt trạng thái:** Khi backend xác nhận POI INACTIVE, không được fallback sang local chỉ để vượt hạn chế public; fallback local chỉ áp dụng khi không thể xác minh qua backend (offline hoặc lỗi truy vấn), với cảnh báo snapshot có thể cũ.


**BR-01, BR-02:** QR không thay thế quy tắc public POI ACTIVE; Tourist không cần đăng nhập.<br><br>**AC-M04-01:** US-M09 quét QR hợp lệ mở đúng chi tiết POI tương ứng.<br><br>**AC-M04-02:** QR không hợp lệ, camera bị từ chối, POI không có sẵn đều có thông báo rõ.<br><br>**AC-M04-03:** Quy trình QR thực hiện được mà không yêu cầu GPS.<br><br>**AC-M04-04:** Khi offline, chỉ truy cập tài nguyên có trong package READY và đã xác minh trước khi phát.

## Activity Diagram

```mermaid
flowchart TD
 A([Chọn quét QR]) --> B{Được cấp quyền camera?}
 B -- Không --> C[Xin quyền]
 C --> D{Người dùng cấp quyền?}
 D -- Không --> X[Báo thiếu quyền; cho tìm POI thủ công]
 B -- Có --> E[Đọc và giải mã QR]
 D -- Có --> E
 E --> F{QR thuộc định dạng hệ thống?}
 F -- Không --> G[Báo QR sai; quét lại] --> E
 F -- Có --> H{Có Internet và API phản hồi?}
 H -- Có --> I{POI tồn tại và ACTIVE?}
 I -- Không --> J[Báo POI không khả dụng; không bypass bằng local]
 I -- Có --> K[Chọn POI online]
 H -- Không --> L{Snapshot package READY chứa QR và POI hợp lệ?}
 L -- Không --> M[Báo cần kết nối hoặc tải package]
 L -- Có --> N[Chọn POI local; cảnh báo snapshot có thể cũ]
 K --> O[Điều hướng tới POI Detail]
 N --> O
 O --> P{Người dùng chọn nghe?}
 P -- Có --> Q[FT-M03 kiểm tra audio online hoặc local VERIFIED] --> Z([Kết thúc])
 P -- Không --> Z
```

## Traceability, Data and Implementation Notes

- **Dependencies:** FT-M01/03/07; QR offline cần Local_POIs.poi_qr_code.
- **Sources:** `PRD.md` (Feature/Requirement/User Story), `docs/database-design.md` (database contract), template `docs/usecase/authentication-session.md`.
- **Maturity:** Target behavior / đặc tả, không khẳng định tính năng đã chạy trên client và backend.

## Exception Acceptance Scenarios

- **AT-FT01**: Offline READY có poi_qr_code: tìm chính xác poi_id.
- **AT-FT02**: Online API xác nhận INACTIVE: không lấy snapshot cũ để bypass.
- **AT-FT03**: API timeout, không có snapshot: báo lỗi, không điều hướng.
- **AT-FT04**: Từ chối camera: gợi ý khám phá thủ công, không yêu cầu GPS.
