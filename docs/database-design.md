# DATABASE DESIGN - MULTILINGUAL AUTOMATIC NARRATION SYSTEM

# 1. OVERVIEW

**_Tổng quan về đề tài_**

- Hệ thống được xây dựng nhằm cung cấp cho khách du lịch trong và ngoài nước một ứng dụng phát thuyết minh tự động đa ngôn ngữ tại các điểm tham quan, hỗ trợ trải nghiệm tham quan tự túc mà không bắt buộc phải có hướng dẫn viên.
- Khách du lịch không cần đăng nhập để sử dụng các chức năng chính của ứng dụng. Ứng dụng có thể hoạt động dưới dạng anonymous client và sử dụng một installation_id được sinh ngẫu nhiên trên thiết bị nếu cần phục vụ đồng bộ hoặc thống kê.
- Các điểm tham quan, nội dung thuyết minh, tệp âm thanh và gói dữ liệu ngoại tuyến được quản lý tập trung trên hệ thống quản trị.
- Ứng dụng mobile có thể tải dữ liệu cần thiết về thiết bị để tiếp tục hoạt động trong trường hợp mất kết nối Internet.

**_Database được thiết kế để hỗ trợ:_**

- Quản lý người dùng quản trị và phân quyền.
- Quản lý phiên đăng nhập của người dùng quản trị.
- Quản lý các điểm tham quan và mã QR đi kèm.
- Quản lý danh mục, khu vực và ngôn ngữ.
- Quản lý nội dung thuyết minh đa ngôn ngữ theo phiên bản.
- Quản lý các tệp audio được thu âm hoặc sinh bằng Text-to-Speech.
- Quản lý gói nội dung ngoại tuyến cho khách du lịch tải xuống.
- Ghi nhận lịch sử nghe nhằm phục vụ thống kê và phân tích.
- Ghi nhận nhật ký thao tác của người dùng quản trị.
- Hỗ trợ đồng bộ phiên bản giữa dữ liệu trên server và dữ liệu đã lưu trên thiết bị.

# 2. LIST OF TABLES AND DESCRIPTIONS

## 2.1 GROUP 1: AUTHENTICATION AND AUTHORIZATION

Nhóm chịu trách nhiệm quản lý thông tin người dùng quản trị, phiên đăng nhập, vai trò và quyền truy cập trong hệ thống. Nhóm này hỗ trợ hai chức năng chính:

- **Authentication (Xác thực)**: Xác định danh tính của người dùng khi đăng nhập vào hệ thống.
- **Authorization (Phân quyền)**: Xác định người dùng được phép truy cập chức năng nào và thực hiện những hành động nào trên từng chức năng.

Cơ chế phân quyền được xây dựng theo mô hình Role-Based Access Control (RBAC). Mỗi người dùng được gán một vai trò; mỗi vai trò có thể sở hữu nhiều quyền; mỗi quyền được xác định dựa trên sự kết hợp giữa một **chức năng** và một **hành động** cụ thể.

### 2.1.1 Manager_Users (Người dùng quản trị)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin tài khoản của người dùng sử dụng hệ thống quản trị web, bao gồm thông tin định danh, thông tin xác thực, vai trò và trạng thái tài khoản.

Thông tin về từng phiên đăng nhập không được lưu trực tiếp tại bảng này mà được quản lý riêng trong bảng **User_Sessions**, giúp một tài khoản có thể có nhiều phiên đăng nhập độc lập.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type      | Nullable | Meaning                                                                                                                       |
| --------------- | --------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| id              | varchar   | No       | Mã định danh duy nhất của người dùng trong hệ thống, định dạng: `user-ddmmyy-xxxxxxxx`.                                       |
| role_id         | varchar   | No       | Mã vai trò được gán cho người dùng để xác định quyền truy cập của người dùng, liên kết đến bảng **Roles**.                    |
| email           | varchar   | No       | Địa chỉ email của người dùng, được sử dụng làm thông tin nhận diện và phục vụ quá trình đăng nhập vào hệ thống, đổi mật khẩu. |
| password_hash   | varchar   | No       | Mật khẩu đã được băm một chiều bằng Argon2id trước khi lưu; không phải dữ liệu mã hóa có thể giải mã.                         |
| full_name       | varchar   | No       | Họ và tên hoặc tên hiển thị của người dùng trong hệ thống.                                                                    |
| user_status     | enum      | No       | Trạng thái hoạt động của tài khoản người dùng, gồm: `ACTIVE`/`INACTIVE`.                                                      |
| created_at      | timestamp | No       | Thời điểm tài khoản người dùng được tạo trong hệ thống.                                                                       |
| last_updated_at | timestamp | No       | Thời điểm thông tin tài khoản được cập nhật gần nhất.                                                                         |
| last_login_at   | timestamp | Yes      | Thời điểm người dùng đăng nhập thành công gần nhất.                                                                           |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                     |
| ---------- | ------------- | ----------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất người dùng.      |
| **FK**     | `role_id`     | Tham chiếu đến `Roles(id)`.                     |
| **UNIQUE** | `email`       | Mỗi email chỉ được dùng cho một tài khoản.      |
| **ENUM**   | `user_status` | Thuộc kiểu `manager_user_status`, gồm `ACTIVE` và `INACTIVE`. |
| **INDEX**  | `role_id`     | Tăng tốc truy vấn người dùng theo vai trò.      |
| **INDEX**  | `user_status` | Tăng tốc lọc tài khoản theo trạng thái.         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `user_status`

```
Các trạng thái hiện tại gồm:
    - ACTIVE: tài khoản đang hoạt động và có thể đăng nhập nếu thông tin xác thực hợp lệ.
    - INACTIVE: tài khoản bị vô hiệu hóa và không được phép tạo phiên đăng nhập mới; các phiên còn hiệu lực phải bị thu hồi.
```

Email được chuẩn hóa về chữ thường và kiểm tra định dạng ở tầng ứng dụng trước
khi lưu; database bảo đảm tính duy nhất bằng ràng buộc `UNIQUE`.

### 2.1.2 User_Sessions (Phiên người dùng)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ các phiên đăng nhập của người dùng quản trị.

**_[2] Trường dữ liệu (Fields)_**

| Field              | Type      | Nullable | Meaning                                                                                                     |
| ------------------ | --------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| id                 | varchar   | No       | Mã định danh duy nhất của phiên đăng nhập, định dạng: `sess-ddmmyy-xxxxxxxx`.                               |
| user_id            | varchar   | No       | Người dùng sở hữu phiên đăng nhập, liên kết đến bảng **Manager_Users**.                                     |
| refresh_token_hash | varchar   | No       | SHA-256 của Refresh Token, được sử dụng để cấp lại Access Token mà không lưu token gốc.                     |
| expires_at         | timestamp | No       | Thời điểm hết hạn tuyệt đối của phiên; rotate Refresh Token không kéo dài thời điểm này.                    |
| created_at         | timestamp | No       | Thời điểm phiên đăng nhập được tạo.                                                                         |
| revoked_at         | timestamp | Yes      | Thời điểm phiên bị thu hồi hoặc đăng xuất. NULL nghĩa là phiên chưa bị thu hồi.                             |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to        | Description                                     |
| ---------- | -------------------- | ----------------------------------------------- |
| **PK**     | `id`                 | Khóa chính, định danh duy nhất phiên đăng nhập. |
| **FK**     | `user_id`            | Tham chiếu đến `Manager_Users(id)`.             |
| **UNIQUE** | `refresh_token_hash` | Mỗi refresh token hash chỉ xuất hiện một lần.   |
| **CHECK**  | `revoked_at`         | Nếu có giá trị thì phải `>= created_at`.        |
| **CHECK**  | `expires_at`         | Phải `> created_at`.                            |
| **INDEX**  | `user_id`            | Tăng tốc truy vấn phiên theo người dùng.        |
| **INDEX**  | `expires_at`         | Tăng tốc dọn dẹp phiên hết hạn.                 |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

Phiên không được cấp Access Token mới nếu đã hết hạn (`expires_at <= thời điểm hiện tại`), đã bị thu hồi (`revoked_at IS NOT NULL`) hoặc tài khoản sở hữu phiên không ở trạng thái `ACTIVE`.

Khi người dùng đăng xuất khỏi một thiết bị, chỉ phiên tương ứng cần được cập nhật `revoked_at`.

Quy trình cấp Access Token, quản lý JWT/Refresh Token, hash mật khẩu và thu hồi
phiên được mô tả tại [authentication-design.md](authentication-design.md).

### 2.1.3 Roles (Vai trò)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các vai trò được định nghĩa trong hệ thống.

Vai trò được sử dụng để nhóm các quyền truy cập và gán chúng cho người dùng. Thay vì gán quyền trực tiếp cho từng người dùng, hệ thống gán quyền cho vai trò, sau đó gán vai trò tương ứng cho người dùng.

Ví dụ một số vai trò:

- System Administrator
- Content Editor
- Content Reviewer

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type      | Nullable | Meaning                                                                                           |
| --------------- | --------- | -------- | ------------------------------------------------------------------------------------------------- |
| id              | varchar   | No       | Mã định danh duy nhất của vai trò trong hệ thống, định dạng: `role-xxxxxxxx`.                     |
| name            | varchar   | No       | Tên hiển thị của vai trò, dùng để nhận biết và phân biệt các nhóm quyền khác nhau trong hệ thống. |
| description     | text      | Yes      | Mô tả phạm vi và mục đích sử dụng của vai trò.                                                    |
| created_by      | varchar   | Yes      | Người dùng quản trị đã tạo vai trò, liên kết đến bảng **Manager_Users**.                          |
| last_updated_by | varchar   | Yes      | Người dùng quản trị cập nhật vai trò gần nhất, liên kết đến bảng **Manager_Users**.               |
| created_at      | timestamp | No       | Thời điểm vai trò được tạo trong hệ thống.                                                        |
| last_updated_at | timestamp | Yes      | Thời điểm thông tin vai trò được cập nhật gần nhất.                                               |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to   | Description                                      |
| ---------- | --------------- | ------------------------------------------------ |
| **PK**     | `id`            | Khóa chính, định danh duy nhất vai trò.          |
| **FK**     | `created_by`    | Tham chiếu đến `Manager_Users(id)`.              |
| **FK**     | `last_updated_by` | Tham chiếu đến `Manager_Users(id)`.            |
| **UNIQUE** | `name`          | Mỗi tên vai trò chỉ xuất hiện một lần.           |

### 2.1.4 Role_Permissions (Phân quyền theo vai trò)

**_[1] Ý nghĩa bảng (Description)_**

Là bảng trung gian dùng để thiết lập mối quan hệ nhiều-nhiều giữa Roles và Permissions.

Bảng xác định mỗi vai trò được phép sở hữu những quyền nào trong hệ thống. Một vai trò có thể có nhiều quyền và một quyền có thể được gán cho nhiều vai trò khác nhau.

**_[2] Trường dữ liệu (Fields)_**

| Field         | Type    | Nullable | Meaning                                                           |
| ------------- | ------- | -------- | ----------------------------------------------------------------- |
| role_id       | varchar | No       | Mã vai trò được cấp quyền, liên kết đến bảng **Roles**.           |
| permission_id | varchar | No       | Mã quyền được gán cho vai trò, liên kết đến bảng **Permissions**. |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to                | Description                                                     |
| --------- | ---------------------------- | --------------------------------------------------------------- |
| **PK**    | (`permission_id`, `role_id`) | Khóa chính phức hợp, đồng thời bảo đảm mỗi cặp chỉ xuất hiện một lần. |
| **FK**    | `role_id`                    | Tham chiếu đến `Roles(id)`.                                     |
| **FK**    | `permission_id`              | Tham chiếu đến `Permissions(id)`.                               |
| **INDEX** | `role_id`                    | Tăng tốc truy vấn danh sách quyền của một vai trò.              |

### 2.1.5 Permissions (Quyền truy cập)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ các quyền truy cập cụ thể có thể được cấp cho vai trò trong hệ thống.

Mỗi quyền được hình thành từ sự kết hợp giữa một chức năng Management_Functions và một hành động Actions.

Ví dụ: Một số chi tiết quyền nhỏ trong hệ thống

- POI Management + create
- POI Management + update
- POI Management + delete
- POI Management + read
- User Management + create
- User Management + update

**_[2] Trường dữ liệu (Fields)_**

