# UC-WEB-01 — Quản trị POI, nội dung thuyết minh và audio

| Use case number: | UC-WEB-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Quản trị POI, nội dung thuyết minh và audio |  |
| **Actor(s):** | Người quản trị nội dung có quyền tương ứng, Admin Web, MNR Backend |  |
| **Maturity:** | Specification / Target behavior — mô tả luồng nghiệp vụ mục tiêu; cần xác minh từng API và tích hợp tài nguyên audio trước khi đánh dấu Implemented. |  |
| **Summary:** | Quản lý vòng đời POI, phiên bản nội dung đa ngôn ngữ và metadata audio từ khâu tạo/hiệu chỉnh đến phê duyệt, xuất bản và phân phối công khai; bảo đảm không công bố dữ liệu chưa hợp lệ. **Traceability:** Epic: EP-W01 — POI and Narration Administration; Component / Priority: Web Administration / P0; Features: FT-W01 POI Management; FT-W02 Narration Content Management; FT-W03 Audio Management; Requirements: FR-W02; FR-W03; FR-W04; User Stories: US-W01–US-W08 |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | **FT-W01 — Quản lý POI** |  |
|  | 1\. Người quản trị mở danh sách POI; backend kiểm tra session và permission `read`. |  **E1, E2, E3** |
|  | 2\. Người quản trị tìm kiếm/lọc/phân trang, xem chi tiết POI và dữ liệu khu vực, danh mục. |  |
|  | 3\. Chọn tạo POI; nhập `region_id`, `poi_name`, `poi_location`, `poi_image_url`, `poi_qr_code`, tọa độ và `trigger_radius_meter`. |  **A1, E4** |
|  |  | 4\. Backend kiểm tra bắt buộc, tọa độ trong miền hợp lệ, bán kính dương, mã QR/địa chỉ không trùng và khóa ngoại; tạo POI với `poi_status = INACTIVE` (**BR-03**). **A1, E4** |
|  |  | 5\. Khi cập nhật, backend kiểm tra permission, tham chiếu và quy tắc toàn vẹn dữ liệu. |
|  | 6\. Khi yêu cầu kích hoạt, backend chỉ chuyển sang `ACTIVE` nếu POI có ít nhất một phiên bản tiếng Anh `PUBLISHED` và audio metadata/tài nguyên hợp lệ (**BR-04**). |  **A2, E6** |
|  | 7\. Khi vô hiệu hóa, POI ngừng xuất hiện ở API công khai online; thay đổi dữ liệu mobile-relevant đánh dấu package liên quan cần rebuild. |  **A2, E10** |
|  | 8\. Khi xóa, backend từ chối nếu còn tham chiếu nội dung, lịch sử nghe hoặc package vi phạm ràng buộc (**BR-11**). |  **E5** |
|  | **FT-W02 — Quản lý nội dung và xuất bản** |  |
|  | 1\. Từ một POI, người quản trị chọn ngôn ngữ đã đăng ký và tạo nội dung `narration_title`, `narration_script`. |  **A3, E2, E3** |
|  |  | 2\. Backend tạo `Poi_Content` mới ở `DRAFT` với `content_version` tăng trong phạm vi `poi_id + language_id`; không ghi đè bản đang PUBLISHED. **A3** |
|  | 3\. Người có quyền gửi `WAITING_APPROVAL`; reviewer có permission tương ứng phê duyệt thành `APPROVED` hoặc từ chối (`REJECTED` theo state machine). |  **E3, E7** |
|  |  | 4\. Trước khi publish, hệ thống yêu cầu audio hợp lệ gắn với đúng phiên bản content; nếu có quy trình TTS khi publish thì tạo file, upload và xác minh trước khi đổi trạng thái. **A4, E8, E11** |
|  |  | 5\. Khi mọi điều kiện đạt và permission `publish` hợp lệ, backend chuyển bản mới thành `PUBLISHED`, lưu thông tin người/thời điểm xuất bản. **A5, E7, E9** |
|  |  | 6\. Bản PUBLISHED trước của cùng cặp POI-ngôn ngữ được chuyển `ARCHIVED` trong xử lý nhất quán; đánh dấu package offline bị ảnh hưởng cần rebuild. **A5, E9, E10** |
|  |  | 7\. Nếu đây là tiếng Anh cho POI ACTIVE, phải bảo đảm quá trình thay phiên bản không tạo khoảng trống bản tiếng Anh khả dụng. |
|  | **FT-W03 — Quản lý metadata audio** |  |
|  | 1\. Người có quyền mở phiên bản content và trang quản lý audio. |  **E2, E3** |
|  |  | 2\. Hệ thống hiển thị `audio_source_type` (`RECORD` hoặc `TTS`), `audio_url`, `audio_mime_type`, `audio_size`, `audio_duration_sec`, `audio_checksum_sha256`. |
|  |  | 3\. Trước khi gắn/thay audio, hệ thống kiểm tra tính hợp lệ của metadata và xác minh tài nguyên vật lý qua cơ chế tích hợp thích hợp. **A4, E8, E11** |
|  |  | 4\. Mỗi `poi_content_id` có tối đa một `Content_Audio` trong thiết kế hiện tại. |
|  | 5\. Nếu thay audio, phải dùng asset URL bất biến phù hợp checksum; đánh dấu các package tham chiếu nội dung cần rebuild. |  **A4, E10** |
|  |  | 6\. Chỉ metadata **không** chứng minh tệp đã upload/verify; không publish dựa trên bản ghi chưa kiểm chứng. **E11** |
| **Alternative Paths:** | **A1 — Quản lý POI và sửa metadata:** Người có quyền tạo/sửa POI; chỉ POI hợp lệ được lưu, POI mới luôn INACTIVE.<br><br>**A2 — Kích hoạt và vô hiệu hóa POI:** Khi kích hoạt phải có nội dung en PUBLISHED + audio thực sự hợp lệ; khi vô hiệu hóa, API online không trả POI và package liên quan cần rebuild.<br><br>**A3 — Tạo phiên bản nội dung mới:** Giữ bản PUBLISHED cũ đang phân phối trong khi bản mới DRAFT/WAITING_APPROVAL/APPROVED; không ghi đè version cũ.<br><br>**A4 — Thay audio RECORD/TTS:** Upload tài nguyên mới trước, xác minh SHA-256/MIME/size/duration và URL bất biến rồi liên kết metadata; đánh dấu offline package liên quan cần rebuild.<br><br>**A5 — Xuất bản phiên bản mới:** Chuyển phiên bản cũ cùng POI/ngôn ngữ sang ARCHIVED nhất quán; bảo đảm POI ACTIVE không mất bản en PUBLISHED hợp lệ. |  |
| **Exception Paths:** | **E1 — Không có mạng đến Admin API/timeout/HTTP 5xx:** Thông báo yêu cầu chưa được xác nhận; không tự giả định ghi thành công, tải lại trạng thái server khi có mạng trước khi retry để tránh tạo dữ liệu trùng.<br><br>**E2 — JWT/session hết hạn hoặc bị thu hồi:** Trả 401; đăng nhập/làm mới phiên theo EP-W02, không thực hiện mutation trước khi xác thực hợp lệ.<br><br>**E3 — Không có permission cho hành động:** Backend trả 403; không sửa database, dù giao diện có hiển thị thao tác.<br><br>**E4 — POI thiếu trường, tọa độ ngoài [-90,90]/[-180,180], bán kính không dương, QR/địa chỉ trùng:** Trả validation/conflict; không tạo hoặc cập nhật bản ghi không hợp lệ.<br><br>**E5 — Xóa POI còn quan hệ content/history/offline package:** Từ chối xóa theo ràng buộc tham chiếu BR-11; giữ nguyên dữ liệu liên quan.<br><br>**E6 — Bật ACTIVE nhưng thiếu bản tiếng Anh PUBLISHED hoặc audio hợp lệ:** Giữ INACTIVE và chỉ rõ điều kiện còn thiếu.<br><br>**E7 — Content chưa APPROVED, role không có quyền approve/publish, hoặc phiên bản đã thay đổi:** Không xuất bản; yêu cầu kiểm tra lại state và quyền ở backend.<br><br>**E8 — TTS/upload/file verification thất bại:** Giữ content APPROVED, bản PUBLISHED cũ tiếp tục phục vụ, không archive, cho retry bước tạo audio.<br><br>**E9 — Publish/đổi ARCHIVED hoặc ghi DB lỗi giữa transaction:** Rollback để không có hai bản PUBLISHED hoặc mất bản đang phân phối; thông báo lỗi và tải lại trạng thái.<br><br>**E10 — Offline package rebuild thất bại:** Không công bố manifest BUILDING/FAILED; bản PUBLISHED cũ và local READY cũ tiếp tục sử dụng.<br><br>**E11 — Audio metadata tồn tại nhưng file thiếu/checksum sai:** Không chấp nhận tài nguyên chưa VERIFIED khi publish; không đánh đồng metadata với upload thực tế. |  |
| **Extension Points:** | Có thể bổ sung hệ thống xử lý TTS/upload file thực tế, audit event và quy trình rebuild package tự động. |  |
| **Triggers:** | Người quản trị muốn tạo/cập nhật POI, quản lý phiên bản nội dung hoặc audio và xuất bản. |  |
| **Assumptions:** | Permission quản trị được backend kiểm tra; tệp audio phải xác minh riêng với metadata. |  |
| **Preconditions:** | Người quản trị đã đăng nhập, session còn hợp lệ và có permission tương ứng với hành động create/read/update/delete/approve/publish. |  |
| **Post Conditions:** | Dữ liệu được lưu/đổi trạng thái hợp lệ; nội dung PUBLISHED có audio hợp lệ; POI ACTIVE chỉ tồn tại khi có bản tiếng Anh PUBLISHED và audio phù hợp. |  |
| **Preferences:** | Ưu tiên bảo đảm quyền riêng tư, không khai báo chức năng đã triển khai khi mới ở mức thiết kế; xử lý nguồn dữ liệu/phiên bản đúng PRD và database contract. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 09-11-2026 |  |

