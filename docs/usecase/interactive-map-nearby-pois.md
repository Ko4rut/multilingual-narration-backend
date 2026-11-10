# UC-MOBILE-MAP-01 — Xem bản đồ và khám phá POI lân cận

| Use case number: | UC-MOBILE-MAP-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Xem bản đồ tương tác và danh sách điểm tham quan lân cận |  |
| **Actor(s):** | Khách du lịch (Tourist); thành phần hỗ trợ: Mobile Application, dịch vụ vị trí, bản đồ và dữ liệu POI |  |
| **Maturity:** | Specified — mô tả nghiệp vụ mục tiêu dựa trên giao diện Mobile hiện có; không khẳng định mọi chức năng đã được triển khai |  |
| **Summary:** | Du khách mở tab **Map** để xem vị trí hiện tại và các điểm tham quan (POI) trong bán kính **5 km** quanh người dùng khi có vị trí GPS hợp lệ. Giao diện có bản đồ và **Bottom Sheet** ở phía dưới; du khách có thể vuốt thanh kéo lên/xuống, cuộn danh sách, tìm POI theo tên và chọn POI để xem chi tiết. Khi có Internet, ứng dụng lấy POI ACTIVE từ hệ thống; khi không có Internet, dùng POI từ package offline **READY** nếu đã tải. Lớp nền bản đồ được đóng gói sẵn theo ứng dụng nên có thể hiển thị khi không có Internet; việc tải dữ liệu POI online hoặc sử dụng POI offline là quy trình độc lập với lớp nền bản đồ. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Du khách chọn tab **Map** trên ứng dụng. |  |
|  |  | 2\. Ứng dụng hiển thị trạng thái “Đang xác định vị trí của bạn...” trong lúc kiểm tra quyền vị trí và lấy tọa độ hiện tại. **A1, E1** |
|  |  | 3\. Ứng dụng kiểm tra khả năng lấy dữ liệu POI: có Internet thì nhận danh sách POI ACTIVE; nếu không kết nối được thì kiểm tra dữ liệu offline trong package READY. **A2, A3, E2** |
|  |  | 4\. Ứng dụng hiển thị lớp nền bản đồ có sẵn trong ứng dụng và vị trí người dùng (nếu GPS hợp lệ). Dữ liệu POI được chọn từ nguồn tại bước 3. **A1, A3** |
|  |  | 5\. Khi có tọa độ GPS hợp lệ, hệ thống tính khoảng cách địa lý đến từng POI và chỉ giữ POI có khoảng cách **≤ 5.000 m (5 km)**; sắp xếp theo khoảng cách tăng dần rồi hiển thị marker trên bản đồ và các POI card tại **Bottom Sheet** (ảnh, danh mục, tên, mô tả ngắn, khoảng cách). **A1, E3** |
|  | 6\. Du khách vuốt **thanh kéo** của Bottom Sheet lên hoặc chạm vào thanh kéo. |  |
|  |  | 7\. Ứng dụng mở rộng Bottom Sheet để hiển thị thêm các POI card và ô tìm kiếm; du khách có thể cuộn danh sách trong sheet, hoặc kéo thanh xuống để thu gọn mà không rời màn Map. **A4** |
|  | 8\. Du khách nhập từ khóa vào ô **Search point of interest...** hoặc cuộn danh sách để tìm POI. |  |
|  |  | 9\. Ứng dụng lọc danh sách theo **tên POI**, hiển thị các kết quả tương ứng; cho phép xóa từ khóa tìm kiếm. **A5, E4** |
|  | 10\. Du khách chạm vào một **POI card** trên Bottom Sheet hoặc marker tương ứng trên bản đồ. |  |
|  |  | 11\. Ứng dụng mở trang chi tiết của POI đã chọn; người dùng có thể xem thông tin và chủ động phát narration từ trang chi tiết theo Use Case phát thuyết minh riêng. **E5** |
|  | 12\. Du khách quay lại bản đồ hoặc nhấn nút xác định vị trí hiện tại. |  |
|  |  | 13\. Ứng dụng trở về màn Map; khi có vị trí hợp lệ, nút định vị đưa tâm bản đồ về tọa độ của người dùng. **E1** |
| **Alternative Paths:** | **A1 — Không có quyền hoặc chưa có vị trí:** Tại bước 2 hoặc bước 5, nếu du khách không cấp quyền hoặc chưa có mẫu GPS đáng tin cậy, ứng dụng vẫn hiển thị bản đồ và POI thuộc khu vực mặc định/đã tải (nếu có). **Không áp dụng bộ lọc bán kính 5 km khi thiếu tâm GPS**, không gắn nhãn “POI trong 5 km” và không hiển thị khoảng cách giả; tiếp tục bước 3 (khi mới mở Map) hoặc bước 6 (khi đã có danh sách). Đây là yêu cầu nghiệp vụ mục tiêu; màn Map hiện tại cần điều chỉnh để thực hiện được.<br><br>**A2 — Có Internet:** Tại bước 3, nếu kết nối và hệ thống cung cấp dữ liệu thành công, ứng dụng dùng POI **ACTIVE** đang công khai để hiển thị; tiếp tục bước 4.<br><br>**A3 — Không có Internet nhưng đã tải offline:** Tại bước 3, nếu không có kết nối nhưng đã có package **READY** chứa POI, ứng dụng dùng snapshot POI trên thiết bị và hiển thị “Đang sử dụng dữ liệu điểm tham quan đã tải xuống.”. Lớp nền bản đồ vẫn hiển thị từ tài nguyên đi kèm ứng dụng, không cần tải tile qua Internet; tiếp tục bước 4.<br><br>**A4 — Thu gọn hoặc mở rộng Bottom Sheet:** Tại bước 6 hoặc 7, nếu du khách vuốt thanh kéo xuống hoặc nhấn lại thanh kéo, sheet thu gọn; khi kéo lên hoặc nhấn lại, sheet mở rộng. Việc **cuộn bên trong danh sách** không được hiểu là yêu cầu thu gọn toàn bộ sheet; quay lại bước 7 hoặc tiếp tục bước 8.<br><br>**A5 — Xóa từ khóa tìm kiếm:** Tại bước 9, nếu du khách chọn biểu tượng xóa ô tìm kiếm, ứng dụng xóa từ khóa và hiển thị lại danh sách POI hiện có; quay lại bước 8. |  |
| **Exception Paths:** | **E1 — Không thể lấy vị trí GPS:** Tại bước 2 hoặc 13, nếu dịch vụ định vị tắt, không có quyền hoặc không lấy được tọa độ, hiển thị “Không thể xác định vị trí hiện tại. Bạn vẫn có thể khám phá các điểm tham quan.”; không tính khoảng cách khi thiếu tọa độ tin cậy; tiếp tục bước 3 (nếu đang mở Map) hoặc quay lại bước 12 (nếu đang nhấn định vị).<br><br>**E2 — Không có Internet và chưa tải POI offline:** Tại bước 3, nếu không thể lấy POI từ hệ thống và không có package READY chứa POI, hiển thị “Chưa có dữ liệu điểm tham quan. Vui lòng kết nối Internet hoặc tải nội dung ngoại tuyến.”; **vẫn hiển thị bản đồ nền có sẵn**, Bottom Sheet ở trạng thái trống và kết thúc luồng tải POI hiện tại.<br><br>**E3 — Không có POI trong bán kính 5 km:** Tại bước 5, nếu GPS hợp lệ nhưng không có POI nào có tọa độ hợp lệ và khoảng cách ≤ 5 km, hiển thị “Không tìm thấy điểm tham quan nào trong phạm vi 5 km.”; vẫn giữ nền bản đồ và Bottom Sheet trống, cho phép tìm kiếm sau khi có dữ liệu mới; tiếp tục bước 8. Nếu thiếu GPS, áp dụng A1 thay vì kết luận không có POI trong 5 km.<br><br>**E4 — Tìm kiếm không có kết quả:** Tại bước 9, nếu không có tên POI khớp từ khóa, hiển thị “Không tìm thấy điểm tham quan.” và “Hãy thử tìm tên khác.”; quay lại bước 8.<br><br>**E5 — POI không còn khả dụng:** Tại bước 11, nếu POI được chọn không có dữ liệu chi tiết hợp lệ hoặc server xác nhận đã INACTIVE, hiển thị “Điểm tham quan này hiện không khả dụng.”; không mở trang lỗi và quay lại bước 10. Khi offline, dữ liệu chỉ phản ánh trạng thái snapshot đã tải. |  |
| **Extension Points:** | Có thể mở rộng lọc theo danh mục, chọn vùng bản đồ để tải POI khác, gom cụm marker khi dày đặc và điều hướng qua ứng dụng bản đồ ngoài. Các chức năng này không bắt buộc trong Use Case hiện tại. |  |
| **Triggers:** | Du khách mở tab Map, vuốt Bottom Sheet, tìm kiếm POI hoặc chọn một địa điểm. |  |
| **Assumptions:** | POI công khai online có trạng thái ACTIVE và tọa độ hợp lệ; offline dùng package READY. Khi GPS hợp lệ, POI lân cận là các POI nằm trong **5 km** theo khoảng cách đường chim bay từ người dùng, tính từ tọa độ thực tế, không dùng giá trị mock cố định. **Bán kính khám phá 5 km độc lập với `trigger_radius_meter` của Geofence**. Không có GPS thì hiển thị theo khu vực mặc định/đã tải, không khẳng định kết quả thuộc bán kính 5 km. |  |
| **Preconditions:** | Ứng dụng được mở và có tab Map; không yêu cầu đăng nhập. Quyền vị trí và Internet là điều kiện để bổ sung thông tin, không được coi là điều kiện bắt buộc để xem POI local đã có. |  |
| **Post Conditions:** | **Thành công:** Map hiển thị nền bản đồ đóng gói trong ứng dụng và các marker/POI card trong bán kính **5 km** khi có GPS tin cậy; danh sách được sắp xếp gần đến xa, Bottom Sheet có thể kéo và cuộn, người dùng mở được chi tiết POI. **Thiếu GPS:** Vẫn xem POI nhưng không hiển thị vị trí/khoảng cách không đáng tin cậy. **Thiếu mạng:** Dùng POI READY nếu có; nếu không có dữ liệu thì hiển thị trạng thái trống phù hợp. |  |
| **Preferences:** | Ưu tiên giao diện dễ sử dụng: nút định vị hiện tại; Bottom Sheet thu gọn/mở rộng bằng kéo hoặc chạm thanh kéo; cuộn danh sách độc lập; tìm theo tên và xóa nhanh. Lớp nền bản đồ luôn lấy từ tài nguyên đi kèm ứng dụng; không yêu cầu tải tile nền để khám phá POI. |  |
| **Author(s):** | MNR Documentation Team |  |
| **Date:** | 10-11-2026 |  |

