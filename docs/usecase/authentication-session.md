# UC-IDENTITY-01 — Đăng nhập và đăng xuất hệ thống quản trị

| Use case number: | UC-IDENTITY-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Đăng nhập, sử dụng phiên và đăng xuất hệ thống quản trị |  |
| **Actor(s):** | Người dùng quản trị (Management User), Admin Web |  |
| **Maturity:** | Implemented — backend đã triển khai login, refresh-token rotation, xác thực Bearer token, kiểm tra RBAC và logout |  |
| **Summary:** | Người dùng quản trị cung cấp email và mật khẩu để tạo phiên. Backend cấp JWT Access Token và Refresh Token qua cookie HttpOnly, xác thực phiên và quyền khi người dùng thao tác, đồng thời thu hồi phiên khi đăng xuất. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Người dùng quản trị truy cập Admin Web. |  |
|  |  | 2\. Admin Web hiển thị biểu mẫu đăng nhập gồm email và mật khẩu. |
|  | 3\. Người dùng nhập email, mật khẩu và chọn **Đăng nhập**. |  |
|  |  | 4\. Admin Web gửi `POST /api/v1/auth/login`; FastAPI kiểm tra trường bắt buộc, định dạng email và quy tắc mật khẩu không chứa khoảng trắng. **E1** |
|  |  | 5\. MNR Backend chuẩn hóa email, tìm tài khoản và dùng Argon2id để xác minh mật khẩu. Khi email không tồn tại, backend vẫn thực hiện dummy hash để giảm chênh lệch thời gian phản hồi. **E2** |
|  |  | 6\. MNR Backend kiểm tra tài khoản đang ở trạng thái `ACTIVE`. **E2** |
|  |  | 7\. Trong một transaction, backend tạo Refresh Token, chỉ lưu SHA-256 hash vào `user_session`, đặt hạn tuyệt đối và cập nhật `last_login_at`. **E3** |
|  |  | 8\. Backend ký JWT Access Token RS256 có `sid` liên kết với session, trả token và dữ liệu công khai của người dùng; Refresh Token gốc chỉ được đặt trong cookie HttpOnly. **E4** |
|  |  | 9\. Admin Web chuyển người dùng đến màn hình quản trị phù hợp với vai trò. |
|  | 10\. Người dùng chọn một chức năng quản trị và gửi Bearer Access Token. |  |
|  |  | 11\. Backend xác minh JWT, session, trạng thái tài khoản, role hiện tại và permission theo cặp chức năng–hành động trước khi xử lý. **A1, A3, E5, E6** |
|  | 12\. Người dùng chọn **Đăng xuất**. |  |
|  |  | 13\. Admin Web gửi `POST /api/v1/auth/logout`; backend thu hồi session, trả `204 No Content` và xóa Refresh Token cookie. Admin Web xóa Access Token cục bộ rồi trở về màn hình đăng nhập. **E7** |
| **Alternative Paths:** | **A1 — Cấp lại Access Token:** Khi Access Token hết hạn hoặc sắp hết hạn, Admin Web gửi `POST /api/v1/auth/refresh` cùng Refresh Token cookie. Backend khóa session, kiểm tra hiệu lực, xoay Refresh Token và cấp Access Token mới. Hạn tuyệt đối `expires_at` của session không được kéo dài.<br><br>**A2 — Đóng trình duyệt:** Cookie có `Max-Age` và `Expires`, vì vậy đóng trình duyệt không tự thu hồi session. Session tồn tại đến khi hết hạn, đăng xuất, đổi mật khẩu, vô hiệu hóa tài khoản hoặc bị thu hồi bởi nghiệp vụ khác.<br><br>**A3 — Role thay đổi:** Nếu role hiện tại khác claim `role_id` trong JWT, backend từ chối token và yêu cầu cấp token mới. |  |
| **Exception Paths:** | **E1 — Dữ liệu không hợp lệ:** Body thiếu trường, email sai định dạng hoặc mật khẩu không hợp lệ làm FastAPI trả `422 Unprocessable Entity`; không tạo session.<br><br>**E2 — Xác thực thất bại:** Email không tồn tại, mật khẩu sai hoặc tài khoản `INACTIVE` đều nhận chung `401 Authentication required`, không làm lộ nguyên nhân cụ thể.<br><br>**E3 — Không tạo được phiên:** Transaction rollback và không cấp thông tin xác thực.<br><br>**E4 — Cấu hình JWT không hợp lệ:** Thiếu hoặc sai khóa ký làm endpoint trả `503 Service Unavailable` và không hoàn thành đăng nhập.<br><br>**E5 — Token hoặc phiên không hợp lệ:** JWT sai chữ ký/claim, session không tồn tại, hết hạn, đã thu hồi hoặc role thay đổi làm backend trả `401 Authentication required`.<br><br>**E6 — Không đủ quyền:** Backend trả `403 Insufficient permission` nhưng không thu hồi session.<br><br>**E7 — Lỗi database khi đăng xuất:** Request có thể thất bại trước khi response xóa cookie được gửi; Admin Web vẫn phải xóa Access Token cục bộ. |  |
| **Extension Points:** | Có thể bổ sung MFA, rate limiting/khóa tài khoản, đăng xuất tất cả thiết bị, refresh-token family và phát hiện replay, job dọn session, CSRF token cho topology cross-site và quy trình xoay khóa RSA hoàn chỉnh. |  |
| **Triggers:** | Người dùng quản trị cần đăng nhập, cấp lại Access Token, truy cập chức năng được bảo vệ hoặc kết thúc phiên hiện tại. |  |
| **Assumptions:** | Database và migration đã sẵn sàng; `DATABASE_URL`, định danh JWT và cặp khóa RSA được cấu hình hợp lệ; production sử dụng HTTPS; đồng hồ hệ thống nằm trong dung sai `JWT_LEEWAY_SECONDS`. |  |
| **Preconditions:** | Dữ liệu `manager_user`, `role` và permission tương ứng đã tồn tại; tài khoản đăng nhập có `user_status = ACTIVE`. |  |
| **Post Conditions:** | Login thành công tạo session, cập nhật `last_login_at`, trả Access Token và đặt Refresh Token cookie. Refresh thành công thay hash Refresh Token nhưng giữ nguyên hạn tuyệt đối. Logout thành công đặt `revoked_at` và yêu cầu trình duyệt xóa cookie. |  |
| **Preferences:** | Không trả hoặc ghi log mật khẩu, `password_hash`, Access Token, Refresh Token hay `refresh_token_hash`; không lưu plaintext Refresh Token; không đưa dữ liệu bí mật vào payload JWT; thông báo đăng nhập sai không làm lộ sự tồn tại của email. |  |
| **Author(s):** | MNR Backend Team |  |
| **Date:** | 31-10-2026 |  |