## Business Rules and Acceptance Criteria

**BR-02–04, BR-09, BR-11:** Chỉ ACTIVE công khai; POI mới INACTIVE; điều kiện English + audio; RBAC backend; ràng buộc delete.<br><br>**AC-W01-01:** US-W01–03 quản lý POI hợp lệ, tìm kiếm/lọc và từ chối kích hoạt/xóa sai quy tắc.<br><br>**AC-W01-02:** US-W04–05 tạo bản DRAFT/version mới mà không ghi đè bản đã publish.<br><br>**AC-W01-03:** US-W06 chỉ người có quyền duyệt/publish chuyển trạng thái; content không được PUBLISHED thiếu audio hợp lệ.<br><br>**AC-W01-04:** US-W07–08 hiển thị và kiểm tra metadata đúng content; phân biệt RECORD/TTS.<br><br>**AC-W01-05:** Khi publish bản mới, bản đang PUBLISHED trước đó được ARCHIVED nhất quán; package liên quan cần rebuild.<br><br>**AC-W01-06:** Đối với POI ACTIVE, hệ thống không cho phép thay đổi làm mất bản tiếng Anh PUBLISHED với audio hợp lệ.

## Activity Diagram

Activity Diagram — POI Administration

```mermaid
flowchart TD
    A([Mở quản lý POI]) --> B{Session và permission hợp lệ?}
    B -- Không --> X[Từ chối truy cập]
    B -- Có --> C[Danh sách / tìm kiếm / xem POI]
    C --> D{Hành động}
    D -- Tạo/Cập nhật --> E[Kiểm tra dữ liệu và ràng buộc]
    E --> F{Hợp lệ?}
    F -- Không --> G[Thông báo trường lỗi]
    F -- Có --> H[Lưu POI; tạo mới = INACTIVE] --> Z([Kết thúc])
    D -- Kích hoạt --> I{Có English PUBLISHED và audio hợp lệ?}
    I -- Không --> J[Giữ INACTIVE]
    I -- Có --> K[Đặt ACTIVE và cập nhật phụ thuộc offline] --> Z
    D -- Xóa --> L{Còn tham chiếu bị ràng buộc?}
    L -- Có --> M[Từ chối xóa]
    L -- Không --> N[Xóa theo permission] --> Z
```