| Field       | Type    | Nullable | Meaning                                                                                   |
| ----------- | ------- | -------- | ----------------------------------------------------------------------------------------- |
| id          | varchar | No       | Mã định danh duy nhất của quyền trong hệ thống, định dạng: `perm-xxxxxxxx`.               |
| function_id | varchar | No       | Mã chức năng mà quyền được áp dụng, liên kết đến bảng **Management_Functions**.           |
| action_id   | varchar | No       | Mã hành động được phép thực hiện trên chức năng tương ứng, liên kết đến bảng **Actions**. |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to | Description                                    |
| --------- | ------------- | ---------------------------------------------- |
| **PK**    | `id`          | Khóa chính, định danh duy nhất quyền.          |
| **FK**    | `function_id` | Tham chiếu đến `Management_Functions(id)`.     |
| **FK**    | `action_id`   | Tham chiếu đến `Actions(id)`.                  |
| **INDEX** | `function_id` | Tăng tốc truy vấn quyền theo chức năng.        |
| **INDEX** | `action_id`   | Tăng tốc truy vấn quyền theo hành động.        |

### 2.1.6 Management_Functions (Chức năng quản lý)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các chức năng hoặc module nghiệp vụ chính có trong hệ thống.

Các chức năng này được sử dụng làm đối tượng để xây dựng quyền truy cập. Một chức năng có thể hỗ trợ nhiều hành động khác nhau tùy thuộc vào nghiệp vụ của hệ thống.

Ví dụ: một số chức năng của hệ thống.

- POI Management
- Narration Content Management
- User Management
- Offline Package Management
- Listening Analytics

**_[2] Trường dữ liệu (Fields)_**

| Field       | Type    | Nullable | Meaning                                                                                                                                   |
| ----------- | ------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| id          | varchar | No       | Mã định danh duy nhất của chức năng trong hệ thống, định dạng: `func-xxxxxxxx`.                                                           |
| name        | varchar | No       | Tên hiển thị của chức năng hoặc module nghiệp vụ, có thể được sử dụng để hiển thị trên giao diện như Sidebar hoặc màn hình quản lý quyền. |
| description | text    | Yes      | Mô tả mục đích và phạm vi nghiệp vụ của chức năng quản lý.                                                                                |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                               |
| ---------- | ------------- | ----------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất chức năng. |
| **UNIQUE** | `name`        | Mỗi tên chức năng chỉ xuất hiện một lần.  |

### 2.1.7 Actions (Hành động được phép)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các loại hành động mà người dùng có thể được phép thực hiện đối với các chức năng trong hệ thống.

Các hành động được kết hợp với Management_Functions để tạo thành các Permissions cụ thể.

Ví dụ một số hành động:

- create
- read
- update
- delete
- approve
- publish
- generate_audio

**_[2] Trường dữ liệu (Fields)_**

| Field | Type    | Nullable | Meaning                                                                              |
| ----- | ------- | -------- | ------------------------------------------------------------------------------------ |
| id    | varchar | No       | Mã định danh duy nhất của hành động trong hệ thống, định dạng: `acts-xxxxxxxx`.      |
| name  | varchar | No       | Tên hiển thị của hành động mà người dùng có thể thực hiện trên một chức năng cụ thể. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                               |
| ---------- | ------------- | ----------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất hành động. |
| **UNIQUE** | `name`        | Mỗi tên hành động chỉ xuất hiện một lần.  |

## 2.2 GROUP 2: POINT OF INTEREST AND MULTILINGUAL NARRATION MANAGEMENT

Nhóm chịu trách nhiệm quản lý các điểm tham quan (Point of Interest - POI), nội dung thuyết minh đa ngôn ngữ và tệp audio tương ứng trong hệ thống.

Mỗi POI chứa các dữ liệu cần thiết để ứng dụng nhận diện vị trí, hiển thị thông tin và kích hoạt thuyết minh tự động, bao gồm tọa độ, bán kính kích hoạt, mã QR, hình ảnh, trạng thái và khu vực.

Một POI có thể thuộc nhiều danh mục khác nhau thông qua bảng ánh xạ Poi_Category_Mappings.

Mỗi POI cũng có thể có nhiều nội dung theo các ngôn ngữ khác nhau. Mỗi nội dung được quản lý theo phiên bản để một phiên bản mới có thể đi qua quy trình soạn thảo - phê duyệt mà không làm mất phiên bản đã được phát hành trước đó.

Các bảng thuộc nhóm:

- `Point_Of_Interests`
- `Poi_Category_Mapping`
- `Poi_Contents`
- `Content_Audios`

### 2.2.1 Point_Of_Interests (Điểm tham quan)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin về các điểm tham quan hoặc địa điểm mà hệ thống hỗ trợ thuyết minh tự động.

Mỗi POI bao gồm thông tin vị trí địa lý, hình ảnh, mã QR, mức độ ưu tiên và bán kính kích hoạt để ứng dụng xác định khi nào người dùng tiến gần đến địa điểm.

**_[2] Trường dữ liệu (Fields)_**

| Field                 | Type      | Nullable | Meaning                                                                                          |
| --------------------- | --------- | -------- | ------------------------------------------------------------------------------------------------ |
| id                    | varchar   | No       | Mã định danh duy nhất của POI trong hệ thống, định dạng: `poi-ddmmyy-xxxxxxxx`.                  |
| region_id             | varchar   | No       | Khu vực mà POI thuộc về.                                                                         |
| poi_image_url         | varchar   | No       | Đường dẫn đến hình ảnh đại diện của POI.                                                         |
| image_checksum_sha256 | varchar   | Yes      | Checksum SHA-256 của hình ảnh, giúp ứng dụng xác định file ảnh hiện có có cần tải lại hay không. |
| poi_qr_code           | varchar   | No       | Giá trị hoặc đường dẫn mã QR được sử dụng để nhận diện POI.                                      |
| poi_name              | varchar   | No       | Tên của địa điểm hoặc điểm tham quan.                                                            |
| poi_location          | varchar   | No       | Thông tin mô tả vị trí hoặc địa chỉ của POI                                                      |
| poi_status            | enum      | No       | Xác định POI hiện có được kích hoạt và sử dụng trong hệ thống hay không.                         |
| latitude              | decimal   | No       | Vĩ độ của POI                                                                                    |
| longitude             | decimal   | No       | Kinh độ của POI                                                                                  |
| trigger_radius_meter  | decimal   | No       | Bán kính kích hoạt nội dung tự động xung quanh POI                                               |
| created_by            | varchar   | No       | Người dùng quản trị tạo POI.                                                                     |
| last_updated_by       | varchar   | No       | Người dùng quản trị lần cuối cập nhập POI.                                                       |
| created_at            | timestamp | No       | Thời điểm POI được tạo trong hệ thống.                                                           |
| last_updated_at       | timestamp | No       | Thời điểm POI lần cuối được cập nhật trong hệ thống.                                             |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to             | Description                                                             |
| ---------- | ------------------------- | ----------------------------------------------------------------------- |
| **PK**     | `id`                      | Khóa chính, định danh duy nhất POI.                                     |
| **FK**     | `region_id`               | Tham chiếu đến `Regions(id)`.                                           |
| **FK**     | `created_by`              | Tham chiếu đến `Manager_Users(id)`.                                     |
| **FK**     | `last_updated_by`         | Tham chiếu đến `Manager_Users(id)`.                                     |
| **UNIQUE** | `poi_qr_code`             | Mỗi POI có một mã QR duy nhất.                                          |
| **UNIQUE** | `poi_location`            | Mỗi POI có một địa chỉ duy nhất (một POI hiện tại là một địa điểm lớn). |
| **CHECK**  | `latitude`                | Trong khoảng `[-90, 90]`.                                               |
| **CHECK**  | `longitude`               | Trong khoảng `[-180, 180]`.                                             |
| **CHECK**  | `trigger_radius_meter`    | `> 0`.                                                                  |
| **CHECK**  | `poi_status`              | Thuộc tập giá trị `('ACTIVE', 'INACTIVE')`.                             |
| **INDEX**  | `region_id`               | Tăng tốc truy vấn POI theo khu vực.                                     |
| **INDEX**  | `poi_status`              | Tăng tốc lọc POI theo trạng thái.                                       |
| **INDEX**  | (`latitude`, `longitude`) | Tăng tốc truy vấn không gian (nếu DBMS hỗ trợ).                         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `poi_status`

```
Các trạng thái của poi hiện tại gồm:
    - ACTIVE: đang hoạt động và POI được phép hiển thị và tham gia quá trình tạo gói offline.
    - INACTIVE: tạm ngưng/không hiển thị và POI không được đưa vào gói mới và không được kích hoạt đối với dữ liệu online mới.
```

[4.2] Điều kiện kích hoạt POI

```
Một POI chỉ được phép chuyển trạng thái từ INACTIVE sang ACTIVE khi đáp ứng đầy đủ các điều kiện sau:
    - POI phải có ít nhất một bản ghi Poi_Contents thuộc ngôn ngữ tiếng Anh (en).
    - Nội dung tiếng Anh phải có content_status = 'PUBLISHED'.
    - Nội dung tiếng Anh đã xuất bản phải có bản ghi Content_Audios tương ứng với tệp audio hợp lệ và sẵn sàng sử dụng.

Quy tắc khi tạo POI mới:
    - Khi tạo POI mới, trạng thái mặc định phải là INACTIVE.
    - Hệ thống không cho phép chuyển POI sang ACTIVE nếu chưa đáp ứng đầy đủ các điều kiện trên.
    - Khi POI đã ở trạng thái ACTIVE, hệ thống phải bảo đảm luôn tồn tại ít nhất một phiên bản nội dung tiếng Anh đang được PUBLISHED và có audio hợp lệ.
    - Không cho phép lưu thay đổi khiến POI đang ACTIVE mất phiên bản tiếng Anh khả dụng mà không có phiên bản thay thế.
    - Khi phiên bản tiếng Anh mới được PUBLISHED, phiên bản cũ được chuyển sang ARCHIVED theo quy tắc quản lý phiên bản nội dung.

Việc kiểm tra điều kiện kích hoạt phải được thực hiện tại Backend trước khi cập nhật poi_status.
```

[4.3] Trường `image_checksum_sha256`

```
Mục đích được dùng để:
    - phát hiện file tải xuống bị lỗi hoặc thiếu bytes;
    - kiểm tra tệp image đã có trên thiết bị có đúng với phiên bản server hay không;
    - tránh tải lại cùng một file khi nhiều package cùng tham chiếu đến cùng poi.
```

[4.4] Quy tắc đồng bộ metadata POI

```
Point_Of_Interests không sử dụng poi_version. Các thay đổi đối với POI được nhận diện thông qua dữ liệu hiện tại của POI và được phân phối xuống mobile thông qua phiên bản của Offline Package.

Khi một trong các dữ liệu ảnh hưởng đến ứng dụng mobile thay đổi, bao gồm:
    - poi_name;
    - poi_location;
    - latitude;
    - longitude;
    - trigger_radius_meter;
    - poi_status;
    - region_id;
    - hình ảnh hoặc image_checksum_sha256;
    - danh mục của POI;
thì hệ thống phải xác định các Offline Package chịu ảnh hưởng và thực hiện rebuild.

Trường package_version chỉ tăng khi bản build mới đã hoàn tất thành công và sẵn sàng phân phối.
```

[4.5] Quy tắc phân phối hình ảnh

```
Khi hình ảnh POI thay đổi:
    - Tính lại image_checksum_sha256.
    - Asset mới phải được upload thành công trước khi package mới được publish.
    - Các package có chứa POI này phải được đánh dấu cần rebuild.
    - Mobile sử dụng checksum để xác định có cần tải asset mới hay không.

Không ghi đè một asset đang được tham chiếu bởi manifest đã publish tại cùng một immutable URL. Khuyến nghị lưu asset bằng object key có chứa checksum hoặc một định danh bất biến tương đương.
```

### 2.2.2 Poi_Category_Mapping (Phân loại POI)

**_[1] Ý nghĩa bảng (Description)_**

Là bảng trung gian thiết lập quan hệ nhiều-nhiều giữa **Point_Of_Interests** và **Poi_Categories**.

