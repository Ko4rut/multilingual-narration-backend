# UC-WEB-PACKAGE-01 — Tự động build và phân phối Offline Package

> **Phạm vi:** Tài liệu mô tả quy trình **server tự tạo/tái tạo và phát hành gói dữ liệu**. Đây **không phải** luồng tự tải trên mobile. Người dùng mobile **chủ động** nhấn **“Tải xuống”** hoặc **“Cập nhật”** sau khi gói được cung cấp. Việc Publish nội dung thuyết minh cũng **không đồng nghĩa** POI đã ACTIVE.

| Trường | Nội dung / hành động | Phản hồi hệ thống |
| :--- | :--- | :--- |
| Use case number: | UC-WEB-PACKAGE-01 |  |
| **Use case name:** | Hệ thống tự động build, rebuild và publish Offline Package để phân phối |  |
| **Actor(s):** | **Tác nhân kích hoạt:** sự kiện thay đổi POI/nội dung hoặc yêu cầu gói từ ứng dụng mobile; **tác nhân chính:** hệ thống quản lý và phân phối nội dung (backend); **tác nhân gián tiếp:** người quản trị và du khách. |  |
| **Maturity:** | Specified — nghiệp vụ dự kiến triển khai, không mô tả API. |  |
| **Summary:** | Hệ thống tự xác định gói offline nào cần được xây dựng khi người dùng lần đầu yêu cầu một bộ lọc mới hoặc khi dữ liệu POI/nội dung có ảnh hưởng đến gói đã tồn tại. Hệ thống kiểm tra dữ liệu, tạo manifest và công bố phiên bản mới an toàn, để mobile có thể nhận biết phiên bản tải/cập nhật. |  |
| **Basic Course of Events:** | **Actor action / sự kiện** | **System response** |
|  | 1. Người quản trị hoàn tất Publish nội dung, kích hoạt/vô hiệu hóa hoặc cập nhật POI; hoặc mobile lần đầu yêu cầu một gói theo khu vực/ngôn ngữ/danh mục. |  |
|  |  | 2. Hệ thống ghi nhận sự kiện có thể làm thay đổi dữ liệu phân phối hoặc yêu cầu gói mới. |
|  |  | 3. Hệ thống xác định bộ lọc `region + language + category (tùy chọn)` và các gói có liên quan, sử dụng một `package_key` ổn định cho mỗi bộ lọc. **A1, A3, E6** |
|  |  | 4. Hệ thống kiểm tra có bản PUBLISHED hiện tại hay chưa và chuẩn bị lượt build/rebuild; giữ bản đã phát hành có thể sử dụng trong lúc build. **A2** |
|  |  | 5. Hệ thống chọn POI thuộc đúng khu vực/danh mục với trạng thái **ACTIVE**, đồng thời chọn nội dung **PUBLISHED** đúng ngôn ngữ của gói; **không tự fallback tiếng Anh** khi build gói ngôn ngữ khác. **A5, E1** |
|  |  | 6. Hệ thống tự kiểm tra dữ liệu POI và các audio/hình ảnh được tham chiếu: audio thuộc đúng nội dung, metadata và tệp cần thiết tồn tại, hợp lệ và sẵn sàng phân phối. **E2** |
|  |  | 7. Hệ thống tạo danh sách POI, phiên bản nội dung và audio/hình ảnh cần đưa vào gói; so sánh với phiên bản đang PUBLISHED để xác định có thay đổi thật hay không. **A4, E6** |
|  |  | 8. Hệ thống xây dựng **manifest** mới trong vùng tạm, gồm metadata, các item và đường dẫn/tổng dung lượng/checksum của asset. Gói chỉ tham chiếu audio và hình ảnh, **không sao chép toàn bộ asset vào từng gói**. **E3, E6** |
|  |  | 9. Hệ thống kiểm tra manifest và checksum, bảo đảm các asset được manifest tham chiếu đều tồn tại và hợp lệ. **E3, E6** |
|  |  | 10. Hệ thống lưu manifest đã xác minh vào vị trí phân phối, không ghi đè bản bất biến đang được sử dụng. **E4, E6** |
|  |  | 11. Hệ thống công bố phiên bản mới trong một thao tác nhất quán: cập nhật danh sách item, `package_version`, đường dẫn manifest, checksum, dung lượng và thời gian Publish. **E4, E6** |
|  |  | 12. Hệ thống đánh dấu phiên bản mới **PUBLISHED** và ghi nhận “Build và phát hành gói nội dung thành công.”; phiên bản cũ chỉ được thay thế sau khi thao tác công bố thành công. **E5** |
|  |  | 13. Hệ thống cung cấp thông tin phiên bản PUBLISHED mới nhất để ứng dụng mobile có thể kiểm tra trạng thái gói. **A6** |
| **Alternative Paths:** | **A1 — Chưa từng có gói theo bộ lọc:** Tại bước 3, nếu chưa tồn tại package_key được yêu cầu lần đầu từ mobile, hệ thống tự tạo gói logic và đưa vào hàng đợi build với trạng thái BUILDING; quay lại bước 4 để xử lý như lần build đầu tiên.<br><br>**A2 — Gói đã có phiên bản PUBLISHED:** Tại bước 4, nếu gói đã có phiên bản PUBLISHED, hệ thống tiếp tục phân phối phiên bản hiện tại trong suốt quá trình rebuild, không chuyển bản đang sử dụng sang BUILDING; tiếp tục bước 5.<br><br>**A3 — Nhiều thay đổi hoặc yêu cầu trùng nhau:** Tại bước 3, nếu nhiều sự kiện cùng tác động đến một package_key hoặc gói đó đã có lượt build đang chạy, hệ thống gộp yêu cầu cần xử lý, không tạo các lượt build trùng; tiếp tục bước 4 hoặc xử lý lượt bổ sung sau khi build hiện tại kết thúc.<br><br>**A4 — Không thay đổi dữ liệu cần phân phối:** Tại bước 7, nếu dữ liệu sau khi lọc và kiểm tra tương đương phiên bản đã PUBLISHED, hệ thống giữ nguyên package_version và manifest hiện tại, ghi nhận không cần cập nhật; kết thúc luồng.<br><br>**A5 — POI hoặc nội dung bị thay đổi:** Tại bước 5, nếu POI chuyển INACTIVE, đổi khu vực/danh mục, hoặc nội dung PUBLISHED mới thay thế bản cũ, hệ thống tính lại danh sách item, thêm hoặc loại tham chiếu khỏi manifest mới mà không xóa dữ liệu nguồn; tiếp tục bước 6.<br><br>**A6 — Người dùng mobile kiểm tra gói sau khi server công bố:** Tại bước 13, nếu mobile hỏi thông tin gói mới, hệ thống trả về phiên bản và metadata mới để ứng dụng hiển thị “Có bản cập nhật” khi phù hợp. Mobile chỉ tải khi du khách nhấn “Cập nhật”; kết thúc luồng. |  |
| **Exception Paths:** | **E1 — Không có POI hoặc nội dung hợp lệ:** Tại bước 5, nếu bộ lọc không tìm được POI ACTIVE có nội dung PUBLISHED đúng ngôn ngữ và audio hợp lệ, hệ thống không đưa nội dung không đạt điều kiện vào gói; nếu đây là lần build đầu và không có item hợp lệ, gói chưa được phân phối và ghi nhận “Chưa có nội dung phù hợp để tạo gói.”; kết thúc luồng. Nếu gói đã từng PUBLISHED, giữ bản cũ và chờ thay đổi hợp lệ.<br><br>**E2 — Audio, hình ảnh hoặc metadata không hợp lệ:** Tại bước 6, nếu tài nguyên bắt buộc không tồn tại, không truy cập được hoặc không đáp ứng kiểm tra toàn vẹn, hệ thống không công bố manifest chứa tài nguyên lỗi, ghi nhận “Không thể build gói: dữ liệu hoặc tài nguyên chưa hợp lệ.”; giữ phiên bản PUBLISHED cũ nếu có; kết thúc luồng.<br><br>**E3 — Không thể tạo hoặc xác minh manifest:** Tại bước 8 hoặc 9, nếu manifest thiếu dữ liệu bắt buộc, sai cấu trúc hoặc checksum không khớp, hệ thống loại bỏ bản build tạm và ghi nhận “Không thể xác minh gói nội dung. Vui lòng thử lại.”; không tăng package_version; kết thúc luồng.<br><br>**E4 — Không thể lưu hoặc công bố phiên bản mới:** Tại bước 10 hoặc 11, nếu upload manifest hoặc cập nhật dữ liệu gói thất bại, hệ thống hủy cập nhật phiên bản mới, ghi nhận “Cập nhật gói phân phối thất bại.”; phiên bản PUBLISHED cũ vẫn khả dụng, hoặc trạng thái FAILED nếu chưa từng có bản hợp lệ; kết thúc luồng.<br><br>**E5 — Build lần đầu thất bại:** Tại bước 12, nếu gói chưa từng có phiên bản PUBLISHED mà lượt build thất bại, hệ thống ghi nhận trạng thái FAILED, ứng dụng mobile hiển thị “Gói nội dung hiện chưa khả dụng. Vui lòng thử lại sau.”; kết thúc luồng.<br><br>**E6 — Phát sinh thay đổi trong lúc đang build:** Tại bước 7 đến bước 11, nếu có thêm thay đổi sau thời điểm chốt dữ liệu đầu vào, hệ thống hoàn tất hoặc hủy bản build theo dữ liệu đã chốt một cách nhất quán và đánh dấu cần lượt build tiếp theo; không trộn dữ liệu của hai thời điểm vào một manifest; quay lại bước 3 cho lượt build tiếp theo. |  |
| **Extension Points:** | Quản trị viên xem lịch sử build, kiểm tra lỗi và yêu cầu retry; hệ thống có thể theo dõi hàng đợi build và trạng thái gói. |  |
| **Triggers:** | (1) Bộ lọc gói lần đầu được mobile yêu cầu; (2) POI được thêm/loại khỏi phạm vi, đổi ACTIVE/INACTIVE, metadata, vị trí, bán kính Geofence, khu vực hoặc danh mục; (3) nội dung PUBLISHED hoặc audio/hình ảnh của nội dung đang phân phối thay đổi. |  |
| **Assumptions:** | Các gói logic được xác định theo khu vực, ngôn ngữ và danh mục tùy chọn. POI ACTIVE phải đáp ứng điều kiện tiếng Anh PUBLISHED kèm audio hợp lệ do backend tự kiểm tra trong Use Case kích hoạt POI. Lượt rebuild có thể chạy tự động nhưng gói đã PUBLISHED phải tiếp tục phục vụ mobile trong thời gian build. |  |
| **Preconditions:** | Có dữ liệu khu vực/ngôn ngữ; hệ thống lưu trữ và phân phối manifest/asset hoạt động; đã có sự kiện thay đổi hoặc yêu cầu gói mới. Với gói có item, các POI/content/audio phải đạt điều kiện phát hành. |  |
| **Post Conditions:** | **Thành công:** Package logic có phiên bản PUBLISHED mới, manifest và item hợp lệ; phiên bản chỉ tăng sau khi công bố thành công. **Không thay đổi:** giữ nguyên phiên bản. **Thất bại:** không phát hành dữ liệu chưa xác minh và không làm mất bản PUBLISHED cũ; lần build đầu có thể ở BUILDING/FAILED cho tới khi có bản hợp lệ. |  |
| **Preferences:** | Một package_key chỉ đại diện một bộ lọc; gộp yêu cầu rebuild trùng; không gián đoạn phân phối; tái sử dụng asset; có thông tin trạng thái build; mobile tự quyết định tải/cập nhật. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 10-11-2026 |  |

