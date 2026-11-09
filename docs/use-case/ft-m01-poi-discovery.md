# UC-MOBILE-01 — Khám phá điểm tham quan (POI)

| Use case number: | UC-MOBILE-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Khám phá điểm tham quan (POI) |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Cho phép du khách xem, tìm kiếm, mở chi tiết và khám phá POI lân cận mà không cần đăng nhập. Chức năng khám phá POI lân cận sử dụng khoảng cách đến vị trí thiết bị; bán kính khám phá **khác** `trigger_radius_meter` dành cho Geofence. **Traceability:** Epic: EP-M01 — POI Discovery and Interactive Map; Feature: FT-M01 — Point of Interest Discovery; Requirement: FR-M01; User Stories: US-M01, US-M02, US-M03 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách mở màn hình khám phá. |  |
|  |  | 2\. Ứng dụng kiểm tra kết nối và nguồn dữ liệu POI hợp lệ; ưu tiên dữ liệu công khai mới từ backend khi online, dùng snapshot đã tải khi offline. |
|  |  | 3\. Ứng dụng lấy danh sách POI có `poi_status = ACTIVE` từ API công khai, kèm metadata khu vực/danh mục. |
|  | 4\. Du khách nhập từ khóa hoặc chọn bộ lọc; danh sách cập nhật theo tiêu chí. |  |
|  | 5\. Du khách chọn một POI; ứng dụng hiển thị tên, ảnh, vị trí/địa chỉ, khu vực, danh mục và nội dung thuyết minh khả dụng. |  |
|  | 6\. Khi chọn “gần tôi”, ứng dụng xin quyền vị trí nếu chưa có, đọc mẫu vị trí đủ tin cậy và tính khoảng cách theo tọa độ POI. |  |
|  |  | 7\. Danh sách được sắp xếp theo khoảng cách nếu tính được; người dùng có thể mở bản đồ hoặc phát thuyết minh. |
| **Alternative Paths:** | **A1 — Từ chối quyền vị trí/GPS tắt:** Vẫn hiển thị và tìm kiếm danh sách POI; ẩn khoảng cách, không ép buộc cấp quyền.<br><br>**A2 — Kết nối lỗi, có package READY:** Hiển thị POI thuộc snapshot local đã tải; thông báo dữ liệu có thể cũ.<br><br>**A3 — POI bị chuyển INACTIVE:** Không trả về trong truy vấn online mới; snapshot offline cũ có thể còn cho đến khi cập nhật. |  |
| **Exception Paths:** | **E1 — Kết nối lỗi, không có dữ liệu local:** Thông báo không tải được danh sách và cho phép thử lại.<br><br>**E2 — Tìm kiếm không có kết quả:** Hiển thị trạng thái rỗng và tùy chọn xóa bộ lọc.<br><br>**E3 — Vị trí quá cũ hoặc độ chính xác kém:** Không sử dụng để xếp POI “gần tôi”; chuyển sang danh sách thông thường. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng muốn xem, tìm kiếm hoặc mở POI. |  |
| **Assumptions:** | Chỉ POI ACTIVE được công bố online; dữ liệu offline là snapshot đã được tải và kiểm chứng. |  |
| **Preconditions:** | Ứng dụng được mở; dữ liệu POI công khai truy cập được qua mạng hoặc có snapshot offline hợp lệ. |  |
| **Post Conditions:** | Hiển thị danh sách/chi tiết POI chính xác, người dùng có thể chuyển sang Map hoặc Narration Player; không thay đổi dữ liệu máy chủ. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**BR-01, BR-02:** Truy vấn công khai không yêu cầu đăng nhập và chỉ trả POI ACTIVE.<br><br>**AC-M01-01:** US-M01 hiển thị danh sách POI ACTIVE; POI INACTIVE trên server không xuất hiện online.<br><br>**AC-M01-02:** US-M02 tìm kiếm/lọc và mở đúng chi tiết POI được chọn.<br><br>**AC-M01-03:** US-M03 chỉ hiển thị khoảng cách khi mẫu vị trí hợp lệ; từ chối quyền vị trí không chặn danh sách.<br><br>**AC-M01-04:** Không dùng `trigger_radius_meter` làm bán kính lọc mặc định của khám phá lân cận.<br><br>**AC-M01-05:** Offline chỉ dùng dữ liệu của package local đã commit READY, không giả định có toàn bộ danh mục POI.

## Activity Diagram

```mermaid
flowchart TD
    A([Mở khám phá POI]) --> B{Có kết nối mạng?}
    B -- Có --> C[Lấy danh sách POI ACTIVE từ API]
    B -- Không --> D{Có dữ liệu local READY?}
    D -- Có --> E[Đọc snapshot POI trên thiết bị]
    D -- Không --> X[Thông báo lỗi và cho thử lại]
    C --> F[Hiển thị danh sách]
    E --> F
    F --> G{Tác vụ người dùng}
    G -- Tìm kiếm/lọc --> H[Áp dụng bộ lọc] --> F
    G -- Gần tôi --> I{Vị trí hợp lệ?}
    I -- Có --> J[Tính khoảng cách và sắp xếp] --> F
    I -- Không --> K[Thông báo, giữ danh sách] --> F
    G -- Chọn POI --> L[Hiển thị chi tiết POI] --> M([Kết thúc])
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Point_Of_Interests`, `Regions`, `Poi_Categories`, `Poi_Category_Mapping`; dữ liệu local tương ứng khi offline.
- **Liên kết:** Liên kết FT-M02 (bản đồ), FT-M03 (phát thuyết minh), FT-M07 (snapshot offline).
- **Phạm vi thiết kế mục tiêu:** phần hiển thị gần tôi và đồng bộ dữ liệu local cần được đối chiếu khi tích hợp mobile; sơ đồ không khẳng định đã triển khai.
- Nguồn: PRD.md §2.3.1, §3.3–3.4; `docs/database-design.md` §2.2, §3–4.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
