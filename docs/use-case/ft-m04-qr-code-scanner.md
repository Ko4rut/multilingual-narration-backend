# UC-MOBILE-04 — Quét QR Code để truy cập điểm tham quan

| Use case number: | UC-MOBILE-04 |  |
| :---- | :---- | :---- |
| **Use case name:** | Quét QR Code để truy cập điểm tham quan |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Định danh POI bằng QR Code và mở nhanh thông tin/thuyết minh, không phụ thuộc GPS; QR phải tham chiếu POI hợp lệ. **Traceability:** Epic: EP-M02 — Narration Playback and QR Access; Feature / Requirement: FT-M04 / FR-M04; User Story: US-M09; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách chọn “Quét QR”. |  |
|  |  | 2\. Ứng dụng kiểm tra và yêu cầu quyền camera khi cần. |
|  |  | 3\. Camera đọc QR; ứng dụng phân tích giá trị và kiểm tra cấu trúc/định dạng cho phép. |
|  |  | 4\. Ứng dụng đối chiếu QR với POI: online qua nguồn công khai hoặc offline qua dữ liệu POI đã có. |
|  |  | 5\. Kiểm tra trạng thái POI được phép truy cập tại nguồn đang dùng. |
|  |  | 6\. Điều hướng đến màn hình chi tiết POI; người dùng có thể chủ động chọn phát narration. |
|  |  | 7\. Khi yêu cầu phát, FT-M03 chọn audio/ngôn ngữ và xử lý offline/online theo quy tắc tương ứng. |
| **Alternative Paths:** | **A1 — Từ chối quyền camera:** Hiển thị hướng dẫn cấp quyền, cho trở về khám phá POI thủ công.<br><br>**A2 — POI không tồn tại/INACTIVE trên server:** Không mở nội dung công khai; hiển thị thông báo phù hợp.<br><br>**A3 — Offline nhưng QR không có trong snapshot READY:** Thông báo cần có dữ liệu hoặc kết nối để mở POI. |  |
| **Exception Paths:** | **E1 — Từ chối quyền camera:** Hiển thị hướng dẫn cấp quyền, cho trở về khám phá POI thủ công.<br><br>**E2 — QR sai định dạng/không thuộc hệ thống:** Thông báo QR không hợp lệ, tiếp tục quét.<br><br>**E3 — POI không tồn tại/INACTIVE trên server:** Không mở nội dung công khai; hiển thị thông báo phù hợp.<br><br>**E4 — Offline nhưng QR không có trong snapshot READY:** Thông báo cần có dữ liệu hoặc kết nối để mở POI.<br><br>**E5 — QR đọc lặp liên tục:** Khóa xử lý trong thời gian điều hướng để không mở nhiều lần.<br><br>**E6 — GPS không được cấp quyền:** Không ảnh hưởng khả năng quét QR. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng chọn chức năng quét QR Code. |  |
| **Assumptions:** | Mã QR nhận diện POI theo dữ liệu đã công bố; không phụ thuộc GPS. |  |
| **Preconditions:** | Ứng dụng có màn hình quét và có thể yêu cầu quyền camera; có nguồn tra cứu POI online hoặc snapshot offline đã tải. |  |
| **Post Conditions:** | QR hợp lệ điều hướng đúng `poi_id`; QR không hợp lệ không tạo thao tác phát. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**BR-01, BR-02:** QR không thay thế quy tắc public POI ACTIVE; Tourist không cần đăng nhập.<br><br>**AC-M04-01:** US-M09 quét QR hợp lệ mở đúng chi tiết POI tương ứng.<br><br>**AC-M04-02:** QR không hợp lệ, camera bị từ chối, POI không có sẵn đều có thông báo rõ.<br><br>**AC-M04-03:** Quy trình QR thực hiện được mà không yêu cầu GPS.<br><br>**AC-M04-04:** Khi offline, chỉ truy cập tài nguyên có trong package READY và đã xác minh trước khi phát.

## Activity Diagram

Activity Diagram

```mermaid
flowchart TD
    A([Chọn quét QR]) --> B{Có quyền camera?}
    B -- Không --> C[Yêu cầu quyền]
    C --> D{Được cấp?}
    D -- Không --> X[Thông báo và cho chọn POI thủ công]
    B -- Có --> E[Quét QR]
    D -- Có --> E
    E --> F{QR đúng định dạng?}
    F -- Không --> G[Thông báo mã không hợp lệ] --> E
    F -- Có --> H[Tra cứu POI từ online hoặc local]
    H --> I{POI được phép truy cập?}
    I -- Không --> J[Thông báo không khả dụng]
    I -- Có --> K[Điều hướng tới POI Detail]
    K --> L([Kết thúc])
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Point_Of_Interests.poi_qr_code` là giá trị duy nhất; `poi_status`; `Local_POIs` nếu dùng ngoại tuyến.
- **Liên kết:** Dependencies / Notes
- FT-M01 cung cấp chi tiết; FT-M03 phát audio; FT-M07 cung cấp snapshot.
- Không suy diễn rằng quét QR tự động phát trong mọi tình huống: theo US-M09, luồng chính điều hướng đến nội dung và người dùng có thể yêu cầu phát.
- Nguồn: PRD.md FR-M04, US-M09, BR-01/02/14; `docs/database-design.md` §2.2.1, §3.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
