# UC-MOBILE-GEOFENCE-01 — Tự động phát thuyết minh khi đi vào vùng ảnh hưởng của POI

| Use case number: | UC-MOBILE-GEOFENCE-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Tự động phát thuyết minh khi đi vào vùng ảnh hưởng của POI |  |
| **Actor(s):** | Khách du lịch (Tourist); tác nhân hỗ trợ: dịch vụ định vị của thiết bị, Mobile Application (Geofence Engine, Narration Player, Offline Content Manager, Listening History Synchronizer), hệ thống cung cấp nội dung và nhận lịch sử nghe |  |
| **Maturity:** | Specified — luồng nghiệp vụ mục tiêu; chưa xác nhận toàn bộ hành vi đã triển khai trên Android/iOS hoặc backend |  |
| **Summary:** | Khi du khách bật thuyết minh tự động và đi vào vùng ảnh hưởng của một POI, ứng dụng xác minh vị trí, phát hiện sự kiện vào vùng ổn định, kiểm tra cooldown, giải quyết chồng lấn POI và chọn audio hợp lệ để phát mà không chồng âm thanh. Hệ thống hỗ trợ audio từ package offline đã xác minh hoặc từ server khi có Internet; sau khi audio thực sự bắt đầu, ứng dụng ghi lịch sử nghe trên thiết bị và đồng bộ lên server khi kết nối cho phép. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách bật **Thuyết minh tự động** và di chuyển trong khu vực tham quan. |  |
|  |  | 2\. Ứng dụng kiểm tra cài đặt, quyền vị trí, GPS và khả năng theo dõi của hệ điều hành. **E1** |
|  |  | 3\. Ứng dụng lấy thông tin POI **ACTIVE** từ package local **READY** hoặc từ server khi có Internet. **A1, A2, E2** |
|  |  | 4\. Ứng dụng nhận vị trí mới, kiểm tra độ tin cậy và tính khoảng cách `d` tới POI có bán kính `r = trigger_radius_meter`. **E3** |
|  |  | 5\. Khi `d <= r`, hệ thống chuyển sang `ENTER_DEBOUNCE`; chỉ xác nhận vào vùng sau **3 giây** ở trong vùng ổn định. Nếu ra ngoài sớm, hủy entry. **E4** |
|  |  | 6\. Khi có callback vị trí bị bỏ lỡ, hệ thống **safety reconcile mỗi 5 giây** nếu hệ điều hành cho phép; mẫu vị trí vẫn phải qua bước 4–5. **A3** |
|  |  | 7\. Hệ thống kiểm tra **cooldown 5 phút** theo từng POI từ `last_auto_triggered_at`. Trong cooldown hoặc đã xử lý cùng entry thì không phát lại. **E5** |
|  |  | 8\. Nếu có nhiều POI hợp lệ, chọn tối đa một theo thứ tự `d/r` nhỏ nhất, sau đó `d` và `poi_id`. **A4** |
|  |  | 9\. Nếu đang phát audio khác, hệ thống giữ POI chờ và kiểm tra lại điều kiện khi player rảnh; không tự phát chồng. **A5** |
|  |  | 10\. Ứng dụng chọn audio đúng ngôn ngữ: ưu tiên file local **VERIFIED** thuộc package **READY**, hoặc nội dung **PUBLISHED** online khi khả dụng. **A1, A2, E6** |
|  |  | 11\. Hệ thống bắt đầu phát thuyết minh. Chỉ khi audio **thực sự bắt đầu** mới ghi cooldown và tạo lịch sử nghe `AUTO_LOCATION` với ID duy nhất ở `Local_Listening_Events`. **E7, E9** |
|  | 12\. Du khách nghe thuyết minh và có thể tạm dừng hoặc dừng phát. |  |
|  |  | 13\. Ứng dụng lưu `duration_sec` theo thời lượng phát thực tế và `completed_at` khi kết thúc/dừng. **A6** |
|  |  | 14\. Ứng dụng đồng bộ lịch sử nghe lên server khi có Internet; nếu chưa đồng bộ thành công, giữ sự kiện `PENDING/FAILED` và thử lại **cùng ID** khi có kết nối. **A7, E8** |
|  |  | 15\. Khi người dùng ra ngoài vùng ổn định **3 giây**, chuyển POI về `OUTSIDE`; lần đi vào tiếp theo phải kiểm tra lại debounce và cooldown. |
| **Alternative Paths:** | **A1 — Có dữ liệu offline:** Tại bước 3 hoặc 10, nếu package phù hợp đã **READY** và audio **VERIFIED**, hệ thống dùng dữ liệu local, kể cả khi không có Internet; tiếp tục bước 4 hoặc 11.<br><br>**A2 — Có mạng nhưng chưa tải offline:** Tại bước 3 hoặc 10, nếu chưa có dữ liệu local nhưng server khả dụng, hệ thống lấy POI **ACTIVE** và audio **PUBLISHED** online; tiếp tục bước 4 hoặc 11. Fallback tiếng Anh chỉ áp dụng khi phát online theo quy tắc nghiệp vụ.<br><br>**A3 — Bỏ lỡ sự kiện vị trí:** Tại bước 6, nếu không nhận được callback, safety reconcile lấy mẫu vị trí mới khi có thể, quay lại bước 4; không bỏ qua debounce hoặc cooldown.<br><br>**A4 — Nhiều POI chồng lấn:** Tại bước 8, nếu nhiều POI đủ điều kiện, hệ thống chọn một POI theo `d/r`, `d`, `poi_id`; tiếp tục bước 9.<br><br>**A5 — Player đang bận:** Tại bước 9, nếu đang có audio phát, hệ thống chờ; khi player rảnh, quay lại bước 4 để kiểm tra lại vị trí, entry, cooldown và audio. Nếu không còn hợp lệ, kết thúc nhánh đang chờ.<br><br>**A6 — Người dùng tạm dừng hoặc dừng:** Tại bước 12, nếu người dùng tạm dừng rồi tiếp tục, chỉ tính thời gian audio thực sự phát; nếu dừng, chốt thời lượng đã nghe nhưng vẫn giữ cooldown đã ghi; tiếp tục bước 13.<br><br>**A7 — Đồng bộ khi có mạng trở lại:** Tại bước 14, nếu trước đó offline và còn lịch sử `PENDING/FAILED`, ứng dụng gửi lại từng sự kiện bằng ID cũ; khi server xác nhận, đánh dấu `SYNCED` và kết thúc lượt đồng bộ. |  |
| **Exception Paths:** | **E1 — Không đủ điều kiện định vị:** Tại bước 2, nếu tắt tự động, chưa cấp quyền vị trí, GPS tắt hoặc hệ điều hành không cho theo dõi, hệ thống không tự phát. Với thiếu quyền, hiển thị “Vui lòng cấp quyền vị trí để sử dụng thuyết minh tự động.”; với GPS tắt, hiển thị “Vui lòng bật định vị trên thiết bị.”. Khi đã khắc phục, quay lại bước 2; nếu không, kết thúc luồng.<br><br>**E2 — Không có dữ liệu POI:** Tại bước 3, nếu không có Internet hoặc server lỗi và cũng chưa có package offline **READY**, hiển thị “Chưa có dữ liệu tham quan. Vui lòng kết nối Internet hoặc tải nội dung ngoại tuyến.”; kết thúc luồng.<br><br>**E3 — Vị trí không đáng tin cậy:** Tại bước 4, nếu GPS quá cũ hoặc độ chính xác không đủ, bỏ mẫu và chờ vị trí mới; quay lại bước 4, không kích hoạt audio.<br><br>**E4 — Không đủ thời gian debounce:** Tại bước 5, nếu người dùng ra khỏi vùng trước khi đủ **3 giây** hoặc GPS dao động qua ranh giới, hủy lần vào vùng đang xét; quay lại bước 4.<br><br>**E5 — POI đang cooldown hoặc đã xử lý entry:** Tại bước 7, nếu chưa đủ **5 phút** kể từ lần auto-play thành công hoặc người dùng vẫn ở trong cùng entry, không phát. Chờ xác nhận ra ngoài vùng rồi quay lại bước 4 khi có entry mới; không phát ngay khi cooldown vừa hết.<br><br>**E6 — Không có audio hợp lệ:** Tại bước 10, nếu offline không có audio đúng ngôn ngữ đã **VERIFIED**, hoặc online không lấy được audio **PUBLISHED** hợp lệ, hiển thị “Chưa có nội dung thuyết minh khả dụng cho địa điểm này.”. Không phát và không ghi cooldown; kết thúc nhánh phát.<br><br>**E7 — Không bắt đầu phát được:** Tại bước 11, nếu file lỗi hoặc player không phát được, hiển thị “Không thể phát thuyết minh. Vui lòng thử lại.”; không ghi cooldown hoặc lịch sử bắt đầu nghe; kết thúc nhánh phát.<br><br>**E8 — Đồng bộ lịch sử nghe thất bại:** Tại bước 14, nếu mất mạng, server lỗi hoặc phản hồi bị mất, giữ sự kiện ở `PENDING/FAILED`, không tạo ID mới và không đánh dấu `SYNCED`. Khi có mạng, quay lại bước 14; kết thúc lượt đồng bộ hiện tại.<br><br>**E9 — Không lưu được dữ liệu nghe trên thiết bị:** Tại bước 11, nếu không lưu được cooldown hoặc sự kiện nghe, hệ thống ghi nhận lỗi và tránh tự phát lặp lại không kiểm soát; không đánh dấu đã đồng bộ. Khi lưu trữ phục hồi, thử ghi lại thông tin còn xác định được; nếu không, kết thúc nhánh ghi nhận. |  |
| **Extension Points:** | Các mở rộng như telemetry chuyên sâu, tối ưu hệ điều hành và chiến lược retry nâng cao nằm ngoài phạm vi đồ án; chỉ cần bảo đảm các quy tắc cốt lõi trong luồng chính. |  |
| **Triggers:** | Người dùng bật tính năng tự động và ứng dụng nhận location update, location transition hoặc safety reconcile hợp lệ; sau khi phát, có thêm trigger đồng bộ khi mạng trở lại. |  |
| **Assumptions:** | POI có tọa độ và `trigger_radius_meter` hợp lệ; server chỉ cung cấp POI ACTIVE và content/audio PUBLISHED cho luồng công khai online; gói offline đã xác minh trước khi ở trạng thái READY; hệ điều hành có thể giới hạn callback/auto-play ở nền; cài đặt ngôn ngữ và auto narration được lưu local. |  |
| **Preconditions:** | Người dùng đã bật tự động, cấp quyền vị trí phù hợp, GPS bật, có vị trí đủ tin cậy; có nguồn POI hợp lệ từ server hoặc package READY. Việc audio được phát hay không còn phụ thuộc kiểm tra tại bước 12–13, không mặc định đã có audio. |  |
| **Post Conditions:** | **Phát thành công:** Có đúng một narration được bắt đầu, cooldown theo POI được lưu từ thời điểm phát, event nghe `AUTO_LOCATION` được ghi local với ID duy nhất; khi kết thúc, duration/completed_at được cập nhật. **Đồng bộ thành công:** Event được server xác nhận và đánh dấu SYNCED. **Không phát hoặc đồng bộ thất bại:** Không ghi cooldown cho lượt chưa phát; event chưa đồng bộ được giữ để retry, không ghi trùng. |  |
| **Preferences:** | Không yêu cầu Tourist đăng nhập; không lấy vị trí nếu thiếu quyền; không phát chồng audio; không dùng asset chưa VERIFIED; không lưu IMEI/serial/advertising ID làm installation ID; không đồng bộ sự kiện trùng; không tự phát lại chỉ vì cooldown hết khi người dùng đứng nguyên trong POI. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 10-11-2026 |  |

