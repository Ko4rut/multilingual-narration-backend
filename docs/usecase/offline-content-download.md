# UC-MOBILE-OFFLINE-01 — Tải và quản lý gói nội dung ngoại tuyến

| Use case number: | UC-MOBILE-OFFLINE-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Tải, cập nhật và quản lý gói nội dung offline |  |
| **Actor(s):** | Khách du lịch (Tourist); thành phần hỗ trợ: Mobile Application, hệ thống phân phối nội dung và bộ nhớ thiết bị |  |
| **Maturity:** | Specified — luồng nghiệp vụ mục tiêu, chưa khẳng định tất cả đã được triển khai |  |
| **Summary:** | Du khách chọn khu vực, ngôn ngữ và danh mục (nếu cần), sau đó tải gói nội dung để xem POI và nghe thuyết minh khi không có Internet. Ứng dụng chỉ cho sử dụng gói đã tải và kiểm tra đầy đủ (`READY`), hiển thị trạng thái **“Có bản cập nhật”** khi phát hiện phiên bản mới nhưng **chỉ tải cập nhật sau khi du khách nhấn “Cập nhật”**; đồng thời hỗ trợ tiếp tục lượt tải bị gián đoạn và quản lý dung lượng. Gói đang tải hoặc chưa xác minh không được sử dụng. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách mở chức năng **Nội dung ngoại tuyến / Offline Content**. |  |
|  |  | 2\. Ứng dụng hiển thị khu vực, ngôn ngữ, danh mục tùy chọn, danh sách gói đã tải (nếu có), dung lượng và trạng thái như **“Chưa tải”**, **“Đã tải”** hoặc **“Có bản cập nhật”** (nếu có kết quả kiểm tra phiên bản từ server). |
|  | 3\. Du khách chọn khu vực, ngôn ngữ và danh mục (nếu cần) để xem gói; nếu chưa có gói trên máy, du khách nhấn **Tải xuống**. Đối với gói đã tải, thao tác cập nhật thực hiện theo **A2**. |  |
|  |  | 4\. Khi có Internet, ứng dụng kiểm tra thông tin gói đã công bố và phiên bản mới nhất; thao tác kiểm tra **không tự khởi chạy tải xuống**. **A3, A7, E1, E2** |
|  |  | 5\. Ứng dụng so sánh với gói đã lưu: nếu có phiên bản mới, hiển thị **“Có bản cập nhật”** và nút **“Cập nhật”**; nếu người dùng chưa nhấn nút thì tiếp tục dùng gói READY cũ. **A1, A2** |
|  |  | 6\. **Chỉ sau khi** du khách chọn **Tải xuống** hoặc **Cập nhật**, ứng dụng hiển thị dung lượng bổ sung cần tải và kiểm tra bộ nhớ trống. **E3** |
|  | 7\. Du khách xác nhận **Tải xuống/Cập nhật** để bắt đầu tải; trong quá trình tải có thể chọn **Tạm dừng** hoặc **Hủy tải**. **A5** |  |
|  |  | 8\. Ứng dụng tải thông tin gói cùng các tệp POI, hình ảnh và âm thanh còn thiếu vào vùng lưu tạm; hiển thị tiến độ và kiểm tra tính toàn vẹn của dữ liệu. **A4, E4, E5** |
|  |  | 9\. Khi toàn bộ dữ liệu bắt buộc hợp lệ, ứng dụng lưu dữ liệu và đánh dấu phiên bản mới là **READY**; bản READY cũ chỉ bị thay thế sau khi lưu thành công. **E6** |
|  |  | 10\. Ứng dụng hiển thị “Đã tải gói nội dung thành công.” cho lần tải đầu, hoặc “Cập nhật gói nội dung thành công.” cho lần cập nhật; trạng thái trở về **“Đã tải”**. |
|  | 11\. Du khách mở một gói đã tải để sử dụng các POI và audio khi không có Internet. **E7** |  |
|  |  | 12\. Ứng dụng sử dụng dữ liệu thuộc gói READY, cho phép du khách xem dung lượng hoặc yêu cầu xóa gói. **A6, A7, E8** |
| **Alternative Paths:** | **A1 — Gói đã tải và còn mới:** Tại bước 5, nếu thiết bị đã có gói READY cùng phiên bản và dữ liệu còn nguyên vẹn, ứng dụng hiển thị “Gói nội dung đã được tải xuống.”, không tải lại; quay lại bước 3 để người dùng quản lý gói hoặc kết thúc luồng.<br><br>**A2 — Người dùng chủ động cập nhật gói:** Tại bước 5, nếu hệ thống phát hiện phiên bản mới, ứng dụng hiển thị **“Có bản cập nhật”** và nút **“Cập nhật”** nhưng không tự tải. Nếu du khách nhấn **“Cập nhật”**, tiếp tục bước 6 để kiểm tra dung lượng, xác nhận rồi mới tải phần dữ liệu thay đổi. Nếu không nhấn, bản READY cũ vẫn sử dụng bình thường; quay lại bước 3 hoặc kết thúc luồng.<br><br>**A3 — Gói đang được chuẩn bị:** Tại bước 4, nếu gói chưa có phiên bản được xuất bản và đang được hệ thống chuẩn bị, ứng dụng hiển thị “Gói nội dung đang được chuẩn bị. Vui lòng thử lại sau.”; quay lại bước 3 hoặc kết thúc luồng. Nếu đã có phiên bản PUBLISHED cũ, tiếp tục dùng phiên bản đó tại bước 5.<br><br>**A4 — Tiếp tục lượt tải bị gián đoạn:** Tại bước 8, nếu lượt tải bị gián đoạn hoặc ứng dụng vừa mở lại, hệ thống giữ tiến độ và hiển thị **“Tiếp tục tải”**; chỉ khi du khách nhấn **“Tiếp tục tải”** và có Internet, hệ thống mới tải phần còn thiếu; quay lại bước 8.<br><br>**A5 — Người dùng tạm dừng hoặc hủy tải:** Tại bước 7, nếu người dùng chọn **Tạm dừng** hoặc **Hủy tải**, hệ thống dừng lượt tải, giữ gói READY cũ (nếu có) và hiển thị “Đã tạm dừng tải gói nội dung.” hoặc “Đã hủy tải gói nội dung.”; quay lại bước 3.<br><br>**A6 — Sử dụng hoặc xóa gói đã tải:** Tại bước 12, nếu người dùng muốn xem hoặc xóa một gói, hệ thống hiển thị gói READY và dung lượng; khi xác nhận xóa, chỉ xóa dữ liệu không còn gói nào khác sử dụng. Hiển thị “Đã xóa gói nội dung.” khi thành công; quay lại bước 3 hoặc kết thúc luồng.<br><br>**A7 — Dùng gói đã tải khi mất Internet:** Tại bước 3 hoặc bước 12, nếu không có Internet nhưng đã có gói READY, ứng dụng vẫn cho sử dụng POI, nội dung và audio hợp lệ thuộc gói đó; hiển thị “Bạn đang sử dụng nội dung đã tải xuống.”; kết thúc luồng tải mới. |  |
| **Exception Paths:** | **E1 — Không có Internet để tải:** Tại bước 4, nếu thiết bị không kết nối Internet hoặc không truy cập được hệ thống, hiển thị “Không có kết nối Internet. Vui lòng kết nối mạng để tải nội dung.”; nếu có gói READY, giữ nguyên và cho phép sử dụng theo A7; quay lại bước 3 hoặc kết thúc luồng.<br><br>**E2 — Gói không khả dụng:** Tại bước 4, nếu không tìm được gói PUBLISHED phù hợp hoặc quá trình tạo gói thất bại mà chưa có phiên bản hợp lệ, hiển thị “Gói nội dung hiện chưa khả dụng. Vui lòng thử lại sau.”; quay lại bước 3.<br><br>**E3 — Không đủ bộ nhớ:** Tại bước 6, nếu dung lượng trống không đủ cho những tệp còn phải tải và lưu, hiển thị “Thiết bị không đủ dung lượng. Vui lòng giải phóng bộ nhớ và thử lại.”; không thay đổi gói READY hiện có; quay lại bước 3.<br><br>**E4 — Mất mạng hoặc tải bị lỗi giữa chừng:** Tại bước 8, nếu mất Internet, quá thời gian chờ hoặc tệp không thể tải, ứng dụng lưu tiến độ có thể khôi phục và hiển thị “Tải nội dung bị gián đoạn. Bạn có thể tiếp tục khi có kết nối Internet.”; quay lại bước 3, sau đó có thể tiếp tục theo A4.<br><br>**E5 — Nội dung tải về không hợp lệ:** Tại bước 8, nếu danh sách tệp không hợp lệ, phiên bản dữ liệu chưa được ứng dụng hỗ trợ, hoặc tệp audio/ảnh thiếu hay sai kích thước/checksum, ứng dụng không sử dụng gói mới và hiển thị “Không thể xác minh gói nội dung. Vui lòng tải lại hoặc cập nhật ứng dụng.”; giữ gói READY cũ; quay lại bước 3.<br><br>**E6 — Không thể lưu gói vào thiết bị:** Tại bước 9, nếu việc cập nhật cơ sở dữ liệu local thất bại, ứng dụng hủy thay đổi của phiên bản mới, không ghi READY giả và hiển thị “Không thể lưu gói nội dung. Vui lòng thử lại.”; giữ gói READY cũ; quay lại bước 3.<br><br>**E7 — Gói đã tải bị thiếu hoặc hỏng tệp:** Tại bước 11, nếu phát hiện tệp trong gói đã tải bị mất hoặc không còn hợp lệ, ứng dụng không phát tệp hỏng, hiển thị “Một số nội dung ngoại tuyến không khả dụng. Vui lòng kết nối Internet để tải lại.”; quay lại bước 3 hoặc kết thúc luồng.<br><br>**E8 — Không thể xóa gói:** Tại bước 12 theo nhánh A6, nếu không thể cập nhật dữ liệu local hoặc xóa dữ liệu an toàn, ứng dụng giữ trạng thái nhất quán và hiển thị “Không thể xóa gói nội dung. Vui lòng thử lại.”; quay lại bước 3. |  |
| **Extension Points:** | Có thể mở rộng chọn nhiều khu vực cùng lúc và thông báo khi có phiên bản gói mới. **Không tự động tải mới hoặc cập nhật**, kể cả khi có Wi-Fi; người dùng phải chủ động chọn thao tác. Các chức năng này chưa bắt buộc trong Use Case. |  |
| **Triggers:** | Du khách nhấn **“Tải xuống”**, **“Cập nhật”**, **“Tiếp tục tải”**, hoặc chọn sử dụng/xóa một gói đã tải. Việc kiểm tra và hiển thị phiên bản mới không phải tác nhân bắt đầu tải. |  |
| **Assumptions:** | Server phân phối gói theo khu vực, ngôn ngữ và danh mục tùy chọn; chỉ phiên bản PUBLISHED được cung cấp cho mobile. Nội dung offline là snapshot cố định theo ngôn ngữ đã chọn và không tự fallback tiếng Anh khi thiếu audio; bản đồ nền đã đóng gói trong ứng dụng, không phải một phần bắt buộc của lượt tải gói POI này. |  |
| **Preconditions:** | Ứng dụng đã cài đặt và có đủ quyền lưu dữ liệu cục bộ. Du khách không cần đăng nhập. Internet là điều kiện để tải mới/cập nhật, không bắt buộc để sử dụng một gói READY đã tải. |  |
| **Post Conditions:** | **Thành công:** Gói được lưu ở trạng thái READY với nội dung/asset bắt buộc đã xác minh, sử dụng được khi offline. **Tải thất bại hoặc bị hủy:** Không kích hoạt phiên bản tải dở; phiên bản READY cũ vẫn sử dụng được. **Xóa thành công:** Gỡ dữ liệu tham chiếu của gói và chỉ xóa tệp không còn gói nào khác dùng. |  |
| **Preferences:** | Hiển thị rõ trạng thái **“Có bản cập nhật”**, nút **“Cập nhật”**, tiến độ và dung lượng; chỉ tải khi người dùng xác nhận, cho phép tạm dừng/tiếp tục bằng thao tác chủ động; không làm mất dữ liệu cũ khi cập nhật lỗi; không yêu cầu tải lại ảnh/audio đã có và được xác minh; không coi dữ liệu lưu tạm là nội dung dùng offline. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 10-11-2026 |  |