Một POI có thể thuộc nhiều danh mục và một danh mục có thể chứa nhiều POI.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type    | Nullable | Meaning                                                       |
| --------------- | ------- | -------- | ------------------------------------------------------------- |
| poi_id          | varchar | No       | POI được phân loại, liên kết đến bảng **Point_Of_Interests**. |
| poi_category_id | varchar | No       | Danh mục của POI, liên kết đến bảng **Poi_Categories**.       |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                 | Description                                   |
| ---------- | ----------------------------- | --------------------------------------------- |
| **PK**     | (`poi_id`, `poi_category_id`) | Khóa chính phức hợp.                          |
| **FK**     | `poi_id`                      | Tham chiếu đến `Point_Of_Interests(id)`.      |
| **FK**     | `poi_category_id`             | Tham chiếu đến `Poi_Categories(id)`.          |
| **UNIQUE** | (`poi_id`, `poi_category_id`) | Mỗi cặp POI - danh mục chỉ xuất hiện một lần. |
| **INDEX**  | `poi_category_id`             | Tăng tốc truy vấn POI theo danh mục.          |

### 2.2.3 Poi_Contents (Nội dung thuyết minh của POI)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ các phiên bản nội dung thuyết minh của POI theo từng ngôn ngữ.

Một cặp POI - ngôn ngữ có thể có nhiều phiên bản nội dung. Điều này cho phép phiên bản mới ở trạng thái chờ duyệt hoặc bị từ chối trong khi phiên bản đã xuất bản trước đó vẫn tiếp tục được sử dụng cho ứng dụng mobile và các gói offline.

Trong phạm vi hiện tại, mỗi phiên bản Poi_Content có tối đa một Content_Audio. Thiết kế có thể mở rộng thành một-nhiều trong tương lai nếu cần nhiều giọng đọc, vùng miền hoặc nhiều nhà cung cấp TTS.

**_[2] Trường dữ liệu (Fields)_**

| Field            | Type      | Nullable | Meaning                                                                                                                    |
| ---------------- | --------- | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| id               | varchar   | No       | Mã định danh duy nhất của nội dung POI, định dạng: `cont-ddmmyy-xxxxxxxx`.                                                 |
| poi_id           | varchar   | No       | POI mà nội dung thuộc về, liên kết đến bảng **Point_Of_Interests**.                                                        |
| language_id      | varchar   | No       | Ngôn ngữ của nội dung, liên kết đến bảng **Languages**.                                                                    |
| narration_title  | varchar   | No       | Tiêu đề của nội dung thuyết minh.                                                                                          |
| narration_script | text      | No       | Nội dung văn bản dùng để thuyết minh dùng.                                                                                 |
| content_version  | integer   | No       | Số phiên bản nội dung trong phạm vi một cặp `poi_id` - `language_id`.                                                      |
| content_status   | enum      | No       | Trạng thái xử lý hoặc xuất bản của nội dung, gồm: `DRAFT`/`WAITING_APPROVAL`/`REJECTED`/`APPROVED`/`PUBLISHED`/`ARCHIVED`. |
| created_by       | varchar   | No       | Người dùng tạo nội dung, liên kết đến bảng **Manager_Users**.                                                              |
| approved_by      | varchar   | Yes      | Người dùng phê duyệt nội dung, liên kết đến bảng **Manager_Users**.                                                        |
| published_by     | varchar   | Yes      | Người dùng phát hành nội dung, liên kết đến bảng **Manager_Users**.                                                        |
| created_at       | timestamp | No       | Thời điểm nội dung được tạo, tức lưu bản DRAFT.                                                                            |
| approved_at      | timestamp | Yes      | Thời điểm nội dung được phê duyệt.                                                                                         |
| published_at     | timestamp | Yes      | Thời điểm nội dung được chính thức xuất bản.                                                                               |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                                | Description                                                                                         |
| ---------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **PK**     | `id`                                         | Khóa chính, định danh duy nhất nội dung POI.                                                        |
| **FK**     | `poi_id`                                     | Tham chiếu đến `Point_Of_Interests(id)`.                                                            |
| **FK**     | `language_id`                                | Tham chiếu đến `Languages(id)`.                                                                     |
| **FK**     | `created_by`                                 | Tham chiếu đến `Manager_Users(id)`.                                                                 |
| **FK**     | `approved_by`                                | Tham chiếu đến `Manager_Users(id)`.                                                                 |
| **FK**     | `published_by`                               | Tham chiếu đến `Manager_Users(id)`.                                                                 |
| **UNIQUE** | (`poi_id`, `language_id`, `content_version`) | Mỗi phiên bản nội dung trong một cặp POI - ngôn ngữ là duy nhất.                                    |
| **CHECK**  | `content_version`                            | `>= 1`.                                                                                             |
| **CHECK**  | `content_status`                             | Thuộc tập giá trị `('DRAFT', 'WAITING_APPROVAL', 'REJECTED', 'APPROVED', 'PUBLISHED', 'ARCHIVED')`. |
| **CHECK**  | `approved_at`                                | Nếu có giá trị thì phải `>= created_at`.                                                            |
| **CHECK**  | `published_at`                               | Nếu có giá trị thì phải `>= approved_at` (nếu `approved_at` có giá trị).                            |
| **INDEX**  | (`poi_id`, `language_id`, `content_status`)  | Tăng tốc truy vấn nội dung đang phân phối.                                                          |
| **INDEX**  | `content_status`                             | Tăng tốc lọc theo trạng thái.                                                                       |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `content_version`

```
Có các đặc điểm sau
    - Bắt đầu từ 1 cho phiên bản đầu tiên của một POI theo một ngôn ngữ.
    - Khi tạo nội dung thay thế cho phiên bản đã phát hành, tạo một dòng mới với content_version + 1; không ghi đè nội dung đã phát hành cũ.
    - ách này cho phép phiên bản cũ tiếp tục phục vụ người dùng trong khi phiên bản mới đang chờ duyệt.
```

[4.2] Trường `content_status`

```
Các trạng thái của content hiện tại gồm:
    - DRAFT: đang được soạn thảo, chưa gửi duyệt.
    - WAITING_APPROVAL: đã gửi duyệt và đang chờ người có quyền phê duyệt.
    - REJECTED: không được phê duyệt; đưa về trạng thái Draft để có thể tiếp tục chỉnh sửa.
    - APPROVED: đã được phê duyệt
    - PUBLISHED: phiên bản đang được phép phân phối đến ứng dụng mobile và gói offline.
    - ARCHIVED: phiên bản đã từng được phát hành nhưng không còn là phiên bản đang phân phối.

Quy tắc chuyển trạng thái:
    - Khi một phiên bản mới chuyển sang `PUBLISHED`, phiên bản `PUBLISHED` cũ của cùng `poi_id`-`language_id` sẽ được chuyển sang `ARCHIVED`.
    - Chỉ nội dung `PUBLISHED` được dùng khi xây dựng Offline_Packages.
```

[4.3] Quy trình Publish và TTS

```
Nếu hệ thống áp dụng nghiệp vụ "TTS khi Publish", thao tác Publish phải được xử lý theo thứ tự:
    - 1. Kiểm tra Poi_Content đang ở trạng thái APPROVED.
    - 2. Tạo audio TTS từ narration_title và narration_script.
    - 3. Upload audio lên object storage.
    - 4. Tính và xác minh audio_checksum_sha256, audio_size, audio_duration_sec và MIME type.
    - 5. Tạo hoặc cập nhật Content_Audios.
    - 6. Chỉ sau khi audio đã sẵn sàng người quản trị mới có thể chuyển Poi_Content sang PUBLISHED.
    - 7. Phiên bản PUBLISHED trước đó của cùng poi_id + language_id chuyển thành ARCHIVED.
    - 8. Đánh dấu các Offline Package liên quan cần rebuild.

Nếu TTS hoặc upload audio thất bại:
    - Poi_Content vẫn ở trạng thái APPROVED;
    - Phiên bản PUBLISHED hiện tại vẫn tiếp tục được phục vụ;
    - Không cập nhật package đang được phân phối;
    - Người quản trị có thể thực hiện một thao tác để retry quá trình TTS và sau đó thực hiện chuyển Poi_Content sang PUBLISHED.

Nhờ đó không tồn tại trạng thái PUBLISHED nhưng chưa có audio hợp lệ.
```

[4.4] Ngôn ngữ mặc định và cơ chế Fallback

```
Hệ thống sử dụng tiếng Anh (en) làm ngôn ngữ thuyết minh mặc định (Fallback Language), với quy tắc sau
    - Mỗi POI ở trạng thái ACTIVE bắt buộc phải có một phiên bản nội dung tiếng Anh đang được PUBLISHED và có audio hợp lệ.
    - Khi người dùng yêu cầu thuyết minh bằng một ngôn ngữ, hệ thống ưu tiên tìm nội dung PUBLISHED tương ứng với ngôn ngữ được chọn.
    - Nếu không tìm thấy nội dung PUBLISHED có audio khả dụng bằng ngôn ngữ được chọn, hệ thống tự động chuyển sang nội dung tiếng Anh đã được PUBLISHED của POI đó.
    - Nếu ngôn ngữ được chọn là tiếng Anh, hệ thống sử dụng trực tiếp phiên bản tiếng Anh đang được PUBLISHED.
    - Khi phát hành phiên bản tiếng Anh mới cho POI đang ACTIVE, hệ thống phải bảo đảm việc thay thế phiên bản không làm gián đoạn khả năng truy cập nội dung tiếng Anh đang được phân phối.
    - Cơ chế Fallback được áp dụng cho  chế độ Online.
```

### 2.2.4 Content_Audios (Âm thanh nội dung)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ metadata của tệp âm thanh thuyết minh tương ứng với một phiên bản Poi_Content.

Bảng không lưu trực tiếp bytes của audio trong cơ sở dữ liệu. Tệp được lưu trên object/file storage, còn bảng lưu URL, kích thước, thời lượng, nguồn tạo và checksum để phục vụ phân phối, kiểm tra toàn vẹn, nhận diện thay đổi và đồng bộ offline.

**_[2] Trường dữ liệu (Fields)_**

| Field                 | Type      | Nullable | Meaning                                                                                    |
| --------------------- | --------- | -------- | ------------------------------------------------------------------------------------------ |
| id                    | varchar   | No       | Mã định danh duy nhất của tệp âm thanh, định dạng: `audio-ddmmyy-xxxxxxxx`.                 |
| poi_content_id        | varchar   | No       | Nội dung POI tương ứng với tệp âm thanh, liên kết đến bảng **Poi_Contents**.               |
| audio_url             | varchar   | No       | Đường dẫn hoặc URL đến tệp âm thanh được lưu trữ.                                          |
| audio_size            | bigint    | No       | Kích thước của tệp âm thanh, thường được lưu theo đơn vị `byte`.                           |
| audio_source_type     | enum      | No       | Nguồn tạo audio, gồm: `RECORD`/`TTS`.                                                      |
| audio_duration_sec    | integer   | No       | Tổng thời lượng của tệp audio.                                                             |
| audio_mime_type       | varchar   | No       | MIME type của tệp, ví dụ: `audio/mpeg`, `audio/aac`.                                       |
| audio_checksum_sha256 | varchar   | No       | Checksum SHA-256 dùng để kiểm tra tính toàn vẹn và nhận diện tệp đã tồn tại trên thiết bị. |
| created_at            | timestamp | No       | Thời điểm bản ghi âm thanh được tạo.                                                       |
| last_updated_at       | timestamp | Yes      | Thời điểm bản ghi âm thanh cuối được cập nhật trong hệ thống.                              |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to        | Description                                                                 |
| ---------- | -------------------- | --------------------------------------------------------------------------- |
| **PK**     | `id`                 | Khóa chính, định danh duy nhất tệp âm thanh.                                |
| **FK**     | `poi_content_id`     | Tham chiếu đến `Poi_Contents(id)`.                                          |
| **UNIQUE** | `poi_content_id`     | Bảo đảm quan hệ 1-1 giữa nội dung và tệp âm thanh (trong phạm vi hiện tại). |
| **CHECK**  | `audio_size`         | `>= 0`.                                                                     |
| **CHECK**  | `audio_duration_sec` | `>= 0`.                                                                     |
| **CHECK**  | `audio_source_type`  | Thuộc tập giá trị `('RECORD', 'TTS')`.                                      |
| **CHECK**  | `audio_mime_type`    | Thuộc tập giá trị hợp lệ (ví dụ: `audio/mpeg`, `audio/aac`, ...).           |
| **INDEX**  | `audio_source_type`  | Tăng tốc lọc audio theo nguồn tạo.                                          |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `audio_checksum_sha256`

```
Mục đích được dùng để:
    - phát hiện file tải xuống bị lỗi hoặc thiếu bytes;
    - kiểm tra tệp audio đã có trên thiết bị có đúng với phiên bản server hay không;
    - tránh tải lại cùng một file khi nhiều package cùng tham chiếu đến cùng audio.
```

[4.2] Trường `audio_source_type`