## Quy tắc thời gian và trạng thái

| Cơ chế | Điều kiện/công thức | Hành vi |
| --- | --- | --- |
| Trong vùng | `d <= trigger_radius_meter` | Bắt đầu/duy trì kiểm tra entry debounce |
| Ngoài vùng | `d > trigger_radius_meter` | Bắt đầu/duy trì kiểm tra exit debounce |
| Entry debounce | `now - inside_since >= 3 giây`, trong vùng liên tục với mẫu tin cậy | Xác nhận một entry, sau đó mới kiểm tra cooldown |
| Exit debounce | Ngoài vùng ổn định 3 giây | Về `OUTSIDE`, cho phép entry mới trong tương lai |
| Safety reconcile | 5 giây **khi runtime và OS cho phép** | Sửa state qua cùng logic; không gọi player trực tiếp |
| Cooldown của POI | `now - last_auto_triggered_at < 5 phút` | Không auto-play trong một entry mới vẫn đang cooldown |
| Chống lặp theo entry | Trạng thái `INSIDE_HANDLED` | Không tự phát tiếp khi chỉ đứng trong vùng, dù cooldown hết |
| POI chồng lấn | Sắp xếp `(d/r, d, poi_id)` tăng dần | Chọn tối đa một candidate, không sử dụng trường ưu tiên POI riêng |
| Ghi cooldown | Chỉ khi playback thực sự bắt đầu | Load audio thất bại không tạo cooldown |