## Trạng thái trong phiên bản hiện tại

Use case trên đã được triển khai với các HTTP contract sau:

| Method | Endpoint | Chức năng |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Xác minh email/mật khẩu, tạo session, trả Access Token và đặt Refresh Token cookie |
| `POST` | `/api/v1/auth/refresh` | Xoay Refresh Token và cấp Access Token mới |
| `POST` | `/api/v1/auth/logout` | Thu hồi session hiện tại và xóa Refresh Token cookie |
| `GET` | `/api/v1/auth/me` | Trả dữ liệu công khai của người dùng hiện tại |

Các cơ chế đang được sử dụng:

- mật khẩu được băm và xác minh bằng Argon2id;
- Access Token là JWT RS256, mặc định sống 900 giây;
- JWT có `kid` và các claim bắt buộc gồm `iss`, `aud`, `sub`, `sid`, `role_id`,
  `type`, `jti`, `iat`, `nbf`, `exp`;
- Refresh Token là chuỗi opaque có entropy cao; database chỉ lưu SHA-256 hash;
- session mặc định sống 2.592.000 giây và không được gia hạn khi refresh;
- Bearer dependency kiểm tra JWT, session, tài khoản, role và permission hiện tại;
- cookie Refresh Token dùng `HttpOnly`, `Secure`, `SameSite`, `Max-Age`, `Expires`
  và bắt buộc có `Path=/api/v1/auth` để được gửi đến refresh và logout;
- thay đổi mật khẩu hoặc vô hiệu hóa tài khoản sẽ thu hồi các session đang hoạt động.

Các giá trị triển khai bắt buộc phải được cung cấp qua environment hoặc secret
manager gồm `DATABASE_URL`, `JWT_ACTIVE_KEY_ID`, `JWT_ISSUER` và `JWT_AUDIENCE`.
`JWT_PRIVATE_KEY` và `JWT_PUBLIC_KEYS` không có khóa mặc định; endpoint cần ký hoặc
xác minh token trả `503 Service Unavailable` nếu thiếu cấu hình khóa. Private key
thật không được commit vào Git hoặc đóng gói trong Docker image.

Refresh Token cookie phải dùng:

```env
AUTH_COOKIE_PATH=/api/v1/auth
```

Ngoài phạm vi phiên bản hiện tại:

- MFA và chính sách khóa tài khoản theo số lần đăng nhập sai;
- logout tất cả thiết bị bằng endpoint riêng;
- phát hiện replay theo refresh-token family;
- job dọn dẹp session hết hạn hoặc đã thu hồi;
- CSRF token riêng cho topology cross-site;
- quy trình vận hành hoàn chỉnh cho xoay khóa RSA;
- quy ước lưu Access Token và tự động refresh ở Admin Web.

API quản trị manager user, role và permission được mô tả riêng trong
`app/domains/identity/README.md`.