```
Các trạng thái hiện tại gồm:
    - RECORD: audio được thu âm và tải lên bởi người quản trị.
    - TTS: audio được sinh tự động từ nội dung văn bản bằng dịch vụ Text-to-Speech.
```

[4.3] Quy tắc thay thế audio

```
Khi thay audio TTS bằng audio RECORD hoặc tạo lại TTS cho cùng một poi_content_id, quy trình sẽ được xử lý theo thứ tự:
    - 1. Upload file mới.
    - 2. Tính audio checksum mới.
    - 3. Cập nhật metadata của Content_Audios.
    - 4. Cập nhật audio_source_type.
    - 5. Cập nhật last_updated_at.
    - 6. Rebuild các Offline Package đang tham chiếu poi_content_id đó.

Không nên ghi đè trực tiếp bytes tại một URL bất biến mà manifest cũ đang tham chiếu. Khuyến nghị tạo physical asset mới theo checksum, ví dụ: /audio/<audio_checksum_sha256>.mp3

Sau đó cập nhật audio_url sang asset mới.
Asset cũ có thể được garbage-collect sau khi không còn manifest/package cần sử dụng.

```

## 2.3 GROUP 3: OFFLINE CONTENT DISTRIBUTION

Nhóm chịu trách nhiệm quản lý các gói dữ liệu được chuẩn bị để ứng dụng mobile có thể tải xuống và sử dụng khi không có kết nối Internet.

Trong thiết kế này, Offline Package được xem là một package logic + manifest, không nhất thiết là một file ZIP chứa lặp lại toàn bộ audio và hình ảnh. Các asset như audio/hình ảnh vẫn có URL và checksum riêng, nhờ đó ứng dụng có thể tái sử dụng asset đã tải từ một package khác thay vì tải lại.

### 2.3.1 Offline_Packages (Gói dữ liệu ngoại tuyến)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin về các gói dữ liệu được chuẩn bị để người dùng có thể tải về và sử dụng khi không có kết nối Internet.

Mỗi gói offline được xây dựng dựa trên danh mục POI, khu vực và ngôn ngữ cụ thể, giúp ứng dụng tải trước các nội dung cần thiết như dữ liệu POI và nội dung thuyết minh.

**_[2] Trường dữ liệu (Fields)_**

| Field                   | Type       | Nullable | Meaning                                                                                                                      |
| ----------------------- | ---------- | -------- | ---------------------------------------------------------------------------------------------------------------------------- |
| id                      | varchar PK | No       | Mã định danh duy nhất của gói dữ liệu offline, định dạng: `pack-ddmmyy-xxxxxxxx`                                              |
| category_id             | varchar FK | Yes      | Danh mục POI của gói dữ liệu, liên kết đến bảng **Poi_Categories**.                                                          |
| region_id               | varchar FK | No       | Khu vực của gói dữ liệu, liên kết đến bảng **Regions**.                                                                      |
| language_id             | varchar FK | No       | Ngôn ngữ của gói dữ liệu, liên kết đến bảng **Languages**.                                                                   |
| package_key             | varchar    | No       | Khóa ổn định đại diện cho bộ filter của package, dùng để tìm lại đúng package logic.                                         |
| package_name            | varchar    | No       | Tên hiển thị của package.                                                                                                    |
| package_url             | varchar    | Yes      | URL đến manifest hoặc metadata bundle của package sau khi build thành công. Có thể NULL khi package đang được build lần đầu. |
| package_version         | integer    | No       | Phiên bản hiện tại của package logic.                                                                                        |
| total_size              | bigint     | Yes      | Tổng dung lượng dự kiến cần tải đối với toàn bộ asset của package nếu thiết bị chưa có asset nào, đơn vị `byte`.             |
| package_checksum_sha256 | varchar    | Yes      | Checksum SHA-256 của manifest/metadata bundle để kiểm tra toàn vẹn.                                                          |
| package_status          | enum       | No       | Trạng thái build của package, gồm: `BUILDING`/`PUBLISHED`/`FAILED`.                                                          |
| schema_version          | integer    | No       | Phiên bản cấu trúc dữ liệu/manifest mà mobile cần hỗ trợ để đọc package.                                                     |
| created_at              | timestamp  | No       | Thời điểm package logic được tạo lần đầu.                                                                                    |
| last_updated_at         | timestamp  | No       | Thời điểm metadata/package version được cập nhật gần nhất.                                                                   |
| published_at            | timestamp  | Yes      | Thời điểm phiên bản package hiện tại được publish thành công.                                                                |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                | Description                                              |
| ---------- | ---------------------------- | -------------------------------------------------------- |
| **PK**     | `id`                         | Khóa chính, định danh duy nhất gói dữ liệu offline.      |
| **FK**     | `category_id`                | Tham chiếu đến `Poi_Categories(id)`.                     |
| **FK**     | `region_id`                  | Tham chiếu đến `Regions(id)`.                            |
| **FK**     | `language_id`                | Tham chiếu đến `Languages(id)`.                          |
| **UNIQUE** | `package_key`                | Mỗi bộ filter chỉ có một package logic.                  |
| **CHECK**  | `package_version`            | `>= 1`.                                                  |
| **CHECK**  | `schema_version`             | `>= 1`.                                                  |
| **CHECK**  | `total_size`                 | `>= 0` nếu có giá trị.                                   |
| **CHECK**  | `package_status`             | Thuộc tập giá trị `('BUILDING', 'PUBLISHED', 'FAILED')`. |
| **CHECK**  | `published_at`               | Nếu có giá trị thì phải `>= created_at`.                 |
| **INDEX**  | (`region_id`, `language_id`) | Tăng tốc truy vấn package theo khu vực + ngôn ngữ.       |
| **INDEX**  | `package_status`             | Tăng tốc lọc package theo trạng thái build.              |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `package_key`

```
Được tạo tự động lần đầu khi người dùng filter các trường dữ liệu trong đó trường category là optional.

Tạo package_key bằng biểu diễn canonical để tránh collision (va chạm), phiên bản hiện tại có 2 dạng.
    - package_key = region:<region_code>|lang:<language_code>.
    - package_key = cat:<category_code>|region:<region_code>|lang:<language_code>.

Quy tắc khởi tạo package
    - Khi người dùng đầu tiên yêu cầu một `package_key` chưa tồn tại thì hệ thống tạo package và build dữ liệu.
    - Những người dùng sau có cùng filter thì tái sử dụng package đã có.
```

[4.2] Trường `package_status`

```
Các trạng thái hiện tại gồm:
    - BUILDING: hệ thống đang tạo hoặc tái tạo metadata package.
    - PUBLISHED: package hiện tại đã sẵn sàng cho mobile.
    - FAILED: lần build gần nhất thất bại; hệ thống cần retry hoặc người quản trị kiểm tra.
```

[4.3] Trường `package_version`

```
Bắt đầu từ 1 cho phiên bản đầu tiên.
    - Khi build thành công phiên bản mới, tăng lên 1: package_version = package_version + 1.
    - Mobile chỉ ghi nhận version mới sau khi đã tải và xác minh dữ liệu cần thiết thành công.
```

[4.4] Quy tắc phân phối asset

```
Không đóng toàn bộ audio/hình ảnh vào từng package độc lập, nhằm tránh trùng lặp giữa nhiều package.

package_url nên trỏ đến manifest/metadata bundle.

Asset lớn (audio, hình ảnh) được tải thông qua URL riêng của chúng.
```

[4.5] Quy tắc build và publish package

```
Một package đã PUBLISHED không được làm mất khả năng sử dụng trong khi hệ thống đang xây dựng phiên bản tiếp theo.

Khi package đã có phiên bản đang hoạt động:
    - 1. Build manifest mới và danh sách item mới trong vùng staging.
    - 2. Không thay đổi package_version, package_url hoặc membership hiện tại trong quá trình build.
    - 3. Upload manifest mới.
    - 4. Xác minh checksum manifest.
    - 5. Xác minh các asset được manifest tham chiếu đã tồn tại.
    - 6. Trong một thao tác atomic/transaction:
            thay membership hiện tại bằng membership mới;
            tăng package_version;
            cập nhật package_url;
            cập nhật package_checksum_sha256;
            cập nhật total_size;
            cập nhật published_at.
    - 7. Sau commit, phiên bản mới mới được xem là package hiện tại.

Nếu rebuild thất bại, package PUBLISHED trước đó vẫn tiếp tục được sử dụng.

FAILED chỉ có nghĩa là lần build mới thất bại; không được làm mất bản package đã publish thành công trước đó.

Đối với lần build đầu tiên, khi chưa tồn tại version hợp lệ, trạng thái có thể là BUILDING hoặc FAILED.
```

[4.6] Các thay đổi làm package cần rebuild

```
Package phải được rebuild khi dữ liệu ảnh hưởng đến snapshot của package thay đổi, bao gồm:
    - POI được thêm hoặc loại khỏi khu vực/danh mục;
    - poi_status thay đổi;
    - tọa độ hoặc trigger_radius_meter thay đổi;
    - metadata POI được phân phối cho mobile thay đổi;
    - hình ảnh hoặc image checksum thay đổi;
    - Poi_Content mới được PUBLISHED;
    - Content_Audio của content đang publish thay đổi;
    - quan hệ Poi_Category_Mapping thay đổi;
    - POI chuyển từ region này sang region khác.

Chỉ sau khi build thành công mới tăng package_version.
```

**_[5] Giải thích và ví dụ_**

[5.1] Package logic?

```
Package logic (gói logic) là một dòng trong bảng Offline_Packages, đại diện cho một bộ filter duy nhất gồm: $(region, language, category?)$

Nó không phải là file .zip cụ thể, cũng không phải là bản build cụ thể. Nó là định danh nghiệp vụ cho một "loại gói" mà người dùng có thể yêu cầu.

Ví dụ: Ba dòng này là 3 package logic khác nhau, dù cùng khu vực.
| package_key          | Ý nghĩa                                          |
| -------------------- | ------------------------------------------------ |
| district1-vi         | Tất cả POI ở Quận 1, tiếng Việt.                 |
| history-district1-vi | Chỉ POI danh mục "lịch sử" ở Quận 1, tiếng Việt. |
| district1-en         | Tất cả POI ở Quận 1, tiếng Anh.                  |

Tại sao cần "logic"?
    - Vì nội dung bên trong có thể thay đổi theo thời gian (thêm POI, sửa audio, đổi ảnh...). Nếu mỗi lần thay đổi lại tạo một dòng mới --> bảng phình to, mobile khó biết đâu là gói mới nhất.
    - Nên giải pháplà : giữ nguyên dòng package logic, chỉ tăng package_version và cập nhật Offline_Package_Items.

Minh họa:

    Thời điểm T1:
    package_key = district1-vi
    package_version = 1
    package_url = .../v1/manifest.json

    Thời điểm T2 (thêm 3 POI mới):
    package_key = district1-vi <-- vẫn cùng dòng
    package_version = 2 <-- tăng lên
    package_url = .../v2/manifest.json <-- URL mới

==> Mobile cũ có package_version = 1 sẽ thấy có bản 2 ==> tải manifest mới ==> so sánh asset ==> chỉ tải phần thay đổi.
```

[5.2] Manifest là gì?

```
Manifest là file mô tả nội dung của package — thường ở dạng JSON — chứa danh sách asset và metadata để mobile biết cần tải gì.

Manifest không chứa audio/hình ảnh thật. Nó chỉ trỏ đến các asset đó.

Ví dụ manifest manifest.json:
{
    "package_key": "district1-vi",
    "package_version": 2,
    "schema_version": 1,
    "region_code": "district1",
    "language_code": "vi",
    "generated_at": "2026-10-04T10:00:00Z",
    "items": [
        {
        "poi_id": "poi-011024-0001",
        "narration_id": "cont-011024-0001",
        "audio_url": "https://cdn.../audio/cont-011024-0001.mp3",
        "audio_checksum": "a3f5...",
        "audio_size": 245120,
        "image_url": "https://cdn.../img/poi-011024-0001.jpg",
        "image_checksum": "b7c9...",
        "image_size": 51200
        },
        {
        "poi_id": "poi-011024-0002",
        "narration_id": "cont-011024-0002",
        "audio_url": "https://cdn.../audio/cont-011024-0002.mp3",
        "audio_checksum": "d1e2...",
        "audio_size": 198400,
        "image_url": "https://cdn.../img/poi-011024-0002.jpg",
        "image_checksum": "f4a6...",
        "image_size": 47800
        }
    ]
}

Mobile dùng manifest để:
    - 1. Biết package có version mới hay không (`package_version`).
    - 2. Biết cần tải asset nào (`items[].audio_url`, `items[].image_url`).
    - 3. Kiểm tra toàn vẹn file sau khi tải (`*_checksum`).
    - 4. Ước lượng dung lượng cần tải (`*_size`).
    - 5. Bỏ qua asset đã có sẵn (so sánh checksum với file local).
```