```mermaid
flowchart TD
    A([Chọn POI và ngôn ngữ]) --> B[Tạo phiên bản DRAFT]
    B --> C[Gửi WAITING_APPROVAL]
    C --> D{Có quyền approve và nội dung đạt?}
    D -- Không --> E[REJECTED / chỉnh sửa bản nháp]
    E --> B
    D -- Có --> F[APPROVED]
    F --> G[Liên kết / chuẩn bị audio]
    G --> H{Audio có tệp và metadata đã verify?}
    H -- Không --> I[Giữ APPROVED, cho retry]
    H -- Có --> J{Có quyền publish?}
    J -- Không --> X[Từ chối publish]
    J -- Có --> K[Publish bản mới, archive bản cũ cùng POI-ngôn ngữ]
    K --> L[Đánh dấu package cần rebuild]
    L --> M([Kết thúc])
```

## Traceability, Data and Implementation Notes

- **Nguồn dữ liệu:** - **Hậu điều kiện thành công:** Dữ liệu được lưu/đổi trạng thái hợp lệ; nội dung PUBLISHED có audio hợp lệ; POI ACTIVE chỉ tồn tại khi có bản tiếng Anh PUBLISHED và audio phù hợp. `Point_Of_Interests`, `Poi_Category_Mapping`, `Regions`, `Poi_Categories`, `Languages`, `Poi_Contents`, `Content_Audios`, `Offline_Packages`, `Offline_Package_Items`; audit log là yêu cầu hệ thống.
- **Liên kết:** EP-W01 chỉ bao gồm FT-W01, FT-W02, FT-W03 theo PRD §3.3.2; xác thực/phiên quản trị thuộc EP-W02.
- Quy trình TTS/upload/verify file được mô tả như **luồng tích hợp mục tiêu**; không khẳng định chỉ từ metadata rằng file đã được tạo thực tế.
- PRD FR-W03 có nghiệp vụ gỡ bỏ nội dung; chuyển trạng thái/gỡ bỏ phải bảo toàn quy tắc English narration của POI ACTIVE và phiên bản đang phân phối.
- Nguồn: PRD.md FR-W02–04, US-W01–08, BR-02–04/09/11; `docs/database-design.md` §2.2–2.3.
- **Nguồn tham khảo:** PRD.md (§2.3, §3.3–3.4); `docs/database-design.md`; mẫu bố cục `docs/usecase/authentication-session.md`.
