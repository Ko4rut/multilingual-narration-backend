# UC-MOBILE-05 — Phát hiện vị trí và xử lý Geofence

| Use case number: | UC-MOBILE-05 |  |
| :---- | :---- | :---- |
| **Use case name:** | Phát hiện vị trí và xử lý Geofence |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application, Location Services của Android/iOS |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Nhận diện entry/exit của vùng POI và chỉ đề xuất tự phát khi sự kiện hợp lệ, không rung do GPS và không chồng audio. **Traceability:** Epic: EP-M03 — Automatic Geofence Narration; Feature / Requirement: FT-M05 / FR-M07; User Stories: US-M10, US-M11; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  |  | 1\. Location Engine nhận mẫu tọa độ, kiểm tra độ mới và độ chính xác. |
|  |  | 2\. Đối với POI có liên quan, tính khoảng cách và so với `trigger_radius_meter`. |
|  |  | 3\. Xử lý state machine `OUTSIDE → ENTER_DEBOUNCE → INSIDE_HANDLED → EXIT_DEBOUNCE → OUTSIDE`. |
|  |  | 4\. Khi chuyển từ OUTSIDE vào vùng, bắt đầu **debounce 3 giây**; nếu rời vùng trước khi đủ thời gian, hủy entry. |
|  |  | 5\. Sau khi ở trong vùng ổn định, kiểm tra **cooldown 5 phút** theo từng POI cho `AUTO_LOCATION`. Nếu đang cooldown, đánh dấu entry đã xử lý nhưng không phát. |
|  |  | 6\. Nếu nhiều POI cùng đủ điều kiện, chọn lần lượt theo tỷ lệ khoảng cách/bán kính thấp hơn, khoảng cách tuyệt đối thấp hơn, rồi `poi_id` để phân xử ổn định. |
|  |  | 7\. Nếu player đang bận, lưu pending candidate và **kiểm tra lại** khi audio hiện tại kết thúc; không tự cắt ngang. |
|  |  | 8\. Chỉ chuyển yêu cầu phát tới FT-M03 khi điều kiện còn hợp lệ; sau khi bắt đầu phát thành công, cập nhật `last_auto_triggered_at`. |
|  |  | 9\. Khi exit ổn định đủ debounce, trả POI về OUTSIDE để chờ entry mới. |
| **Alternative Paths:** | **A1 — Entry mới khi người dùng đã ở trong vùng lúc mở app:** Safety reconcile đọc sample mới, chuyển OUTSIDE → ENTER_DEBOUNCE; chỉ trigger sau đủ 3 giây.<br><br>**A2 — Nhiều Geofence cùng đủ điều kiện:** Xếp theo tỷ lệ distance/trigger_radius_meter thấp hơn, distance tuyệt đối thấp hơn, poi_id tăng dần; chọn tối đa một candidate.<br><br>**A3 — Đang phát narration khác:** Giữ pending candidate; khi player rảnh kiểm tra lại vị trí, entry, cooldown và audio trước khi phát; không tự cắt ngang.<br><br>**A4 — Có Internet nhưng thiếu local audio:** Truy vấn nội dung PUBLISHED/audio online; chỉ ghi cooldown khi phát thực sự thành công. |  |
| **Exception Paths:** | **E1 — GPS không được cấp quyền, bị tắt hoặc sample stale/accuracy kém:** Không auto-trigger; QR/manual vẫn dùng được.<br><br>**E2 — GPS dao động tại ranh giới:** Yêu cầu debounce 3 giây cho entry và exit; sự kiện không ổn định không thay state.<br><br>**E3 — Miss location callback:** Safety reconcile mỗi 5 giây khi runtime cho phép, đưa mẫu mới qua cùng state machine; không bypass debounce/cooldown.<br><br>**E4 — Re-entry trong cooldown 5 phút:** Đánh dấu INSIDE_HANDLED nhưng không phát; cooldown hết khi còn ở trong vùng không gây trigger mới.<br><br>**E5 — Mất mạng và không có local VERIFIED audio:** Không phát và không đặt last_auto_triggered_at.<br><br>**E6 — Audio load thất bại hoặc pending candidate đã ra khỏi vùng:** Không phát; không ghi cooldown; loại pending không còn hợp lệ.<br><br>**E7 — App restart khi cooldown chưa hết:** Đọc Local_POI_Trigger_State để tiếp tục cooldown theo POI. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Ứng dụng nhận mẫu vị trí/entry event khi chế độ tự thuyết minh đang bật. |  |
| **Assumptions:** | Location sample phải đủ mới/chính xác; thông số điều kiện vị trí theo database design. |  |
| **Preconditions:** | Người dùng đã bật auto narration; đã cấp quyền vị trí phù hợp; GPS đang bật; có mẫu vị trí đủ tin cậy và metadata POI ACTIVE; có thể truy cập audio hợp lệ. |  |
| **Post Conditions:** | Một entry được xử lý tối đa một lần; chỉ một candidate được chuyển đến FT-M03; cooldown chỉ ghi khi audio thực sự bắt đầu. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Không sử dụng `trigger_priority`.** Thứ tự chọn POI khi overlap là `(distance / trigger_radius_meter) ASC`, `distance ASC`, `poi_id ASC`; dùng mẫu vị trí tin cậy. Safety reconcile 5 giây không thể cam kết trong OS background bị hạn chế. State được lưu/khôi phục để không phát lại do restart.