[5.3]. Quan hệ giữa package logic, manifest, và asset

```
┌─────────────────────────────────────────────────────────┐
│  Offline_Packages (1 dòng = 1 package logic)            │
│  ─────────────────────────────────────────────          │
│  package_key     = district1-vi                         │
│  package_version = 2                                    │
│  package_url     = https://cdn.../v2/manifest.json      │
│  checksum_sha256 = <checksum của manifest>              │
└────────────────────────┬────────────────────────────────┘
                         │ trỏ đến
                         ▼
┌─────────────────────────────────────────────────────────┐
│  manifest.json (file nhỏ, mô tả nội dung)               │
│  ─────────────────────────────────────────────          │
│  items: [                                               │
│    { poi_id, audio_url, image_url, checksum, size },    │
│    ...                                                  │
│  ]                                                      │
└────────────────────────┬────────────────────────────────┘
                         │ trỏ đến
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Asset thật (audio .mp3, ảnh .jpg)                      │
│  ─────────────────────────────────────────────          │
│  https://cdn.../audio/cont-011024-0001.mp3              │
│  https://cdn.../img/poi-011024-0001.jpg                 │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘

Ý tưởng cốt lõi:
    - Package logic = định danh nghiệp vụ (bộ filter).
    - Manifest = danh sách "cần tải gì" (nhẹ, thay đổi thường xuyên).
    - Asset = file thật (nặng, chia sẻ giữa nhiều package).

Nhờ tách 3 tầng như vậy:
    - Nhiều package có thể dùng chung asset (không trùng lặp).
    - Mobile chỉ tải manifest mới (~vài KB) để kiểm tra, thay vì tải lại toàn bộ.
    - Dễ dàng cache, CDN, và kiểm tra toàn vẹn.
```

### 2.3.2 Offline_Package_Items

**_[1] Ý nghĩa bảng (Description)_**

Lưu danh sách các thành phần mà một Offline_Package hiện đang tham chiếu.

Bảng đóng vai trò server-side manifest index, cho biết package chứa POI nào, nội dung nào, phiên bản nội dung nào và audio nào. Đây là dữ liệu quan trọng để kiểm tra package có cần rebuild và để mobile thực hiện tải tăng dần (incremental download).

Offline_Package_Items không nhằm tạo bản sao nội dung/audio. Các item chỉ tham chiếu đến dữ liệu gốc, vì vậy cùng một Poi_Content hoặc Content_Audio có thể được nhiều package sử dụng mà không cần tạo bản ghi nội dung/audio mới.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type       | Nullable | Meaning                                                                      |
| --------------- | ---------- | -------- | ---------------------------------------------------------------------------- |
| id              | varchar PK | No       | Mã định danh của item trong package, định dạng `pack-item-ddmmyy-xxxxxxxx`  |
| package_id      | varchar FK | No       | Package chứa item, liên kết đến bảng **Offline_Packages**.                   |
| poi_id          | varchar FK | No       | POI được đưa vào package, liên kết đến bảng **Point_Of_Interests**.          |
| poi_content_id  | varchar FK | No       | Phiên bản nội dung được package sử dụng, liên kết đến bảng **Poi_Contents**. |
| audio_id        | varchar FK | No       | Audio tương ứng được đưa vào package, liên kết đến bảng **Content_Audios**.  |
| content_version | integer    | No       | Phiên bản nội dung được ghi nhận tại thời điểm package được build.           |
| created_at      | timestamp  | No       | Thời điểm item được thêm vào package.                                        |
| last_updated_at | timestamp  | No       | Thời điểm snapshot version của item được cập nhật gần nhất.                  |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                    | Description                                        |
| ---------- | -------------------------------- | -------------------------------------------------- |
| **PK**     | `id`                             | Khóa chính, định danh duy nhất item trong package. |
| **FK**     | `package_id`                     | Tham chiếu đến `Offline_Packages(id)`.             |
| **FK**     | `poi_id`                         | Tham chiếu đến `Point_Of_Interests(id)`.           |
| **FK**     | `poi_content_id`                 | Tham chiếu đến `Poi_Contents(id)`.                 |
| **FK**     | `audio_id`                       | Tham chiếu đến `Content_Audios(id)`.               |
| **UNIQUE** | (`package_id`, `poi_content_id`) | Trong phạm vi hiện tại: một content - một audio.   |
| **CHECK**  | `content_version`                | `>= 1`.                                            |
| **INDEX**  | `package_id`                     | Tăng tốc truy vấn item theo package.               |
| **INDEX**  | `poi_content_id`                 | Kiểm tra content đang được package nào tham chiếu. |
| **INDEX**  | `audio_id`                       | Kiểm tra audio đang được package nào tham chiếu.   |
| **INDEX**  | `poi_id`                         | Kiểm tra POI đang được package nào tham chiếu.     |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `audio_id`

```
Mỗi Offline_Package_Items bắt buộc phải tham chiếu đến một Content_Audios thông qua audio_id.

Chỉ được đưa một Poi_Content vào Offline Package khi nội dung đó đã có audio hợp lệ tương ứng.

audio_id phải là audio thuộc đúng poi_content_id được lưu trong cùng item.

Nếu content chưa có audio hoặc audio chưa sẵn sàng thì item đó không được đưa vào package được publish.
```

[4.2] Trường `content_version`

```
content_version là phiên bản của Poi_Content tại thời điểm package được build.

Giá trị content_version phải được lấy trực tiếp từ Poi_Contents.content_version tương ứng với poi_content_id.

Không được cập nhật content_version trong Offline_Package_Items một cách độc lập với Poi_Contents.

Khi một phiên bản content mới được PUBLISHED, các package liên quan phải được rebuild để sử dụng poi_content_id, content_version và audio_id tương ứng với phiên bản mới.
```

[4.3] Quy tắc tái sử dụng dữ liệu

```
Một Poi_Content hoặc Content_Audio có thể được nhiều Offline Package cùng tham chiếu.

Việc một content hoặc audio đã tồn tại trong package khác không làm phát sinh bản sao mới của Poi_Contents hoặc Content_Audios.

Các package chỉ lưu quan hệ tham chiếu thông qua Offline_Package_Items.
```

[4.4] Quy tắc khi item bị loại khỏi package

```
Khi một POI hoặc content không còn thuộc phiên bản mới của package, Offline_Package_Items tương ứng được loại khỏi membership của package trong quá trình rebuild.

Việc loại item khỏi package không đồng nghĩa với việc xóa Poi_Content, Content_Audio hoặc physical asset tương ứng.

Physical asset chỉ được xóa khi không còn package hoặc manifest còn hiệu lực nào tham chiếu đến asset đó.
```

## 2.4 GROUP 4: VISITOR ACTIVITY AND ANALYTICS

Nhóm chịu trách nhiệm ghi nhận dữ liệu tương tác của khách du lịch với nội dung thuyết minh.

Các dữ liệu này có thể được sử dụng để thống kê số lượt nghe, thời lượng nghe, mức độ hoàn thành nội dung và mức độ quan tâm đến từng điểm tham quan.

Khách du lịch không cần tài khoản để sử dụng ứng dụng, do đó dữ liệu trong nhóm này không phụ thuộc vào Manager_Users.

Các bảng thuộc nhóm:

- `Listening_Histories`: Lịch sử nghe

### 2.4.1 Listening_Histories (Lịch sử nghe)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ lịch sử phát nội dung thuyết minh tại các POI.

Thông tin này có thể được sử dụng để thống kê số lượt nghe, thời lượng nghe thực tế và mức độ hoàn thành nội dung của từng POI.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type       | Nullable | Meaning                                                                                   |
| --------------- | ---------- | -------- | ----------------------------------------------------------------------------------------- |
| id              | varchar PK | No       | Mã định danh duy nhất của lượt nghe, định dạng: `listen-ddmmyy-xxxxxxxx`.                 |
| installation_id | UUID       | No       | Mã định danh ngẫu nhiên của một lần cài đặt ứng dụng.                                     |
| poi_id          | varchar FK | No       | Giúp biết POI được người dùng nghe thuyết minh, liên kết đến bảng **Point_Of_Interests**. |
| poi_content_id  | varchar FK | No       | Giúp biết ngôn ngữ/nội dung nào được nghe, liên kết đến bảng **Poi_Contents**.            |
| trigger_type    | enum       | No       | Cho biết cách thức audio thyết minh được kích hoạt, gồm: `AUTO_LOCATION`/`QR_CODE`.       |
| started_at      | timestamp  | No       | Thời điểm người dùng bắt đầu nghe nội dung.                                               |
| completed_at    | timestamp  | Yes      | Thời điểm người dùng nghe hoàn tất hoặc kết thúc nội dung.                                |
| duration_sec    | integer    | Yes      | Tổng thời gian đã nghe, tính bằng giây.                                                   |
| created_at      | timestamp  | No       | Thời điểm bản ghi lịch sử nghe được tạo.                                                  |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to                     | Description                                       |
| --------- | --------------------------------- | ------------------------------------------------- |
| **PK**    | `id`                              | Khóa chính, định danh duy nhất lượt nghe.         |
| **FK**    | `poi_id`                          | Tham chiếu đến `Point_Of_Interests(id)`.          |
| **FK**    | `poi_content_id`                  | Tham chiếu đến `Poi_Contents(id)`.                |
| **CHECK** | `trigger_type`                    | Thuộc tập giá trị `('AUTO_LOCATION', 'QR_CODE')`. |
| **CHECK** | `duration_sec`                    | `>= 0` nếu có giá trị.                            |
| **CHECK** | `completed_at`                    | `>= started_at` nếu có giá trị.                   |
| **INDEX** | (`poi_id`, `started_at`)          | Tăng tốc thống kê theo POI + thời gian.           |
| **INDEX** | (`installation_id`, `started_at`) | Truy vấn lịch sử của một thiết bị.                |
| **INDEX** | `poi_content_id`                  | Thống kê theo nội dung/ngôn ngữ.                  |
| **INDEX** | `trigger_type`                    | Tăng tốc thống kê theo hình thức kích hoạt.       |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `installation_id`

- Được sinh ngẫu nhiên bằng UUID khi ứng dụng chạy lần đầu;
- Lưu cục bộ trên thiết bị;
- Không sử dụng IMEI, serial number hoặc advertising ID;
- Sẽ thay đổi khi người dùng xóa ứng dụng và cài lại;

[4.2] Trường `trigger_type`

Các type hiện tại gồm:

- `AUTO_LOCATION`: hệ thống tự kích hoạt khi thiết bị đi vào bán kính của POI.
- `QR_CODE`: người dùng quét QR để mở/kích hoạt nội dung.

[4.3] Trường `duration_sec`

- Là tổng thời gian phát thực tế do player ghi nhận. Không nên luôn suy ra bằng `completed_at` - `started_at` vì người dùng có thể pause/resume.

[4.4] Quy tắc đồng bộ offline

- Khi thiết bị offline, event được lưu trong local SQLite và đồng bộ lên server sau khi có mạng.

## 2.5 GROUP 5: MASTER AND REFERENCE DATA

Nhóm lưu trữ các dữ liệu danh mục dùng chung trong toàn hệ thống.

Các dữ liệu này được nhiều module khác tham chiếu đến, bao gồm khu vực địa lý, ngôn ngữ được hỗ trợ và danh mục phân loại điểm tham quan.

Các bảng thuộc nhóm:

- `Regions`
- `Languages`
- `Poi_Categories`

### 2.5.1 Poi_Categories (Danh mục POI)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ các danh mục được sử dụng để phân loại POI.

Việc phân loại giúp hệ thống tổ chức, tìm kiếm, lọc dữ liệu và xây dựng các gói nội dung offline theo từng nhóm địa điểm.

**_[2] Trường dữ liệu (Fields)_**

