# UC-MOBILE-07 — Tải, cập nhật và sử dụng nội dung ngoại tuyến

| Use case number: | UC-MOBILE-07 |  |
| :---- | :---- | :---- |
| **Use case name:** | Tải, cập nhật và sử dụng nội dung ngoại tuyến |  |
| **Actor(s):** | Tourist (khách du lịch), Mobile Application |  |
| **Maturity:** | Specification / Target behavior — chức năng được đặc tả theo PRD và database design; chưa xác nhận toàn bộ luồng mobile đã triển khai. |  |
| **Summary:** | Chọn/tải gói thuyết minh theo `region + language + category?`, xác minh đầy đủ trước khi dùng offline và quản lý lưu trữ mà không làm hỏng package READY cũ. **Traceability:** Epic: EP-M04 — Offline Content and Preferences; Feature / Requirement: FT-M07 / FR-M05; User Stories: US-M13, US-M14, US-M15; Priority: P0 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách chọn khu vực, ngôn ngữ và bộ lọc danh mục POI tùy chọn. |  |
|  |  | 2\. Mobile xây dựng yêu cầu package logic theo `package_key` canonical và gửi tới backend. |
|  |  | 3\. Backend tra hoặc tạo package logic; chỉ công bố version **PUBLISHED** có manifest/asset hợp lệ, không coi `BUILDING` là sẵn sàng. |
|  |  | 4\. Mobile so sánh `package_version`, `schema_version` và checksum manifest với phiên bản local. |
|  |  | 5\. Mobile tải manifest, xác minh checksum, kiểm tra schema; xác định asset nào đã tồn tại theo checksum. |
|  |  | 6\. Mobile kiểm tra dung lượng, lưu download job, tải những asset còn thiếu vào file tạm `.part`, kiểm tra kích thước và SHA-256. |
|  |  | 7\. Chỉ khi **toàn bộ** asset bắt buộc đã VERIFIED, mobile thực hiện transaction upsert POI/content, cập nhật membership, version/checksum/status `READY`. |
|  |  | 8\. Sau commit thành công mới cleanup asset cũ không còn được package nào tham chiếu. |
|  | 9\. Du khách sử dụng content/audio local khi offline; xem dung lượng và có thể quản lý gói đã tải. |  |
| **Alternative Paths:** | **A1 — Có local package READY và không có Internet:** Tiếp tục sử dụng phiên bản đã commit; không phát sinh tải mới.<br><br>**A2 — Server đang BUILDING/FAILED phiên bản mới nhưng có bản PUBLISHED cũ:** Tiếp tục phân phối version PUBLISHED cũ; mobile giữ local READY trước khi có bản mới.<br><br>**A3 — Tệp checksum đã có trên máy:** Tái sử dụng `Local_Assets` VERIFIED thay vì tải lại, có lock khi hai package cần cùng asset.<br><br>**A4 — Máy tắt ứng dụng hoặc mất mạng trong download:** Giữ `Local_Download_Jobs` và file `.part`; resume/retry khi điều kiện phục hồi, không commit sớm.<br><br>**A5 — Server phát hành v3 trong khi thiết bị đang tải manifest v2 bất biến:** Cho phép hoàn tất v2 rồi kiểm tra phiên bản ở lần cập nhật tiếp theo. |  |
| **Exception Paths:** | **E1 — Không có mạng khi yêu cầu gói mới và chưa có READY:** Thông báo cần Internet, không đánh dấu package READY giả.<br><br>**E2 — Manifest URL lỗi, hết hạn HTTP 401/403:** Lấy lại package metadata/URL mới khi có mạng; retry có giới hạn.<br><br>**E3 — Manifest sai SHA-256, JSON lỗi hoặc schema_version chưa hỗ trợ:** Reject toàn bộ bản mới, yêu cầu cập nhật ứng dụng nếu schema không hỗ trợ, giữ READY cũ.<br><br>**E4 — HTTP 404/410 của asset:** Làm mới manifest/metadata vì có thể stale; không commit bản tải dở.<br><br>**E5 — HTTP 5xx/timeout/mất mạng trong tải:** Retry có giới hạn/backoff, giữ job và `.part` hoặc restart download khi thích hợp; package cũ không ảnh hưởng.<br><br>**E6 — File tải sai size/SHA-256 hoặc local file thiếu:** Không VERIFIED; xóa file `.part` hỏng và tải lại; file local bị mất phải xác minh lại khi dùng.<br><br>**E7 — Không đủ dung lượng hoặc người dùng hủy:** Dừng/PAUSED job; không làm mất package READY đang hoạt động.<br><br>**E8 — Transaction commit SQLite thất bại:** Rollback toàn bộ upsert/membership/version; giữ bản READY cũ, dọn orphan asset sau.<br><br>**E9 — Hai package tham chiếu cùng asset:** Không xóa physical asset khi còn `Local_Package_Items` tham chiếu; lock theo checksum để tránh tải trùng.<br><br>**E10 — Backend rebuild/publish thất bại:** Không phân phối version chưa xác minh; bản PUBLISHED cũ tiếp tục khả dụng. |  |
| **Extension Points:** | Có thể mở rộng theo các năng lực tích hợp mobile, backend và chính sách vận hành đã ghi trong PRD; không nằm trong phạm vi xác nhận triển khai hiện tại. |  |
| **Triggers:** | Người dùng yêu cầu tải/cập nhật/quản lý gói nội dung offline. |  |
| **Assumptions:** | Backend phải xuất bản manifest và tài nguyên hợp lệ; metadata DB không đồng nghĩa asset đã upload xong. |  |
| **Preconditions:** | Có kết nối để tải; backend có package/manifest phù hợp; thiết bị hỗ trợ schema và đủ dung lượng. |  |
| **Post Conditions:** | Package version mới ở trạng thái local `READY`, asset bắt buộc `VERIFIED`, có thể phát không cần mạng. Không kích hoạt package mới; package READY trước đó vẫn dùng được. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**Nguyên tắc atomic:** Không ghi đè READY cũ khi download, validate hoặc transaction chưa hoàn tất. Manifest đã publish là bất biến theo version; asset chia sẻ được lưu theo checksum. Gói offline chỉ gồm ngôn ngữ đã chọn, không tự bổ sung English fallback.


