# UC-MOBILE-01 — Khám phá điểm tham quan (POI)

| Use case number: | UC-MOBILE-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Khám phá điểm tham quan (POI) |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Cho phép du khách xem, tìm kiếm, mở chi tiết và khám phá POI lân cận mà không cần đăng nhập. Chức năng khám phá POI lân cận sử dụng khoảng cách đến vị trí thiết bị; bán kính khám phá **khác** `trigger_radius_meter` dành cho Geofence. **Traceability:** Epic: EP-M01 — POI Discovery and Interactive Map; Feature: FT-M01 — Point of Interest Discovery; Requirement: FR-M01; User Stories: US-M01, US-M02, US-M03 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách mở màn hình khám phá. |  |
|  |  | 2\. Ứng dụng kiểm tra kết nối và nguồn dữ liệu POI hợp lệ; ưu tiên dữ liệu công khai mới từ backend khi online, dùng snapshot đã tải khi offline. **A1, E1, E2** |
|  |  | 3\. Ứng dụng lấy danh sách POI có `poi_status = ACTIVE` từ API công khai, kèm metadata khu vực/danh mục. |
|  | 4\. Du khách nhập từ khóa hoặc chọn bộ lọc; danh sách cập nhật theo tiêu chí. |  **A3** |
|  | 5\. Du khách chọn một POI; ứng dụng hiển thị tên, ảnh, vị trí/địa chỉ, khu vực, danh mục và nội dung thuyết minh khả dụng. |  **E4** |
|  | 6\. Khi chọn “gần tôi”, ứng dụng xin quyền vị trí nếu chưa có, đọc mẫu vị trí đủ tin cậy và tính khoảng cách theo tọa độ POI. |  **A2, E3** |
|  |  | 7\. Danh sách được sắp xếp theo khoảng cách nếu tính được; người dùng có thể mở bản đồ hoặc phát thuyết minh. |
| **Alternative Paths:** | **A1 — Mất mạng nhưng có package READY:** Đọc `Local_POIs` trong package READY; chỉ hiển thị dữ liệu thuộc snapshot, thông báo có thể cũ.<br><br>**A2 — Không cho phép vị trí:** Vẫn cho xem/tìm kiếm POI, không hiện khoảng cách/gần tôi.<br><br>**A3 — Không có kết quả:** Hiển thị empty state và cho điều chỉnh tìm kiếm/bộ lọc. |  |
| **Exception Paths:** | **E1 — API lỗi/timeout dù có Internet:** Thử dùng snapshot local READY; nếu không có, hiển thị lỗi và thao tác retry.<br><br>**E2 — Mất mạng và không có package READY:** Không thể tải danh mục; báo cần kết nối hoặc tải gói trước.<br><br>**E3 — Mẫu GPS stale/accuracy kém hoặc dịch vụ định vị tắt:** Không dùng vị trí để xếp gần tôi, giữ danh sách thường.<br><br>**E4 — Chi tiết POI online đã INACTIVE/không còn tồn tại:** Không mở dữ liệu online đã bị gỡ, cập nhật danh sách; khi offline chỉ tin snapshot sẵn có cho đến lần đồng bộ. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng muốn xem, tìm kiếm hoặc mở POI. |  |
| **Assumptions:** | Chỉ POI ACTIVE được công bố online; dữ liệu offline là snapshot đã được tải và kiểm chứng. |  |
| **Preconditions:** | Ứng dụng được mở; dữ liệu POI công khai truy cập được qua mạng hoặc có snapshot offline hợp lệ. |  |
| **Post Conditions:** | Hiển thị danh sách/chi tiết POI chính xác, người dùng có thể chuyển sang Map hoặc Narration Player; không thay đổi dữ liệu máy chủ. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Lưu ý:** Kiểm tra kết nối Internet không thay cho kiểm tra kết quả HTTP; API vẫn có thể timeout/5xx khi thiết bị online. Không dùng bán kính Geofence để giới hạn danh sách khám phá.


**BR-01, BR-02:** Truy vấn công khai không yêu cầu đăng nhập và chỉ trả POI ACTIVE.<br><br>**AC-M01-01:** US-M01 hiển thị danh sách POI ACTIVE; POI INACTIVE trên server không xuất hiện online.<br><br>**AC-M01-02:** US-M02 tìm kiếm/lọc và mở đúng chi tiết POI được chọn.<br><br>**AC-M01-03:** US-M03 chỉ hiển thị khoảng cách khi mẫu vị trí hợp lệ; từ chối quyền vị trí không chặn danh sách.<br><br>**AC-M01-04:** Không dùng `trigger_radius_meter` làm bán kính lọc mặc định của khám phá lân cận.<br><br>**AC-M01-05:** Offline chỉ dùng dữ liệu của package local đã commit READY, không giả định có toàn bộ danh mục POI.

## Activity Diagram

```mermaid
flowchart TD
 A([Mở POI Discovery]) --> B{Internet khả dụng?}
 B -- Có --> C[Gọi API danh sách POI ACTIVE]
 C --> D{API phản hồi hợp lệ?}
 D -- Có --> F[Hiển thị danh sách POI]
 D -- Không --> E{Local package READY?}
 B -- Không --> E
 E -- Có --> G[Đọc snapshot Local_POIs; cảnh báo có thể cũ] --> F
 E -- Không --> X[Thông báo lỗi mạng/dữ liệu và Retry]
 F --> H{Thao tác}
 H -- Tìm kiếm/lọc --> I[Lọc; hiển thị kết quả hoặc empty state] --> F
 H -- Gần tôi --> J{Quyền GPS và sample tin cậy?}
 J -- Không --> K[Giữ danh sách thường; báo giới hạn] --> F
 J -- Có --> L[Tính distance từ tọa độ, không dùng trigger radius] --> F
 H -- Chọn POI --> M{POI hợp lệ theo nguồn hiện tại?}
 M -- Không --> N[Báo POI không khả dụng] --> F
 M -- Có --> O[Hiển thị chi tiết POI] --> P([Kết thúc])
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Point_Of_Interests`, `Regions`, `Poi_Categories`, `Poi_Category_Mapping`; dữ liệu local tương ứng khi offline.
- **Liên kết:** Liên kết FT-M02 (bản đồ), FT-M03 (phát thuyết minh), FT-M07 (snapshot offline).
- **Phạm vi thiết kế mục tiêu:** phần hiển thị gần tôi và đồng bộ dữ liệu local cần được đối chiếu khi tích hợp mobile; sơ đồ không khẳng định đã triển khai.
- Nguồn: PRD.md §2.3.1, §3.3–3.4; `docs/database-design.md` §2.2, §3–4.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