| Field         | Type       | Nullable | Meaning                                 |
| ------------- | ---------- | -------- | --------------------------------------- |
| id            | varchar PK | No       | Mã định danh duy nhất của danh mục POI, định dạng: `cat-xxxxxxxx`. |
| category_name | varchar    | No       | Tên của danh mục POI.                   |
| category_code | varchar    | No       | Mã danh mục, ví dụ: ..., ..., ...       |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to   | Description                                                         |
| ---------- | --------------- | ------------------------------------------------------------------- |
| **PK**     | `id`            | Khóa chính, định danh duy nhất danh mục POI.                        |
| **UNIQUE** | `category_name` | Mỗi tên danh mục chỉ xuất hiện một lần.                             |
| **UNIQUE** | `category_code` | Mỗi mã danh mục chỉ xuất hiện một lần.                              |
| **CHECK**  | `category_code` | Chỉ chứa chữ thường, số và dấu gạch ngang (dùng cho `package_key`). |

### 2.5.2 Regions (Khu vực)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các khu vực được sử dụng để tổ chức và phân nhóm các POI trong hệ thống.

Khu vực có thể đại diện cho một khu du lịch, khuôn viên, bảo tàng, vùng địa lý hoặc phạm vi quản lý cụ thể.

**_[2] Trường dữ liệu (Fields)_**

| Field       | Type       | Nullable | Meaning                            |
| ----------- | ---------- | -------- | ---------------------------------- |
| id          | varchar PK | No       | Mã định danh duy nhất của khu vực, định dạng: `region-xxxxxxxx`. |
| region_name | varchar    | No       | Tên khu vực.                       |
| region_code | varchar    | No       | Mã khu vực, ví dụ: ..., ..., ...   |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                         |
| ---------- | ------------- | ------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất khu vực.                             |
| **UNIQUE** | `region_name` | Mỗi tên khu vực chỉ xuất hiện một lần.                              |
| **UNIQUE** | `region_code` | Mỗi mã khu vực chỉ xuất hiện một lần.                               |
| **CHECK**  | `region_code` | Chỉ chứa chữ thường, số và dấu gạch ngang (dùng cho `package_key`). |

### 2.5.3 Languages (Ngôn ngữ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các ngôn ngữ mà hệ thống hỗ trợ.

Thông tin ngôn ngữ được sử dụng để quản lý các phiên bản nội dung thuyết minh và các gói dữ liệu offline theo từng ngôn ngữ.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type       | Nullable | Meaning                                                                                             |
| --------------- | ---------- | -------- | --------------------------------------------------------------------------------------------------- |
| id              | varchar PK | No       | Mã định danh duy nhất của ngôn ngữ trong hệ thống, định dạng: `lang-xxxxxxxx`.                       |
| language_code   | varchar    | No       | Mã ngôn ngữ, ví dụ: `vi`, `en`, `ja`, `ko`.                                                         |
| language_name   | varchar    | No       | Tên hiển thị của ngôn ngữ, ví dụ: `Tiếng Việt`, `English`.                                          |
| language_status | enum       | No       | Xác định ngôn ngữ hiện có đang được hỗ trợ trong hệ thống hay không, gồm: `SUPPORTED`/`UNSUPPORTED` |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to     | Description                                              |
| ---------- | ----------------- | -------------------------------------------------------- |
| **PK**     | `id`              | Khóa chính, định danh duy nhất ngôn ngữ.                 |
| **UNIQUE** | `language_code`   | Mỗi mã ngôn ngữ chỉ xuất hiện một lần.                   |
| **UNIQUE** | `language_name`   | Mỗi tên ngôn ngữ chỉ xuất hiện một lần.                  |
| **CHECK**  | `language_code`   | Theo chuẩn ISO 639-1 (2 ký tự) hoặc ISO 639-2 (3 ký tự). |
| **CHECK**  | `language_status` | Thuộc tập giá trị `('SUPPORTED', 'UNSUPPORTED')`.        |
| **INDEX**  | `language_status` | Tăng tốc lọc ngôn ngữ theo trạng thái hỗ trợ.            |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `language_status`

Các trạng thái hiện tại gồm:

- `SUPPORTED`: ngôn ngữ đang được phép sử dụng để tạo/phân phối nội dung mới.
- `UNSUPPORTED`: ngôn ngữ tạm thời không được phân phối cho người dùng mới; dữ liệu cũ có thể vẫn được giữ để bảo toàn lịch sử.

[4.2] Quy tắc chuyển trạng thái

Khi chuyển `SUPPORTED` sang `UNSUPPORTED`:

- Không xóa dữ liệu cũ (`Poi_Contents`, `Offline_Packages`).
- Không cho phép tạo `Poi_Contents` mới với `language_id` này.
- Không build `Offline_Packages` mới với `language_id` này.

Khi chuyển `UNSUPPORTED` sang `SUPPORTED`:

- Cho phép tạo nội dung mới trở lại.

## 2.6 GROUP 6: AUDIT AND TRACEABILITY

Nhóm chịu trách nhiệm ghi nhận các hành động thay đổi dữ liệu do người dùng quản trị thực hiện.

Nhật ký giúp truy vết ai đã thay đổi dữ liệu nào, thời điểm nào và dữ liệu trước/sau thay đổi ra sao.

Các bảng thuộc nhóm:

- `Audit_Log`

### 2.6.1 Audit_Log (Nhật ký hệ thống)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ lịch sử các thao tác quan trọng được thực hiện bởi người dùng quản trị lên các entity của hệ thống.

Bảng phục vụ audit, điều tra sự cố, đối soát thay đổi và hỗ trợ khôi phục/nghiên cứu nguyên nhân khi dữ liệu bị chỉnh sửa không mong muốn.

**_[2] Trường dữ liệu (Fields)_**

| Field       | Type       | Nullable | Meaning                                                                                             |
| ----------- | ---------- | -------- | --------------------------------------------------------------------------------------------------- |
| id          | UUID PK    | No       | Mã định danh duy nhất của bản ghi nhật ký.                                                          |
| user_id     | varchar FK | No       | Người dùng thực hiện hành động, liên kết đến bảng **Manager_Users**.                                |
| action      | varchar    | No       | Hành động được thực hiện, ví dụ: `CREATE`, `UPDATE`, `DELETE`, `PUBLISH`, `APPROVE`.                |
| entity_type | varchar    | No       | Loại đối tượng hoặc bảng dữ liệu bị tác động, ví dụ: `POI`, `POI_CONTENT`, `CONTENT_AUDIO`, `ROLE`. |
| entity_id   | varchar    | No       | Mã định danh của bản ghi dữ liệu bị tác động.                                                       |
| old_values  | json/jsonb | Yes      | Snapshot các giá trị liên quan trước khi thay đổi                                                   |
| new_values  | json/jsonb | Yes      | Dữ liệu của đối tượng sau khi thay đổi.                                                             |
| created_at  | timestamp  | No       | Thời điểm hành động được ghi nhận.                                                                  |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to                | Description                                                                      |
| --------- | ---------------------------- | -------------------------------------------------------------------------------- |
| **PK**    | `id`                         | Khóa chính, định danh duy nhất bản ghi nhật ký.                                  |
| **FK**    | `user_id`                    | Tham chiếu đến `Manager_Users(id)`.                                              |
| **CHECK** | `action`                     | Thuộc tập giá trị cho phép (`CREATE`, `UPDATE`, `DELETE`, `PUBLISH`, `APPROVE`). |
| **CHECK** | `entity_type`                | Thuộc tập giá trị cho phép (`POI`, `POI_CONTENT`, `CONTENT_AUDIO`, `ROLE`, ...). |
| **INDEX** | (`entity_type`, `entity_id`) | Tăng tốc truy vấn lịch sử của 1 entity.                                          |
| **INDEX** | (`user_id`, `created_at`)    | Tăng tốc truy vấn theo người dùng + thời gian.                                   |
| **INDEX** | `created_at`                 | Tăng tốc truy vấn nhật ký theo thời gian.                                        |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `old_values` và `new_values`

- Với hành động `CREATE`, `old_values` có thể là NULL.
- Với hành động `DELETE`, `new_values` có thể là NULL.

[4.2] Quy tắc bảo mật

- Không ghi `password`, `refresh_token`, hoặc bất kỳ dữ liệu bí mật nào vào `old_values` / `new_values`.
- Nếu entity có field nhạy cảm cần phải mask hoặc loại bỏ trước khi ghi log.

[4.3] Quy tắc bất biến (immutability)

- Bản ghi audit không được UPDATE sau khi tạo.
- Bản ghi audit không được DELETE (trừ khi có quy trình archive riêng).

# 3. DỮ LIỆU LƯU TRÊN THIẾT BỊ NGƯỜI DÙNG

Ứng dụng mobile cần lưu một phần dữ liệu cục bộ để hỗ trợ:

- sử dụng ứng dụng mà không yêu cầu tài khoản;
- tải và sử dụng các Offline Package;
- phát thuyết minh khi không có kết nối Internet;
- tránh tải trùng audio/hình ảnh giữa nhiều package;
- khôi phục quá trình tải khi bị gián đoạn;
- quản lý cooldown của POI;
- ghi nhận lịch sử nghe khi offline và đồng bộ lên server khi có mạng.

Dữ liệu cục bộ có thể được lưu bằng SQLite kết hợp với file storage riêng của ứng dụng.

SQLite lưu metadata, trạng thái và quan hệ giữa các dữ liệu.

Audio, hình ảnh và các file lớn được lưu tại vùng file storage riêng của ứng dụng.

## 3.1 Installation ID

Khách du lịch không bắt buộc đăng nhập.

Do đó, ứng dụng sử dụng installation_id để nhận diện một lần cài đặt ứng dụng mà không sử dụng thông tin định danh phần cứng của thiết bị.

Quy tắc tạo installation_id

```
Khi ứng dụng cần thực hiện thao tác cần nhận diện anonymous client, chẳng hạn tải Offline Package hoặc ghi nhận lịch sử nghe, ứng dụng kiểm tra installation_id trong local storage.

Nếu chưa tồn tại:
    - Sinh một UUID ngẫu nhiên, khuyến nghị UUID v4.
    - Lưu UUID vào vùng private storage của ứng dụng.
    - Sử dụng giá trị này cho các request và listening event về sau.
```

installation_id được giữ ổn định trong suốt vòng đời của lần cài đặt hiện tại; và thay đổi khi người dùng xóa ứng dụng và cài đặt lại.

## 3.2 Local Database

### 3.2.1 Local_App_State

Lưu thông tin cục bộ chung của ứng dụng.

| Field                | Meaning                                  |
| :------------------- | :--------------------------------------- |
| installation_id      | UUID của lần cài đặt hiện tại            |
| selected_language_id | Ngôn ngữ hiện tại của ứng dụng/narration |
| local_schema_version | Phiên bản cấu trúc SQLite                |
| created_at           | Thời điểm dữ liệu local được tạo         |
| last_updated_at      | Thời điểm cập nhật gần nhất              |

Ứng dụng chỉ có một bản ghi AppState cho lần cài đặt hiện tại.

### 3.2.2 Local_Offline_Packages

Lưu các package đã hoặc đang được tải trên thiết bị.

| Field             | Meaning                                    |
| :---------------- | :----------------------------------------- |
| package_id        | ID package trên server                     |
| package_key       | Khóa logic của package                     |
| package_version   | Version đã commit thành công trên thiết bị |
| schema_version    | Schema của manifest                        |
| manifest_checksum | Checksum manifest hiện đang sử dụng        |
| status            | DOWNLOADING, READY, PAUSED, FAILED         |
| downloaded_at     | Thời điểm tải thành công                   |
| last_checked_at   | Lần cuối kiểm tra version với server       |

Chỉ package có status = READY mới được dùng cho chế độ offline.

package_version local chỉ được cập nhật sau khi toàn bộ dữ liệu bắt buộc của version mới đã được tải và verify thành công.

### 3.2.3 Local_POIs

Lưu snapshot metadata POI cần thiết để mobile có thể xác định vùng kích hoạt khi offline.

| Field                | Meaning                                      |
| :------------------- | :------------------------------------------- |
| poi_id               | ID POI                                       |
| region_id            | Khu vực                                      |
| poi_name             | Tên POI                                      |
| poi_location         | Mô tả địa điểm                               |
| latitude             | Vĩ độ                                        |
| longitude            | Kinh độ                                      |
| trigger_radius_meter | Bán kính kích hoạt                           |
| trigger_priority     | Độ ưu tiên khi các vùng chồng nhau           |
| image_checksum       | Asset hình ảnh hiện được snapshot tham chiếu |

Một POI có thể được nhiều package sử dụng.

### 3.2.4 Local_Poi_Contents

Lưu nội dung thuyết minh đã được package tải xuống.