## Mô tả giao diện Map và Bottom Sheet

- **Bản đồ:** sử dụng lớp nền đã đóng gói sẵn khi cài ứng dụng, có thể hiển thị không cần Internet. Nút định vị đưa camera về GPS hiện tại (khi có tọa độ). Việc tích hợp lớp nền offline này là yêu cầu mục tiêu, cần cập nhật cấu hình nguồn bản đồ trong mã nguồn Mobile.
- **Bottom Sheet:** nằm sát cạnh dưới, mặc định thu gọn còn thanh kéo; khi mở rộng chiếm khoảng **54% chiều cao màn hình** theo cấu hình giao diện hiện có. Có thể kéo lên/xuống hoặc nhấn thanh kéo để đổi trạng thái.
- **Ô tìm kiếm:** ở đầu Bottom Sheet với placeholder **“Search point of interest...”**; lọc danh sách **theo tên POI**, không mặc định tìm nội dung mô tả/danh mục.
- **POI card:** có ảnh đại diện, các badge danh mục, tên POI, mô tả ngắn và khoảng cách khi được tính; khi có GPS chỉ hiển thị card trong bán kính 5 km, gần trước xa sau; nhấn card là hành động yêu cầu mở chi tiết.
- **Danh sách:** cuộn theo chiều dọc bên trong Bottom Sheet, không bắt buộc thu sheet khi cuộn; danh sách trống có thông báo rõ ràng.
- **Không có GPS:** đặc tả mục tiêu cho phép xem POI từ nguồn dữ liệu hoặc khu vực mặc định mà không cần quyền vị trí; các POI này không được gọi là “trong bán kính 5 km” vì không xác định được tâm bán kính.