## Quy tắc nghiệp vụ cần thống nhất

1. **Tự động build trên server, không tự động download trên mobile:** Server chủ động tạo lại gói khi có thay đổi liên quan; ứng dụng mobile chỉ hiển thị **“Có bản cập nhật”**, người dùng nhấn **“Cập nhật”** thì mới tải phần chênh lệch. Sau mất mạng, việc tiếp tục tải vẫn do người dùng chủ động.
2. **Thời điểm đưa POI vào gói:** POI chỉ được đưa vào manifest khi đã **ACTIVE**; nội dung tương ứng phải **PUBLISHED** và có audio hợp lệ. Publish content cho POI đang INACTIVE chưa làm POI xuất hiện trong gói.
3. **Ngôn ngữ:** Một package chứa nội dung của đúng ngôn ngữ được chọn; không tự thay bằng bản tiếng Anh khi thiếu content phù hợp. Tiếng Anh là điều kiện kích hoạt POI, không phải ngôn ngữ thay thế tự động cho gói offline khác.
4. **Không thay bản đang phát hành trong lúc build:** Bản PUBLISHED hiện tại vẫn được cung cấp, kể cả khi đang build bản tiếp theo hoặc build thất bại. Nếu chưa từng có bản thành công thì trạng thái có thể BUILDING/FAILED.
5. **Phiên bản gói:** `package_version` bắt đầu từ 1 và chỉ tăng khi manifest cùng metadata đã hợp lệ và được phát hành thành công. Những yêu cầu không tạo khác biệt thực tế không làm tăng phiên bản.
6. **Manifest và asset:** Gói phân phối metadata và tham chiếu đến tệp ảnh/audio dùng chung, kèm checksum và dung lượng. Không yêu cầu tạo một file ZIP chứa trùng toàn bộ dữ liệu cho mỗi gói.
7. **Tác động thay đổi:** Khi POI bị INACTIVE, đổi khu vực, danh mục hoặc ngôn ngữ content được Publish, hệ thống xác định **các package_key liên quan** rồi rebuild; không xóa ngay nguồn POI/content/audio hoặc tệp còn được phiên bản đang phục vụ tham chiếu.