| Field            | Meaning                                 |
| :--------------- | :-------------------------------------- |
| poi_content_id   | ID nội dung                             |
| poi_id           | POI tương ứng                           |
| language_id      | Ngôn ngữ                                |
| content_version  | Phiên bản nội dung                      |
| narration_title  | Tiêu đề                                 |
| narration_script | Nội dung văn bản                        |
| audio_checksum   | Checksum audio content hiện tại sử dụng |

### 3.2.5 Local_Assets

Lưu thông tin các physical asset đã có trên thiết bị.

Checksum được sử dụng làm identity của physical asset.

| Field           | Meaning                  |
| :-------------- | :----------------------- |
| checksum_sha256 | PK logic của asset       |
| asset_type      | AUDIO hoặc IMAGE         |
| local_path      | Đường dẫn tới file local |
| file_size       | Kích thước file          |
| mime_type       | MIME type                |
| verify_status   | VERIFIED hoặc CORRUPTED  |
| verified_at     | Lần verify gần nhất      |

Hai package sử dụng cùng checksum sẽ dùng chung một physical file.

Không tải lại asset nếu local đã tồn tại file VERIFIED có cùng checksum.

### 3.2.6 Local_Package_Items

Lưu quan hệ giữa package local và các dữ liệu/asset mà package sử dụng.

| Field          | Meaning               |
| :------------- | :-------------------- |
| package_id     | Package local         |
| poi_id         | POI thuộc package     |
| poi_content_id | Content thuộc package |
| audio_checksum | Audio package sử dụng |
| image_checksum | Image package sử dụng |

Bảng này được sử dụng để xác định asset nào còn đang được package nào tham chiếu.

Khi xóa package, ứng dụng xóa membership trước.

Physical asset chỉ được xóa nếu không còn Local_Package_Items nào tham chiếu checksum tương ứng.

Không nên chỉ dựa vào một trường ref_count riêng vì ref_count có thể sai nếu ứng dụng bị crash giữa transaction; quan hệ thực tế trong Local_Package_Items phải là nguồn xác định cuối cùng.

### 3.2.7 Local_Download_Jobs

Lưu trạng thái tải để có thể resume sau khi mất mạng hoặc ứng dụng bị đóng.

| Field                  | Meaning                                |
| :--------------------- | :------------------------------------- |
| job_id                 | UUID của download job                  |
| package_id             | Package đang tải                       |
| target_package_version | Version đang cài                       |
| status                 | DOWNLOADING, PAUSED, FAILED, COMPLETED |
| bytes_downloaded       | Số bytes đã tải                        |
| retry_count            | Số lần retry                           |
| last_error             | Lỗi gần nhất                           |
| updated_at             | Thời điểm cập nhật                     |

File đang tải dở được lưu dưới dạng temporary file, ví dụ `.part`.

Temporary file không được xem là asset hợp lệ cho tới khi checksum đã được xác minh.

### 3.2.8 Local_POI_Trigger_State

Lưu trạng thái cần thiết để chống phát narration lặp lại khi ứng dụng restart.

| Field                  | Meaning                                 |
| :--------------------- | :-------------------------------------- |
| poi_id                 | POI                                     |
| last_auto_triggered_at | Lần gần nhất POI thực sự được auto-play |
| updated_at             | Thời điểm cập nhật                      |

Cooldown 5 phút được kiểm tra từ `last_auto_triggered_at`.

Debounce 3 giây và trạng thái inside/outside hiện tại chỉ chủ yếu được giữ trong runtime memory.

### 3.2.9 Local_Listening_Events

Lưu các listening event chưa hoặc đã đồng bộ.

| Field                | Meaning                              |
| :------------------- | :----------------------------------- |
| id                   | Mã `listen-ddmmyy-xxxxxxxx` được tạo ngay trên mobile |
| installation_id      | Installation hiện tại                |
| poi_id               | POI được phát                        |
| poi_content_id       | Content được phát                    |
| trigger_type         | AUTO_LOCATION hoặc QR_CODE           |
| started_at           | Thời điểm audio thực sự bắt đầu phát |
| completed_at         | Thời điểm kết thúc                   |
| duration_sec         | Thời gian phát thực tế               |
| sync_status          | PENDING, SYNCING, SYNCED, FAILED     |
| retry_count          | Số lần retry                         |
| last_sync_attempt_at | Lần sync cuối                        |

`id` được sinh trên mobile và giữ nguyên khi gửi lên server.

Nhờ vậy request sync có thể retry nhiều lần mà server vẫn xử lý idempotent theo cùng một mã lượt nghe.

## 3.3 Quy tắc toàn vẹn dữ liệu local

Một Offline Package chỉ được chuyển sang READY khi:

- Manifest hợp lệ.
- Manifest checksum hợp lệ.
- schema_version được phiên bản mobile hiện tại hỗ trợ.
- Tất cả metadata bắt buộc đã được parse thành công.
- Tất cả asset bắt buộc tồn tại.
- Kích thước các asset phù hợp.
- SHA-256 của các asset phù hợp với manifest.
- Transaction cập nhật local database hoàn tất thành công.

Nếu bất kỳ bước nào thất bại, version package đang READY trước đó không được thay đổi.

# 4. CÁC LUỒNG DỮ LIỆU CHÍNH

## 4.1 Luồng tải gói offline

### 4.1.1 Khởi tạo

Khi người dùng yêu cầu tải một package:

- Mobile kiểm tra `installation_id`.
- Nếu chưa có thì sinh UUID và lưu local.
- Mobile gửi filter package gồm:
  - region;
  - language;
  - category nếu có.
- Server xây dựng `package_key` canonical.
- Server tìm `Offline_Package` tương ứng.
- Nếu package chưa từng tồn tại:
  - server tạo package logic;
  - bắt đầu initial build;
  - mobile nhận trạng thái `BUILDING`;
  - mobile không coi package là đã tải;
  - client có thể retry kiểm tra trạng thái theo backoff.
- Nếu package đã có version `PUBLISHED`, server trả version đang hoạt động ngay cả khi một version mới hơn đang được rebuild.
- Nếu initial build thất bại và chưa từng tồn tại package hợp lệ, server trả trạng thái lỗi phù hợp.

### 4.1.2 Kiểm tra version

Server trả về tối thiểu:

- `package_id`
- `package_key`
- `package_version`
- `schema_version`
- `package_url`
- `package_checksum_sha256`
- `total_size`
- `package_status`

Mobile so sánh với `Local_Offline_Packages`.

**Trường hợp chưa có package local**

- Tiến hành tải version server hiện tại.
- Local `package_version` = server `package_version`
- Nếu checksum manifest giống nhau và local package `READY`, không cần tải lại.
- Mobile có thể thực hiện integrity check nếu phát hiện file local bị thiếu.

**Local `package_version` < server `package_version`**

- Tiến hành incremental update.

**Local `package_version` > server `package_version`**

- Không downgrade ngay.
- Trường hợp này có thể do response/CDN cache bị stale hoặc server rollback.
- Mobile giữ package local hiện tại và yêu cầu lại metadata từ origin/server trước khi quyết định.

### 4.1.3 Kiểm tra schema

Trước khi tải asset, mobile kiểm tra `schema_version`.

Nếu mobile không hỗ trợ schema mới:

- không ghi đè package local đang `READY`;
- không parse manifest bằng cấu trúc không hiểu;
- thông báo cần cập nhật ứng dụng nếu cần;
- package cũ vẫn tiếp tục hoạt động nếu còn tương thích.

### 4.1.4 Tải manifest

Manifest được tải về temporary storage.

Sau khi tải xong:

- Kiểm tra HTTP response.
- Kiểm tra kích thước hợp lý.
- Tính SHA-256.
- So sánh với `package_checksum_sha256`.
- Parse JSON.
- Validate `package_key`.
- Validate `package_version`.
- Validate `schema_version`.
- Validate các field bắt buộc.
- Kiểm tra duplicate/invalid item.

Manifest không hợp lệ không được ghi đè manifest local hiện tại.

### 4.1.5 Xác định delta cần tải

Mobile duyệt từng asset trong manifest.

Với mỗi audio/image:

**Asset đã tồn tại và `VERIFIED` với cùng checksum**

- Không tải lại.

**Asset không tồn tại**

- Đưa vào download queue.

**File tồn tại nhưng checksum khác**

- File được xem là corrupted/stale và không được sử dụng.
- Tải lại asset đúng checksum.

**Asset đang được một download job khác tải**

- Không tạo download trùng.
- Job hiện tại chờ job đang tải asset đó hoàn tất rồi tái sử dụng kết quả.

### 4.1.6 Kiểm tra dung lượng

Trước khi bắt đầu download, mobile tính tổng dung lượng bổ sung thực sự cần tải, không dùng trực tiếp `total_size` của package vì thiết bị có thể đã có một số asset dùng chung.

Nếu không đủ dung lượng:

- không xóa package hiện tại;
- không bắt đầu commit version mới;
- thông báo cho người dùng;
- cho phép người dùng xóa package khác hoặc giải phóng bộ nhớ.

### 4.1.7 Tải asset

Asset được tải vào temporary file.

Ví dụ:

`<checksum>.mp3.part`

Sau khi download hoàn tất:

- Kiểm tra kích thước file.
- Tính SHA-256.
- So sánh checksum với manifest.
- Nếu hợp lệ, chuyển file sang vị trí asset chính thức.
- Tạo/cập nhật `Local_Assets` với `VERIFIED`.

Không dùng temporary file để playback.

### 4.1.8 Commit package

Chỉ khi toàn bộ asset bắt buộc đã `VERIFIED`, mobile mới commit version mới.

Quá trình commit local database phải chạy trong transaction.

Transaction:

- Upsert `Local_POIs`.
- Upsert `Local_Poi_Contents`.
- Tạo membership `Local_Package_Items` mới.
- Xóa membership không còn tồn tại trong manifest mới.
- Cập nhật `Local_Offline_Packages`:
  - `package_version`;
  - `manifest_checksum`;
  - `schema_version`;
  - `status = READY`;
  - `downloaded_at`.

Nếu transaction thất bại:

- rollback;
- package version cũ vẫn là version đang hoạt động;
- asset mới tải có thể trở thành orphan và được cleanup sau.

Do asset được lưu theo checksum, orphan asset không làm hỏng package cũ.

### 4.1.9 Garbage Collection

Sau khi commit thành công, mobile kiểm tra asset của version/package cũ.

Một physical asset chỉ được xóa khi:

```sql
NOT EXISTS (
    Local_Package_Items tham chiếu checksum đó
)
```

### 4.1.10 Xử lý các trường hợp lỗi

| Trường hợp                               | Cách xử lý                                                                                                                            |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| Không có Internet trước khi tải          | Nếu có package READY, tiếp tục dùng package cũ. Nếu chưa có thì không thể tải.                                                        |
| Mất mạng giữa download                   | Giữ .part và Download Job; resume khi có mạng nếu server hỗ trợ.                                                                      |
| App bị kill                              | Download Job vẫn còn trong SQLite; lần chạy sau tiếp tục hoặc restart asset đang dở.                                                  |
| Người dùng hủy                           | Chuyển job sang PAUSED/cancelled; không ảnh hưởng package READY.                                                                      |
| Timeout                                  | Retry với backoff; không commit dữ liệu chưa đủ.                                                                                      |
| HTTP 5xx                                 | Retry có giới hạn; giữ package cũ.                                                                                                    |
| URL signed hết hạn/HTTP 401-403          | Lấy lại package metadata/URL mới trước khi retry.                                                                                     |
| Asset 404/410                            | Không commit package; refresh manifest/package metadata vì manifest có thể stale.                                                     |
| Checksum asset sai                       | Xóa temporary file và tải lại; sau số lần retry cho phép thì đánh dấu job FAILED.                                                     |
| Manifest checksum sai                    | Không parse/commit; tải lại manifest.                                                                                                 |
| Manifest JSON lỗi                        | Reject toàn bộ version đó.                                                                                                            |
| Schema mới không hỗ trợ                  | Giữ package cũ và yêu cầu cập nhật app.                                                                                               |
| Không đủ storage                         | Dừng trước download/commit; package cũ không bị ảnh hưởng.                                                                            |
| File local bị người dùng/OS làm mất      | Local integrity check phát hiện file thiếu và tải lại nếu online; package tạm thời không được coi là hoàn chỉnh cho POI bị ảnh hưởng. |
| Hai package tải cùng một asset           | Dùng lock theo checksum; chỉ một job thực sự tải.                                                                                     |
| Server publish v3 khi mobile đang tải v2 | Mobile được phép hoàn thành v2 vì manifest v2 là immutable; sau đó lần kiểm tra tiếp theo mới cập nhật v3.                            |
| Rebuild server thất bại                  | Version PUBLISHED cũ tiếp tục được phân phối.                                                                                         |
| POI bị loại khỏi package mới             | Xóa membership khi commit; chỉ xóa physical asset nếu không package nào khác tham chiếu.                                              |
| Database local lỗi khi commit            | Rollback transaction và giữ package cũ.                                                                                               |
| Asset mới đã tải nhưng DB commit fail    | Asset trở thành orphan; cleanup sau, không làm hỏng package cũ.                                                                       |