**Ví dụ thời gian:** Tại `t = 0s` thiết bị được phát hiện trong vùng; nếu các mẫu hợp lệ tiếp tục xác nhận ở trong vùng đến ít nhất `t = 3s`, entry được xét cooldown. Nếu callback đầu tiên bị bỏ lỡ và reconcile phát hiện vào vùng tại `t = 5s`, debounce bắt đầu từ `t = 5s`, không được tính ngược như thể đã biết người dùng ở trong vùng từ `t = 0s`. Một POI đã auto-play lúc `10:00:00` có cooldown đến `10:05:00`; nếu người dùng ở nguyên trong vùng qua thời điểm đó thì không tự phát lần hai.

## Nguồn audio và tính sẵn sàng offline

| Trạng thái | Kết quả |
| --- | --- |
| Offline, package READY và audio local VERIFIED đúng ngôn ngữ | Phát local; ghi lịch sử local PENDING, đồng bộ sau |
| Offline, package READY có POI nhưng thiếu audio hoặc sai ngôn ngữ | Không phát và không set cooldown; thông báo cần tải đúng nội dung |
| Offline, package đang DOWNLOADING/PAUSED/FAILED | Không coi là sẵn sàng; không dùng file `.part` để phát |
| Online, chưa có package local nhưng API POI/content/audio hợp lệ | Có thể phát online theo bản PUBLISHED, không bắt buộc tải package trước |
| Online, audio local CORRUPTED | Bỏ file lỗi, lấy bản PUBLISHED online nếu khả dụng |
| Online, ngôn ngữ được chọn không có bản PUBLISHED hợp lệ | Theo BR-05, thử tiếng Anh; nếu vẫn thiếu thì không phát |
| Online nhưng API/audio timeout hoặc server xác nhận POI INACTIVE | Không bỏ qua hạn chế public bằng snapshot cũ; nếu không có nguồn hợp lệ thì không phát |

