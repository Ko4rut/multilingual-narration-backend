# UC-MOBILE-06 — Theo dõi vị trí và thuyết minh ở chế độ nền

| Use case number: | UC-MOBILE-06 |  |
| :---- | :---- | :---- |
| **Use case name:** | Theo dõi vị trí và thuyết minh ở chế độ nền |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application, Location Services của Android/iOS |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Tiếp tục nhận diện sự kiện Geofence khi ứng dụng ở nền **trong phạm vi hệ điều hành cho phép**, đồng thời tôn trọng quyền vị trí, tùy chọn người dùng và trạng thái nguồn lực thiết bị. **Traceability:** Epic: EP-M03 — Automatic Geofence Narration; Feature / Requirement: FT-M06 / FR-M08; User Story: US-M12; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách bật tự phát và đưa ứng dụng xuống nền. |  |
|  |  | 2\. Kiểm tra quyền foreground/background và OS; thiếu quyền nền chỉ dùng foreground. **A1, E2** |
|  |  | 3\. Đăng ký location service nếu OS cho phép; không hứa reconcile đúng 5 giây khi app bị đình chỉ. **E1** |
|  |  | 4\. Khi có event hợp lệ, chuyển sang Geofence FT-M05; bỏ sample stale. **A2, E3** |
|  |  | 5\. Thực thi debounce, cooldown và pending/revalidate khi player bận. **A3, E6** |
|  |  | 6\. Chỉ dùng audio local VERIFIED hoặc online PUBLISHED khi OS cho phép playback. **E4, E5** |
|  | 7\. Du khách tắt auto hoặc thu hồi quyền. |  |
|  |  | 8\. Dừng theo dõi; QR/manual còn hoạt động; khi app restart khôi phục cooldown nhưng không phát từ vị trí stale. |
| **Alternative Paths:** | **A1 — Ứng dụng còn foreground hoặc chỉ có quyền foreground:** Tiếp tục Geofence ở foreground; không khởi động tracking nền trái quyền.<br><br>**A2 — Background event đến trong khi offline:** FT-M05 xử lý theo snapshot POI local và phát chỉ khi audio VERIFIED; không bắt buộc mạng để nhận event.<br><br>**A3 — Có event lúc narration đang phát:** Không phát chồng; áp dụng pending/revalidate của FT-M05. |  |
| **Exception Paths:** | **E1 — Hệ điều hành đình chỉ task, app kill hoặc hạn chế battery saver:** Không cam kết callback hay vòng lặp 5 giây; khi app trở lại, phục hồi state và xác minh location sample mới.<br><br>**E2 — Người dùng thu hồi background permission, tắt GPS hoặc tắt auto:** Dừng subscription/trigger tự động; giữ QR/manual hoạt động.<br><br>**E3 — Sample quá cũ hoặc sai số lớn:** Không chuyển thẳng tới player; bỏ sample hoặc chờ location cập nhật.<br><br>**E4 — OS không cho autoplay khi nền/khóa màn hình:** Không vượt giới hạn nền tảng; thực hiện hành vi phát/thông báo được OS cho phép, tránh tạo event phát thành công giả.<br><br>**E5 — Offline không có snapshot ACTIVE hoặc audio VERIFIED:** Không phát; có thể thông báo tải nội dung khi kết nối trở lại.<br><br>**E6 — App restart với cooldown/entry state còn hiệu lực:** Khôi phục `Local_POI_Trigger_State`, không kích hoạt trùng khi chưa có entry mới. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Ứng dụng chuyển sang background và hệ điều hành gửi sự kiện vị trí hợp lệ. |  |
| **Assumptions:** | OS có thể đình chỉ tác vụ nền; không cam kết callback chính xác theo thời gian thực. |  |
| **Preconditions:** | Auto narration được bật; ứng dụng đã giải thích và nhận quyền vị trí cần thiết; hệ điều hành cho phép cơ chế theo dõi nền tương ứng; có POI metadata. |  |
| **Post Conditions:** | Sự kiện vị trí được chuyển qua cùng Geofence Engine như foreground; không tạo audio trùng, không tiếp tục theo dõi khi không được phép. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Lưu ý nền tảng:** Safety reconcile 5 giây chỉ là quy tắc logic theo database design; Android/iOS không bảo đảm đánh thức dịch vụ chạy nền đúng nhịp. Offline cần snapshot POI và audio đã xác minh, không chỉ cần GPS.


**BR-12, BR-13:** Tính năng phụ thuộc auto setting, quyền location và cooldown.<br><br>**AC-M06-01:** US-M12 khi được cấp quyền nền và OS hỗ trợ, location event hợp lệ được xử lý qua FT-M05.<br><br>**AC-M06-02:** Không cấp hoặc thu hồi quyền nền thì ứng dụng không tiếp tục truy cập vị trí trái phép.<br><br>**AC-M06-03:** Không có GPS/background service vẫn cho phép quét QR và phát thủ công.<br><br>**AC-M06-04:** Sự kiện nền không được bỏ qua chính sách một audio/cooldown/độ tin cậy của mẫu.

## Activity Diagram

```mermaid
flowchart TD
 A([Chuyển ứng dụng xuống nền]) --> B{Auto narration đang bật?}
 B -- Không --> X[Không chạy location task]
 B -- Có --> C{Quyền background và OS cho phép?}
 C -- Không --> D[Dừng tracking nền; hướng dẫn quyền; QR/manual còn dùng]
 C -- Có --> E[Đăng ký background location task]
 E --> F{OS gửi location event?}
 F -- Không --> G[Chờ sự kiện hợp lệ; không cam kết timer 5 giây]
 F -- Có --> H{Mẫu tin cậy?}
 H -- Không --> G
 H -- Có --> I[FT-M05: debounce/cooldown, chọn tối đa một POI]
 I --> J{Đủ local audio VERIFIED hoặc API online khả dụng?}
 J -- Không --> K[Không phát; không ghi cooldown] --> G
 J -- Có --> L{OS cho phát audio và player rảnh?}
 L -- Không --> M[Giữ pending/tuân thủ giới hạn OS] --> G
 L -- Có --> N[FT-M03 bắt đầu phát; ghi event khi thành công] --> G
 E --> O{Quyền bị thu hồi hoặc app bị dừng?}
 O -- Có --> P[Dừng task/khôi phục state khi được mở lại]
```

## Traceability, Data and Implementation Notes

- **Dependencies:** FT-M05/03/08; OS có thể hạn chế location task.
- **Sources:** `PRD.md` (Feature/Requirement/User Story), `docs/database-design.md` (database contract), template `docs/usecase/authentication-session.md`.
- **Maturity:** Target behavior / đặc tả, không khẳng định tính năng đã chạy trên client và backend.

## Exception Acceptance Scenarios

- **AT-FT01**: Thu hồi quyền background: dừng tracking nền.
- **AT-FT02**: OS kill/resume: không phát từ location stale.
- **AT-FT03**: Không cam kết reconcile chính xác 5 giây ở background.
- **AT-FT04**: Không có verified audio offline: không ghi cooldown.