**BR-06, BR-07, BR-08, BR-14:** Package offline một ngôn ngữ xác định; chỉ PUBLISHED được phân phối; BUILDING không sẵn sàng; toàn vẹn bắt buộc trước kích hoạt.<br><br>**AC-M07-01:** US-M13 chọn region/language/category? truy xuất đúng package logic.<br><br>**AC-M07-02:** US-M14 khi mất mạng vẫn truy cập được POI/audio từ package READY và asset VERIFIED.<br><br>**AC-M07-03:** US-M15 hiển thị dung lượng và cho phép quản lý gói mà không xóa nhầm asset dùng chung.<br><br>**AC-M07-04:** Checksum sai, schema sai, thiếu bộ nhớ, transaction thất bại không làm mất bản READY trước đó.<br><br>**AC-M07-05:** Không áp dụng online English fallback tự động khi chỉ có package offline theo ngôn ngữ khác.

## Activity Diagram

```mermaid
flowchart TD
 A([Chọn region/language/category?]) --> B{Internet và API package khả dụng?}
 B -- Không --> C{Đã có local READY?}
 C -- Có --> D[Tiếp tục dùng local READY] --> Z([Kết thúc])
 C -- Không --> X[Báo cần kết nối để tải]
 B -- Có --> E[Tra package_key và phiên bản PUBLISHED]
 E --> F{Có phiên bản PUBLISHED sẵn sàng?}
 F -- Không --> G[Chờ build/giữ READY cũ] --> Z
 F -- Có --> H[Kiểm tra version/schema; tải manifest]
 H --> I{Manifest SHA/JSON/schema hợp lệ?}
 I -- Không --> J[Reject bản mới; giữ READY cũ] --> Z
 I -- Có --> K[Tính delta và dung lượng cần tải]
 K --> L{Đủ dung lượng?}
 L -- Không --> J
 L -- Có --> M[Tái sử dụng asset VERIFIED; tải asset thiếu vào .part]
 M --> N{Tải thành công và size/SHA-256 đúng?}
 N -- Không --> O[Retry/resume; lưu job; tuyệt đối chưa commit] --> Z
 N -- Có --> P{Mọi asset bắt buộc VERIFIED?}
 P -- Không --> O
 P -- Có --> Q[Transaction cập nhật Local_POIs/content/membership/version]
 Q --> R{Commit thành công?}
 R -- Không --> S[Rollback; giữ READY cũ; cleanup orphan sau] --> Z
 R -- Có --> T[Đánh dấu local READY; GC asset không còn tham chiếu] --> U([Dùng offline])
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** `Offline_Packages`, `Offline_Package_Items`, `Point_Of_Interests`, `Poi_Contents`, `Content_Audios`. `Local_Offline_Packages`, `Local_POIs`, `Local_Poi_Contents`, `Local_Assets`, `Local_Package_Items`, `Local_Download_Jobs`.
- **Liên kết:** Dependencies / Notes
- FT-M01/02/03/04/05 có thể dùng snapshot local; FT-M08 chọn ngôn ngữ tải.
- Server metadata package/manifest và cơ chế tải vật lý là hai giai đoạn; không đồng nhất “có DB row” với “đã có bundle tải hoàn chỉnh”.
- Nguồn: PRD.md FR-M05, US-M13–15, BR-06–08/14; `docs/database-design.md` §2.3, §3, §4.1.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