## Quy tắc nghiệp vụ chính

- **Nguồn gói:** Người dùng chọn `region + language + category (tùy chọn)`. Ứng dụng chỉ tải một phiên bản gói đã `PUBLISHED`. Nếu server đang tạo phiên bản mới, bản PUBLISHED cũ (nếu có) vẫn được phân phối.
- **Tải lần đầu và cập nhật do người dùng quyết định:** Nếu chưa có gói, hiển thị **“Tải xuống”**. Nếu đã có gói, ứng dụng kiểm tra `package_version` và `manifest_checksum`; khi phát hiện bản mới, hiển thị **“Có bản cập nhật”** và **“Cập nhật”**, nhưng **không tự động tải**. Chỉ khi người dùng nhấn **“Cập nhật”** và xác nhận, hệ thống mới tải những asset chưa có hoặc chưa `VERIFIED`. Nếu phiên bản local cao hơn thông tin server, không tự hạ phiên bản mà kiểm tra lại thông tin.
- **Bảo vệ gói cũ:** Chỉ chuyển sang `READY` sau khi manifest và toàn bộ asset cần thiết được xác minh, sau đó transaction cập nhật local database hoàn tất. Mọi lỗi trước bước này đều phải giữ gói READY cũ.
- **Mất kết nối:** Tải bị gián đoạn lưu tiến độ/tệp `.part` và công việc tải trong `Local_Download_Jobs`. Khi Internet trở lại, ứng dụng hiển thị **“Tiếp tục tải”** để người dùng chủ động tiếp tục; không tự resume và không phát audio từ file `.part`.
- **Không có Internet:** Có thể dùng `Local_POIs`, `Local_Poi_Contents` và `Local_Assets` thuộc package READY. Nếu chưa có gói phù hợp, không tự tạo nội dung offline và yêu cầu kết nối khi muốn tải.
- **Ngôn ngữ:** Gói tải cho ngôn ngữ cụ thể. Khi offline không tự sử dụng tiếng Anh thay thế nếu package không chứa phiên bản phù hợp.
- **Xóa gói:** Xóa quan hệ của package trước; các asset được gói khác sử dụng vẫn được giữ. Bản đồ nền đóng gói cùng ứng dụng không bị xóa khi xóa gói POI.