## Trạng thái đồng bộ Listening History

1. **Playback thực sự bắt đầu:** tạo `id` dạng `listen-ddmmyy-xxxxxxxx` trên thiết bị, gắn `installation_id` UUID, `poi_id`, `poi_content_id`, `trigger_type = AUTO_LOCATION`, `started_at` và ghi `Local_Listening_Events`. Ghi cooldown ngay thời điểm này, không chờ kết thúc audio.
2. **Playback hoàn thành hoặc bị dừng:** cập nhật `completed_at` và `duration_sec` theo thời gian thực sự phát. Nếu app crash, dùng checkpoint thời lượng đã ghi để phục hồi phần có thể xác định.
3. **Chưa có mạng:** event ở `PENDING`; khi bắt đầu gửi chuyển `SYNCING`; lỗi/timeout giữ `PENDING/FAILED` để retry (không tạo ID khác).
4. **Server xác nhận:** chuyển `SYNCED`. Nếu ACK bị mất nhưng server đã lưu, retry với cùng ID phải được server xử lý idempotent.
5. **Sau khi mạng hồi phục:** xử lý cả event của phiên hiện tại và các event cũ còn PENDING/FAILED; mỗi event được xác nhận độc lập.

## Activity Diagram (tóm tắt luồng quyết định)