## 4.2 Luồng thuyết minh tự động khi đi vào vùng ảnh hưởng của POI

Hệ thống áp dụng ba cơ chế chính:

- **Safety reconcile interval** = 5 giây
- **Debounce** = 3 giây
- **Cooldown** = 5 phút

Ba cơ chế phục vụ mục đích khác nhau:

- **Safety reconcile 5 giây**: phát hiện lại trạng thái trong trường hợp location event bị bỏ lỡ.
- **Debounce 3 giây**: chống GPS dao động tại biên vùng.
- **Cooldown 5 phút**: chống phát lặp lại cùng POI trong thời gian ngắn.

Safety reconcile không được bỏ qua debounce hoặc cooldown.

### 4.2.1 Điều kiện tiên quyết

Auto narration chỉ hoạt động khi:

- ứng dụng có quyền truy cập vị trí phù hợp;
- location service của thiết bị đang bật;
- có location sample đủ tin cậy;
- POI metadata đã có trên thiết bị hoặc có thể lấy từ server;
- POI đang được xem là ACTIVE theo snapshot hiện có;
- tồn tại content cho ngôn ngữ hiện tại;
- audio có thể phát từ local hoặc từ server.

Nếu người dùng không cấp quyền vị trí thì chức năng auto narration bị vô hiệu hóa nhưng QR/manual narration vẫn có thể hoạt động.

### 4.2.2 State của mỗi POI

Runtime có thể quản lý mỗi POI theo các trạng thái:

- OUTSIDE
- ENTER_DEBOUNCE
- INSIDE_HANDLED
- EXIT_DEBOUNCE

**OUTSIDE**

Thiết bị được xem là ngoài vùng POI.

**ENTER_DEBOUNCE**

Thiết bị vừa được phát hiện nằm trong:

`distance <= trigger_radius_meter`

Ứng dụng bắt đầu timer debounce.

**INSIDE_HANDLED**

Lần đi vào vùng hiện tại đã được xử lý.

Có thể là:

- narration đã được phát;
- bị suppression do cooldown;
- không đủ điều kiện tại thời điểm entry.

Ứng dụng không tự phát lại chỉ vì cooldown hết hạn trong khi người dùng vẫn đứng trong cùng vùng.

Muốn kích hoạt entry mới, người dùng phải ra khỏi vùng và đi vào lại.

**EXIT_DEBOUNCE**

Thiết bị vừa được phát hiện ra ngoài vùng.

Sau khi trạng thái outside ổn định đủ debounce, POI trở lại OUTSIDE.

### 4.2.3 Xử lý mỗi location update

Mỗi khi nhận location mới:

- Kiểm tra sample có đủ mới và đủ chính xác hay không.
- Xác định các POI có khả năng liên quan.
- Tính khoảng cách từ thiết bị tới từng POI.
- Cập nhật state machine của POI.
- Xác định candidate đủ điều kiện.
- Chọn tối đa một POI để auto-play.

Location sample quá cũ hoặc có độ chính xác quá thấp không được dùng để auto-trigger.

Trong trường hợp không có sample đáng tin cậy, hệ thống giữ trạng thái an toàn và chờ sample mới thay vì tự phát audio dựa trên vị trí stale.

### 4.2.4 Debounce 3 giây khi vào vùng

Khi:

```
distance <= trigger_radius_meter
```

và state hiện tại là OUTSIDE:

```
state = ENTER_DEBOUNCE
inside_since = current_time
```

POI chỉ đủ điều kiện trigger khi thiết bị liên tục nằm trong vùng ít nhất 3 giây.

```
current_time - inside_since >= 3 seconds
```

Nếu trong 3 giây thiết bị lại ra ngoài vùng:

```
state = OUTSIDE
inside_since = null
```

và không phát audio.

Điều này hạn chế trường hợp GPS nhảy qua lại quanh đường biên.

Tương tự, có thể áp dụng debounce 3 giây cho việc xác nhận exit để tránh một GPS sample sai làm reset entry state ngay lập tức.

### 4.2.5 Safety Reconcile mỗi 5 giây

Cứ mỗi 5 giây, khi ứng dụng đang ở trạng thái được phép theo dõi vị trí:

- Lấy location hợp lệ gần nhất.
- Tính lại khoảng cách đến các POI liên quan.
- So sánh với state hiện tại.
- Sửa lại state nếu location event trước đó bị bỏ lỡ.
- Cho các POI đủ thời gian debounce tiếp tục đi qua state machine bình thường.

Ví dụ:

```
T0: người dùng đi vào POI nhưng callback location transition bị bỏ lỡ.

T0 + 5s: safety reconcile thấy distance <= radius.
    -> chuyển OUTSIDE -> ENTER_DEBOUNCE

Sau khi đủ 3s inside ổn định:
    -> xét cooldown
    -> trigger nếu đủ điều kiện.
```

Safety reconcile tuyệt đối không gọi player trực tiếp.

Nó chỉ đưa dữ liệu qua cùng state machine, debounce và cooldown như location update thông thường.

### 4.2.6 Cooldown 5 phút

Cooldown được áp dụng riêng cho từng POI đối với AUTO_LOCATION.

Khi audio thực sự bắt đầu phát thành công:

```
last_auto_triggered_at = current_time
```

POI bị cooldown nếu:

```
current_time - last_auto_triggered_at < 5 minutes
```

Nếu người dùng đi vào POI trong thời gian cooldown:

- không auto-play;
- entry hiện tại được đánh dấu INSIDE_HANDLED;
- không tự phát audio khi cooldown hết nếu người dùng vẫn đứng trong POI.

Người dùng phải exit rồi re-enter sau cooldown để tạo entry mới.

Cooldown chỉ được set khi playback thực sự bắt đầu.

Nếu việc load audio thất bại trước khi player bắt đầu thì không set cooldown.

Nếu người dùng tự dừng audio sau khi đã bắt đầu, cooldown vẫn được giữ để tránh phát lại ngay lập tức.

QR_CODE là hành động chủ động của người dùng và có thể không bị ràng buộc bởi cooldown AUTO_LOCATION.

### 4.2.7 Khi nhiều POI cùng đủ điều kiện

Không được phát nhiều narration đồng thời.

Các POI candidate được xếp theo:

1. trigger_priority cao hơn.
2. distance / trigger_radius_meter nhỏ hơn.
3. Khoảng cách tuyệt đối nhỏ hơn.
4. poi_id để tie-break deterministic.

Chỉ candidate tốt nhất được phép auto-play.

Các candidate còn lại vẫn tiếp tục được theo dõi.

### 4.2.8 Khi đang có narration khác phát

Auto narration mới không nên tự động cắt ngang narration đang phát.

Nếu một POI khác đủ điều kiện trong lúc player đang bận:

- Ghi nhận nó là pending candidate.
- Không bắt đầu player thứ hai.
- Khi audio hiện tại kết thúc, revalidate:
  - người dùng còn ở trong POI không;
  - entry còn hợp lệ không;
  - cooldown còn cho phép không;
  - content/audio còn khả dụng không.
- Chỉ khi tất cả điều kiện vẫn đúng mới phát tiếp.

Không phát candidate cũ dựa trên một vị trí đã stale.

### 4.2.9 Chọn audio để phát

Khi POI đủ điều kiện:

**Có verified local asset**

- Phát audio local ngay.

**Không có local asset nhưng có Internet**

- Ứng dụng có thể lấy content/audio PUBLISHED hiện tại từ server và phát online theo nghiệp vụ online của hệ thống.
- Có thể cache asset sau đó.

**Không có local asset và không có Internet**

- Không auto-play.
- Không set cooldown vì audio chưa bắt đầu.
- Có thể hiển thị thông báo nội dung chưa được tải offline.

Không được tự động phát content của một ngôn ngữ khác nếu hệ thống chưa có business rule fallback ngôn ngữ rõ ràng.

### 4.2.10 Ghi Listening History

Ngay khi player thực sự bắt đầu:

- Sinh mã `Listening_History.id` theo định dạng `listen-ddmmyy-xxxxxxxx` trên mobile.
- Lấy installation_id.
- Ghi:
  - poi_id;
  - poi_content_id;
  - trigger_type = AUTO_LOCATION;
  - started_at.
- Lưu event vào Local_Listening_Events.

Trong quá trình phát, player theo dõi thời gian phát thực tế.

Khi kết thúc hoặc người dùng dừng:

- cập nhật completed_at;
- cập nhật duration_sec.

Nếu offline:

```
sync_status = PENDING
```

Khi có Internet, mobile gửi event lên server.

Server xử lý idempotent theo id.

Nếu cùng một event được gửi lại do timeout/retry, server không tạo bản ghi thứ hai.

Chỉ sau khi server ACK thành công:

```
sync_status = SYNCED
```

### 4.2.11 Các trường hợp bất thường

| Trường hợp                                                           | Xử lý                                                                                                                        |
| :------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| GPS dao động ở đường biên                                            | Debounce 3 giây, không trigger ngay từ một sample.                                                                           |
| Callback location bị miss                                            | Safety reconcile 5 giây phát hiện lại.                                                                                       |
| App vừa mở và người dùng đã đứng trong POI                           | Safety reconcile coi đây là một candidate mới → debounce 3 giây → xét cooldown.                                              |
| App restart trong cooldown                                           | Đọc last_auto_triggered_at từ Local_POI_Trigger_State và tiếp tục cooldown.                                                  |
| Cooldown hết khi người dùng vẫn đứng nguyên trong POI                | Không phát lại; phải exit rồi re-enter.                                                                                      |
| Người dùng ra ngoài rồi vào lại trong < 5 phút                       | Entry mới được nhận diện nhưng bị cooldown, không phát.                                                                      |
| Người dùng ra ngoài rồi vào lại sau > 5 phút                         | Debounce lại 3 giây rồi có thể phát.                                                                                         |
| Hai POI overlap                                                      | Chỉ chọn một POI theo priority và khoảng cách.                                                                               |
| Đang phát POI A thì vào POI B                                        | Không interrupt tự động; B được revalidate sau khi A kết thúc.                                                               |
| Không có audio local nhưng online                                    | Có thể lấy bản PUBLISHED online.                                                                                             |
| Không có audio local và offline                                      | Không phát; không set cooldown.                                                                                              |
| Audio local tồn tại nhưng checksum sai                               | Không sử dụng file; đánh dấu corrupted và tải lại khi có mạng.                                                               |
| POI đã bị server INACTIVE nhưng thiết bị đang offline với package cũ | Thiết bị chỉ có thể sử dụng snapshot offline hiện tại; trạng thái mới được áp dụng sau lần đồng bộ/package update tiếp theo. |
| Server publish content mới lúc audio cũ đang phát                    | Audio đang phát tiếp tục đến hết; không thay bytes giữa playback. Lần trigger sau dùng snapshot mới sau khi update.          |
| Permission location bị revoke                                        | Dừng auto detection; QR/manual vẫn có thể hoạt động.                                                                         |
| Location Services bị tắt                                             | Không auto-trigger; chờ dịch vụ vị trí hoạt động lại.                                                                        |
| Location sample quá cũ                                               | Không trigger; yêu cầu/đợi sample mới.                                                                                       |
| Location accuracy quá kém                                            | Không trigger dựa trên sample không đáng tin cậy.                                                                            |
| Mất Internet                                                         | Local package READY vẫn hoạt động bình thường.                                                                               |
| Listening event sync thất bại                                        | Giữ PENDING/FAILED và retry sau.                                                                                             |
| Sync request timeout nhưng server thực ra đã lưu event               | Retry cùng id; server xử lý idempotent nên không duplicate.                                                                  |
| App bị kill giữa lúc nghe                                            | Lưu/checkpoint duration local định kỳ; lần mở sau đóng event bị gián đoạn theo dữ liệu cuối cùng có thể xác định.            |
| Người dùng quét QR trong cooldown                                    | QR là trigger chủ động, không nhất thiết chịu cooldown.                                                                      |