## Phân biệt các trường hợp kết nối và dữ liệu

| Tình trạng | Kết quả mong đợi |
| --- | --- |
| Có Internet, chưa có gói local | Hiển thị **“Tải xuống”**; chỉ tải gói PUBLISHED khi người dùng nhấn và xác nhận. |
| Có Internet, đã có bản READY cùng phiên bản còn nguyên vẹn | Không tải lại; thông báo đã tải. |
| Có Internet, server có bản mới | Hiển thị **“Có bản cập nhật”** và nút **“Cập nhật”**; không tự tải. Khi người dùng nhấn và xác nhận mới tải phần thay đổi; giữ READY cũ tới khi hoàn tất. |
| Không có Internet, đã có gói READY | Vẫn xem POI và nghe audio offline từ gói; không tải mới. |
| Không có Internet, chưa có gói READY | Không thể tải; hướng dẫn kết nối mạng. |
| Mất Internet giữa lượt tải | Giữ tiến độ tạm, hiển thị **“Tiếp tục tải”** khi đủ điều kiện; không tự tiếp tục, không đánh dấu READY cho bản mới. |
| Server đang BUILDING phiên bản mới | Dùng bản PUBLISHED cũ nếu có; nếu chưa có, chờ hệ thống chuẩn bị. |
| File local bị mất/hỏng | Không dùng file đó; thông báo cần tải lại khi online. |