## Quy tắc dữ liệu Online và Offline

| Tình trạng | Dữ liệu POI | Lớp nền bản đồ | Cách hiển thị |
| --- | --- | --- | --- |
| Có Internet và tải POI thành công | POI ACTIVE công khai từ hệ thống | Đọc dữ liệu bản đồ có sẵn theo ứng dụng | Nếu có GPS: chỉ marker/card trong bán kính 5 km, gần trước xa sau; nếu không có GPS: theo A1 |
| Có Internet nhưng truy vấn POI lỗi, có local READY | Snapshot POI đã tải (có thể cũ) | Vẫn hiển thị bản đồ đóng gói sẵn | Lọc snapshot theo bán kính 5 km khi có GPS; thông báo dữ liệu có thể cũ |
| Không Internet, có package READY | POI từ `Local_POIs` | Vẫn hiển thị bản đồ đóng gói sẵn | Lọc marker/card trong 5 km khi có GPS; không tải thêm POI hay bản đồ nền |
| Không Internet, không có READY | Không có POI khả dụng | **Vẫn hiển thị bản đồ nền** | Bottom Sheet hiển thị trạng thái chưa có dữ liệu POI; hướng dẫn tải khi online |
| GPS không có quyền hoặc không tin cậy | POI online/offline vẫn có thể xem | Vẫn hiển thị bản đồ đóng gói sẵn | Không lọc 5 km; xem theo vùng mặc định/đã tải và không hiển thị khoảng cách giả |