**BR-12, BR-13:** Tôn trọng bật/tắt auto và cooldown; **không** áp cooldown AUTO_LOCATION cho mọi yêu cầu manual/QR.<br><br>**AC-M05-01:** US-M10 entry đủ điều kiện được xử lý sau debounce 3 giây.<br><br>**AC-M05-02:** US-M11 không phát trùng trong cùng entry hoặc trong cooldown 5 phút của cùng POI.<br><br>**AC-M05-03:** Safety reconcile 5 giây không bypass debounce/cooldown.<br><br>**AC-M05-04:** Khi POI overlap, hệ thống chỉ chọn tối đa một audio.<br><br>**AC-M05-05:** Chỉ ghi cooldown sau khi player thực sự bắt đầu; pending candidate được revalidate trước khi phát.

## Activity Diagram

```mermaid
flowchart TD
 A([Nhận location update hoặc safety reconcile]) --> B{Auto bật, quyền GPS và sample tin cậy?}
 B -- Không --> X[Không auto-trigger; QR/manual còn dùng]
 B -- Có --> C[Chọn POI ACTIVE trong snapshot và tính distance]
 C --> D[Cập nhật state OUTSIDE / ENTER_DEBOUNCE / INSIDE_HANDLED / EXIT_DEBOUNCE]
 D --> E{Ở trong vùng ổn định 3 giây tạo entry mới?}
 E -- Không --> F[Giữ/đưa về OUTSIDE sau exit debounce; chờ sample] --> Z([Tiếp tục theo dõi])
 E -- Có --> G{Cooldown 5 phút của POI còn hiệu lực?}
 G -- Có --> H[INSIDE_HANDLED; không phát lại trong cùng entry] --> Z
 G -- Không --> I[Chọn candidate theo tỷ lệ distance/radius, distance, poi_id]
 I --> J{Player đang phát nội dung khác?}
 J -- Có --> K[Pending; khi player rảnh revalidate vị trí/entry/cooldown/audio] --> L{Còn hợp lệ?}
 L -- Không --> Z
 L -- Có --> M[Chọn audio đúng ngôn ngữ: local VERIFIED hoặc online PUBLISHED]
 J -- Không --> M
 M --> N{Audio khả dụng?}
 N -- Không --> O[Không phát, không set cooldown] --> Z
 N -- Có --> P{Player bắt đầu phát thành công?}
 P -- Không --> O
 P -- Có --> Q[Ghi last_auto_triggered_at; INSIDE_HANDLED] --> Z
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Point_Of_Interests(latitude, longitude, trigger_radius_meter, poi_status)`, `Local_POI_Trigger_State` và trạng thái player.
- **Liên kết:** Dependencies / Notes
- Phụ thuộc FT-M06 cho location background, FT-M08 để bật/tắt auto, FT-M03 cho phát và FT-M07 cho metadata local.
- Nguồn: PRD.md FR-M07, US-M10–11, BR-12–13; `docs/database-design.md` §4.2.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