## Ví dụ tình huống

| Tình huống | Xử lý mong đợi |
| :--- | :--- |
| POI vừa được tạo, vẫn INACTIVE | Không thêm vào gói offline. |
| POI có nội dung tiếng Anh PUBLISHED và audio tốt, người quản trị chọn ACTIVE | Backend tự kiểm tra điều kiện kích hoạt; nếu ACTIVE thành công, các gói phù hợp được đưa vào diện rebuild. |
| Publish bản tiếng Việt mới cho POI ACTIVE | Rebuild các gói ngôn ngữ tiếng Việt có chứa POI đó. Gói tiếng Anh không đổi nếu dữ liệu của nó không bị ảnh hưởng. |
| Đổi tọa độ hoặc hình ảnh POI ACTIVE | Rebuild các gói liên quan vì metadata/asset đã thay đổi. |
| Server đang rebuild v2, mobile yêu cầu tải | Mobile vẫn nhận thông tin v1 PUBLISHED; khi v2 được phát hành mới thấy bản cập nhật. |
| Rebuild v2 thất bại | v1 PUBLISHED vẫn có thể tải và sử dụng; không tăng version. |
| Mobile đang có v1, server phát hành v2 | Mobile hiển thị **“Có bản cập nhật”**; **không tự tải v2**. |
| Mobile chưa từng yêu cầu bộ lọc `region + language + category` này | Server tạo gói logic BUILDING và tự build lần đầu; đến khi PUBLISHED, mobile mới có bản tải được. |

## Ranh giới với các Use Case khác

- **UC-WEB-POI-01:** Quản trị POI, kiểm duyệt/Publish nội dung, kích hoạt POI; sau thay đổi hợp lệ, phát sinh nhu cầu rebuild package. Không tự thay `package_version` trong UC này.
- **UC-MOBILE-OFFLINE-01:** Mobile kiểm tra phiên bản, hiển thị trạng thái đã tải/có cập nhật và **chỉ tải/cập nhật khi người dùng nhấn nút**. `READY` là trạng thái local sau khi tải và kiểm tra thành công, khác với `PUBLISHED` trên server.
- **UC-MOBILE-MAP-01:** Bản đồ nền đóng gói sẵn cùng app, không phải asset cần build vào gói nội dung offline.

## Nguồn đối chiếu

- `docs/database-design.md`: nhóm **2.2 Point Of Interest**, **2.3 Offline Content Distribution** và luồng **4.1 Tải gói offline**.
- Đây là đặc tả nghiệp vụ trước khi triển khai; các thông báo về tiến trình build là thông báo trên màn hình quản trị hoặc trong nhật ký build, không phải thông báo tự đẩy xuống thiết bị du khách.