## Tiêu chí kiểm thử cốt lõi

1. Người dùng tải gói theo đúng khu vực/ngôn ngữ; khi tải hoàn tất có thể mở POI và phát audio ở chế độ máy bay.
2. Mất mạng giữa lượt tải không làm mất gói READY cũ và có thể tiếp tục khi kết nối được khôi phục.
3. Gói có file sai checksum hoặc chưa đủ dữ liệu không được đánh dấu READY.
4. Khi gói có phiên bản mới, ứng dụng hiển thị **“Có bản cập nhật”** và **“Cập nhật”**, không tải tự động; chỉ sau khi người dùng xác nhận mới tải dữ liệu thay đổi, không xóa asset đang được gói khác sử dụng.
5. Thiết bị không đủ dung lượng hoặc người dùng hủy tải thì không làm hỏng gói đã lưu.
6. Gói chỉ cho phép nội dung của ngôn ngữ đã tải khi offline; không tự fallback tiếng Anh.
7. Sau khi người dùng bỏ qua cập nhật, bản READY hiện tại vẫn mở được bình thường; khi kết nối được khôi phục, lượt tải dở không tự chạy lại.

## Đối chiếu thiết kế

- Nguồn nghiệp vụ: `docs/database-design.md`, mục **2.3**, **3.2–3.3** và **4.1**.
- Dữ liệu local chính: `Local_Offline_Packages`, `Local_Download_Jobs`, `Local_POIs`, `Local_Poi_Contents`, `Local_Package_Items` và `Local_Assets`.
- Tài liệu này là **Use Case đặc tả trước khi triển khai**. Không đưa endpoint, phương thức HTTP hay chi tiết công nghệ server vào bảng Use Case.
- Tài liệu Map đã chốt bản đồ nền đóng gói cùng ứng dụng; gói offline ở Use Case này chỉ quản lý POI và các tài nguyên thuyết minh liên quan.