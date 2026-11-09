# FT-M03 — POI Narration Player

## 1. Overview

| Thuộc tính | Giá trị |
| --- | --- |
| Epic | EP-M02 — Narration Playback and QR Access |
| Feature / Requirement | FT-M03 / FR-M03 |
| User Stories | US-M06, US-M07, US-M08 |
| Actor | Tourist |
| Priority | P0 |

**Mục tiêu:** Phát đúng nội dung thuyết minh theo POI/ngôn ngữ lựa chọn, điều khiển pause/resume/stop; với **truy cập online**, fallback sang tiếng Anh nếu không có bản PUBLISHED và audio khả dụng bằng ngôn ngữ chọn.

## 2. Preconditions / Postconditions

- **Tiền điều kiện:** POI xác định được; có nội dung và audio khả dụng từ package READY hoặc từ backend; ứng dụng có thể phát âm thanh.
- **Hậu điều kiện:** Tối đa một audio đang phát tại một thời điểm; phiên phát được đóng khi kết thúc/dừng; nếu có logging thì trạng thái listening event nhất quán.
- **Dữ liệu:** `Poi_Contents` (content_version, content_status, language_id); `Content_Audios` (audio_source_type, audio_url, audio_checksum_sha256); `Local_Assets`, `Local_Listening_Events`.

## 3. Main Flow

1. Nhận `poi_id` từ chi tiết POI, QR Code hoặc Geofence và ngôn ngữ người dùng lựa chọn.
2. Xác định nguồn phát: ưu tiên asset local **VERIFIED** thuộc package READY phù hợp khi khả dụng; nếu online có thể tra nội dung từ backend.
3. Đối với **online**, truy vấn phiên bản `PUBLISHED` theo ngôn ngữ yêu cầu; nếu không có audio hợp lệ, áp dụng fallback sang `en` (PRD BR-05).
4. Đối với **offline**, chỉ chọn nội dung theo ngôn ngữ của package đã tải; không tự bổ sung fallback khác ngôn ngữ (BR-06).
5. Kiểm tra audio metadata và quyền truy cập asset; nếu local, đối chiếu trạng thái xác minh; chuẩn bị player.
6. Bắt đầu phát một audio, cập nhật trạng thái `PLAYING`; ghi nhận listening event khi phát **thực sự bắt đầu** nếu dịch vụ đã được tích hợp.
7. Người dùng có thể `PAUSE`, `RESUME` hoặc `STOP`; khi hoàn tất hoặc dừng, cập nhật thời lượng nghe.

## 4. Alternative / Exception Flows

| Trường hợp | Xử lý |
| --- | --- |
| Không có PUBLISHED theo ngôn ngữ chọn (online) | Thử bản tiếng Anh PUBLISHED có audio hợp lệ; thông báo nếu vẫn không có. |
| Offline không có asset đúng ngôn ngữ | Thông báo cần tải gói phù hợp; không phát bản khác tiếng. |
| Audio local thiếu/hỏng checksum | Không phát file chưa VERIFIED; gợi ý cập nhật/tải lại khi online. |
| URL audio lỗi hoặc mất mạng | Dừng/hiển thị lỗi; dùng local hợp lệ nếu sẵn có. |
| Player đang phát nội dung khác | Không chồng âm thanh; các yêu cầu auto được giữ làm pending và revalidate; yêu cầu thủ công xử lý theo chính sách chuyển phát của ứng dụng. |
| TTS chưa có file audio | Không giả định mobile tự tạo TTS; phát chỉ khi có audio khả dụng. |

## 5. Rules / Acceptance Criteria

- **BR-05, BR-06, BR-14:** Online có fallback tiếng Anh; offline không fallback; chỉ dùng local package đã xác minh.
- **AC-M03-01:** US-M06 phát đúng `poi_id` và nội dung PUBLISHED/ngôn ngữ khả dụng.
- **AC-M03-02:** US-M07 pause/resume/stop điều khiển đúng phiên, không tạo audio chồng.
- **AC-M03-03:** US-M08 thiếu bản ngôn ngữ yêu cầu online thì chọn bản `en` hợp lệ.
- **AC-M03-04:** Không gán thời điểm nghe hoặc cooldown khi player chưa bắt đầu phát thành công.
- **AC-M03-05:** Khi offline, không tự động lấy tiếng Anh nếu package yêu cầu là ngôn ngữ khác.

## 6. Activity Diagram

```mermaid
flowchart TD
    A([Yêu cầu phát narration]) --> B[Nhận POI và ngôn ngữ]
    B --> C{Asset local VERIFIED hợp lệ?}
    C -- Có --> D[Chọn audio local]
    C -- Không --> E{Online?}
    E -- Không --> X[Thông báo nội dung chưa tải]
    E -- Có --> F[Truy vấn content PUBLISHED]
    F --> G{Có nội dung đúng ngôn ngữ và audio?}
    G -- Có --> H[Chọn audio yêu cầu]
    G -- Không --> I{Có bản tiếng Anh hợp lệ?}
    I -- Có --> J[Chọn audio tiếng Anh]
    I -- Không --> X
    D --> K[Kiểm tra player]
    H --> K
    J --> K
    K --> L[Bắt đầu phát thành công]
    L --> M{Thao tác hoặc kết thúc}
    M -- Tạm dừng --> N[Pause] --> O[Resume] --> M
    M -- Dừng/Kết thúc --> P[Đóng phiên nghe] --> Q([Kết thúc])
```

## 7. Dependencies / Notes

- Phụ thuộc FT-M01/FT-M04/FT-M05 để xác định POI; FT-M07 để phát offline và FT-M08 để lấy ngôn ngữ.
- Phân biệt dữ liệu thiết kế và tình trạng triển khai; Listening History / đồng bộ sự kiện là yêu cầu tích hợp.
- Nguồn: PRD.md FR-M03, BR-05–06, BR-14, US-M06–08; `docs/database-design.md` §2.2.3–2.2.4, §3.2, §4.2.