```mermaid
flowchart TD
    A([Bật auto narration]) --> B{Quyền GPS và auto hợp lệ?}
    B -- Không --> X[Không tự phát; manual/QR còn dùng]
    B -- Có --> C{Có POI online hoặc local READY?}
    C -- Không --> Y[Báo thiếu dữ liệu POI]
    C -- Có --> D[Location sample mới, tin cậy]
    D --> E{Trong vùng đủ 3 giây?}
    E -- Không --> D
    E -- Có --> F{Cooldown 5 phút còn hiệu lực?}
    F -- Có --> G[INSIDE_HANDLED, chờ exit/re-entry]
    F -- Không --> H[Chọn một POI theo d/r, d, poi_id]
    H --> I{Player đang bận?}
    I -- Có --> J[Giữ pending, revalidate khi rảnh]
    J --> D
    I -- Không --> K{Có local VERIFIED audio?}
    K -- Có --> L[Chuẩn bị phát local]
    K -- Không --> M{Online và PUBLISHED audio hợp lệ?}
    M -- Không --> N[Không phát, không ghi cooldown]
    M -- Có --> O[Chuẩn bị phát online]
    L --> P{Playback đã thực sự bắt đầu?}
    O --> P
    P -- Không --> N
    P -- Có --> Q[Ghi cooldown và event AUTO_LOCATION local]
    Q --> R[Chốt thời lượng nghe thực tế]
    R --> S{Server nhận được event và ACK?}
    S -- Có --> T[Đánh dấu SYNCED]
    S -- Không --> U[Giữ PENDING/FAILED, retry cùng ID khi có mạng]
    T --> V([Tiếp tục theo dõi exit/re-entry])
    U --> V
```

## Traceability và ghi chú đặc tả

- **Epic:** EP-M03 — Automatic Geofence Narration; **Feature:** FT-M05 / FR-M07 và FT-M06 / FR-M08; **User Stories:** US-M10, US-M11, US-M12.
- **Business Rules:** BR-01, BR-02, BR-05, BR-06, BR-12, BR-13, BR-14. **Nguồn:** `PRD.md` (đặc tả yêu cầu hiện hành), `docs/database-design.md` mục 3.2 và 4.1–4.2; cấu trúc bảng theo `docs/usecase/authentication-session.md` và `docs/usecase/example.md`.
- **Tình trạng quyết định nghiệp vụ:** PRD có đoạn mô tả kiến trúc ban đầu sử dụng thời gian trễ 10 giây và ưu tiên POI; nội dung này không thống nhất với database design hiện hành (debounce 3 giây, không có `trigger_priority`). Tài liệu này áp dụng quy tắc tại mục 4.2 của database design. Các ngưỡng GPS accuracy/staleness, thông báo nền và chính sách retry chưa được nguồn định lượng, nên không tự gán giá trị.
- **Thông báo trong dấu ngoặc kép** là câu chữ đề xuất cho giao diện, không khẳng định đã triển khai. Các thông báo lỗi nội bộ như sync failure chỉ hiển thị cho người dùng nếu có màn hình trạng thái phù hợp.