**Quy tắc:** Mở Map không tải lớp nền bản đồ từ Internet. Chỉ dữ liệu POI là đối tượng cần truy vấn online hoặc đọc từ package offline `READY`. Không có package POI không được xem là lỗi hiển thị nền bản đồ.

**Lưu ý:** Bán kính khám phá mặc định của Map được chốt là **5 km** quanh GPS hiện tại. Không dùng bán kính kích hoạt tự động (`trigger_radius_meter`) làm ngưỡng lọc POI; hai giá trị phục vụ hai nghiệp vụ khác nhau.

## Quy tắc xác định POI lân cận trong bán kính 5 km

- **Tâm bán kính:** tọa độ GPS hiện tại có độ tin cậy phù hợp của người dùng.
- **Bán kính cố định:** `R = 5.000 m`; giữ POI thỏa `distance(user, poi) <= 5.000 m`. Khoảng cách tính theo đường chim bay trên mặt cầu Trái Đất (ví dụ Haversine), **không phải khoảng cách di chuyển theo đường bộ**.
- **Danh sách đầu vào:** POI `ACTIVE` từ server khi online; khi lỗi mạng hoặc offline thì dùng snapshot `Local_POIs` của package `READY` nếu có.
- **Lọc và hiển thị:** chỉ xét POI có tọa độ hợp lệ; lọc cùng một tập POI cho **marker trên Map** và **POI card trong Bottom Sheet**, rồi sắp xếp theo khoảng cách tăng dần. Tìm kiếm theo tên chỉ lọc tiếp trong tập POI đã thỏa bán kính, không mở rộng ra ngoài 5 km.
- **Cập nhật vị trí:** khi có mẫu GPS mới đủ tin cậy, hệ thống tính lại khoảng cách, danh sách và marker theo vị trí mới; không dùng `distanceMeters` cố định trong mock data.
- **Thiếu GPS:** không suy đoán tâm 5 km; áp dụng A1 và hiển thị danh sách theo khu vực mặc định/đã tải, không đưa ra khoảng cách giả.
- **Không có POI trong 5 km:** áp dụng E3 và hiển thị đúng thông báo; trường hợp này khác với **không có dữ liệu nguồn** (E2).
- **Độc lập Geofence:** bán kính khám phá 5 km **không** thay đổi bán kính kích hoạt tự động `trigger_radius_meter` của từng POI.

## Đối chiếu với mã nguồn Mobile tại thời điểm viết

Đã tham chiếu repository `mujin0422/multilingual-narration-mobile`, nhánh `main` tại các file:

- `src/features/map/components/MapController.tsx`
- `src/features/map/components/MapLibreMap.tsx`
- `src/features/map/components/BottomSheet.tsx`
- `src/features/map/hooks/useBottomSheet.ts`
- `src/features/map/hooks/usePoiSearch.ts`
- `src/features/map/hooks/useUserLocation.ts`
- `src/features/map/components/PoiCard.tsx`
- `src/features/map/constants/bottomSheet.ts`
- `src/features/map/data/mock-pois.ts`

**Đã có trên UI:** MapLibre, hiển thị vị trí người dùng, nút focus GPS, Bottom Sheet có kéo/chạm thanh, FlatList cuộn, ô tìm theo tên, POI card và trạng thái danh sách rỗng.

**Chưa hoàn thiện trong mã nguồn hiện tại:** Cấu hình `mapStyle.ts` vẫn tham chiếu raster tile URL của OpenStreetMap; cần thay bằng nguồn bản đồ offline được đóng gói cùng ứng dụng để phù hợp với yêu cầu này. MapController chưa truyền dữ liệu POI thật vào BottomSheet (đang dùng `MOCK_POIS`); MapLibreMap mới hiển thị marker của người dùng, **chưa render marker POI**; BottomSheet trong MapController chưa nhận `onPoiPress` để điều hướng sang POI Detail; quyền GPS bị từ chối hiện trả về màn thông báo thay vì cho xem Map/POI; khoảng cách trong `MOCK_POIS` đang là số cố định; chưa có **lọc bán kính 5 km và sắp xếp theo GPS thật** hoặc cơ chế chính thức để sử dụng package READY trên Map.

Những nội dung **chưa hoàn thiện** ở trên là hành vi yêu cầu trong Use Case, không phải khẳng định hệ thống đã chạy được. Các câu thông báo trong dấu ngoặc kép là đề xuất nội dung UI theo đặc tả.