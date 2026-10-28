# UC-IDENTITY-01 — Đăng nhập và đăng xuất hệ thống quản trị

| Use case number: | UC-IDENTITY-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Đăng nhập, sử dụng phiên và đăng xuất hệ thống quản trị |  |
| **Actor(s):** | Người dùng quản trị (Management User), Admin Web |  |
| **Maturity:** | Implemented — luồng login, refresh, xác thực phiên và logout đã triển khai |  |
| **Summary:** | Người dùng quản trị cung cấp thông tin đăng nhập, hệ thống xác minh tài khoản, tạo phiên, kiểm tra quyền khi người dùng thao tác và kết thúc phiên khi đăng xuất. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Người dùng quản trị truy cập Admin Web. |  |
|  |  | 2\. Admin Web hiển thị biểu mẫu đăng nhập gồm email và mật khẩu. |
|  | 3\. Người dùng nhập email, mật khẩu và chọn **Đăng nhập**. |  |
|  |  | 4\. Admin Web kiểm tra dữ liệu bắt buộc và định dạng email. **E1** |
|  |  | 5\. MNR Backend chuẩn hóa email, tìm tài khoản quản trị và xác minh thông tin đăng nhập. **E2** |
|  |  | 6\. MNR Backend kiểm tra tài khoản đang ở trạng thái `ACTIVE`. **E3** |
|  |  | 7\. MNR Backend tạo một phiên gắn với tài khoản và thời điểm hết hạn. **E4** |
|  |  | 8\. Hệ thống trả thông tin xác thực của phiên cho Admin Web mà không trả `password_hash` hoặc `refresh_token_hash`. |
|  |  | 9\. Admin Web chuyển người dùng đến màn hình quản trị phù hợp với vai trò. |
|  | 10\. Người dùng chọn một chức năng quản trị và thực hiện thao tác. |  |
|  |  | 11\. Hệ thống kiểm tra trạng thái tài khoản, hiệu lực phiên và quyền ứng với cặp chức năng–hành động trước khi xử lý. **A1, E5, E6** |
|  | 12\. Người dùng chọn **Đăng xuất**. |  |
|  |  | 13\. MNR Backend kết thúc phiên hiện tại; Admin Web xóa thông tin xác thực cục bộ và quay về màn hình đăng nhập. **E7** |
| **Alternative Paths:** | **A1 — Tiếp tục phiên:** Tại bước 11, nếu phiên còn hiệu lực và người dùng có quyền, hệ thống xử lý thao tác rồi quay lại bước 10.<br><br>**A2 — Phiên hết hạn:** Tại bước 11, nếu phiên đã hết hạn, hệ thống không xử lý thao tác và yêu cầu người dùng đăng nhập lại từ bước 2. Phiên bản hiện tại không định nghĩa cơ chế tự động gia hạn phiên.<br><br>**A3 — Đóng trình duyệt:** Nếu người dùng đóng Admin Web mà không đăng xuất, phiên phía server chỉ kết thúc khi bị thu hồi hoặc hết hạn theo chính sách được triển khai sau này. |  |
| **Exception Paths:** | **E1 — Dữ liệu không hợp lệ:** Tại bước 4, nếu thiếu email/mật khẩu hoặc email sai định dạng, Admin Web hiển thị lỗi và quay lại bước 3.<br><br>**E2 — Thông tin đăng nhập không hợp lệ:** Tại bước 5, nếu không tìm thấy tài khoản hoặc mật khẩu không đúng, hệ thống trả cùng một thông báo chung và quay lại bước 3, không tiết lộ tài khoản có tồn tại hay không.<br><br>**E3 — Tài khoản không hoạt động:** Tại bước 6, nếu `user_status != ACTIVE`, hệ thống từ chối đăng nhập và kết thúc quy trình.<br><br>**E4 — Không tạo được phiên:** Tại bước 7, nếu không thể lưu phiên, hệ thống rollback thao tác và không cấp thông tin xác thực.<br><br>**E5 — Phiên không hợp lệ:** Tại bước 11, nếu phiên không tồn tại, hết hạn hoặc đã bị thu hồi, hệ thống từ chối thao tác và chuyển về bước 2.<br><br>**E6 — Không đủ quyền:** Tại bước 11, nếu người dùng không có quyền cần thiết, hệ thống từ chối thao tác nhưng không kết thúc phiên; quy trình quay lại bước 10.<br><br>**E7 — Không thể cập nhật phiên khi đăng xuất:** Tại bước 13, Admin Web vẫn phải xóa thông tin xác thực cục bộ; hệ thống ghi nhận lỗi để xử lý nhưng không tiếp tục coi người dùng là đã đăng nhập trên client. |  |
| **Extension Points:** | Có thể bổ sung xác thực đa yếu tố, chính sách khóa tài khoản, đăng xuất tất cả thiết bị và gia hạn phiên trong phiên bản sau. |  |
| **Triggers:** | Người dùng quản trị cần truy cập chức năng quản trị hoặc muốn kết thúc phiên đang sử dụng. |  |
| **Assumptions:** | Kênh giao tiếp được bảo vệ; cơ chế hash/xác minh mật khẩu và cơ chế cấp thông tin xác thực phải được lựa chọn trước khi triển khai use case. |  |
| **Preconditions:** | Dữ liệu `manager_user`, `role` và permission tương ứng đã tồn tại; tài khoản được phép đăng nhập phải ở trạng thái `ACTIVE`. |  |
| **Post Conditions:** | Sau đăng nhập thành công, hệ thống có một phiên hợp lệ gắn với người dùng. Sau đăng xuất thành công, phiên hiện tại bị thu hồi và client không còn giữ thông tin xác thực của phiên. |  |
| **Preferences:** | Không trả hoặc ghi log mật khẩu, `password_hash`, token hay token hash; thông báo đăng nhập sai không làm lộ sự tồn tại của email. |  |
| **Author(s):** | MNR Backend Team |  |
| **Date:** | 28-10-2026 |  |

## Trạng thái trong phiên bản hiện tại

Use case trên đã được triển khai cho quy trình xác thực và quản lý phiên hiện tại:

- model và repository cho `manager_user`, `user_session`, role và permission;
- băm mật khẩu bằng Argon2id khi tạo hoặc đổi tài khoản;
- xác minh email/mật khẩu và trạng thái `ACTIVE` ở tầng service;
- ký và xác minh JWT Access Token RS256 bằng cặp khóa được inject;
- `POST /api/v1/identity/login` tạo session, cập nhật lần đăng nhập cuối, trả
  Access Token và đặt Refresh Token trong cookie HttpOnly;
- `POST /api/v1/identity/refresh` khóa session, xoay Refresh Token và cấp Access
  Token mới;
- Bearer dependency xác minh JWT, `sid`, hiệu lực session, tài khoản và role;
- `GET /api/v1/identity/me` trả dữ liệu công khai của người dùng hiện tại;
- `POST /api/v1/identity/logout` thu hồi session và xóa cookie;
- composition root nạp cấu hình JWT từ môi trường triển khai;
- service quản trị người dùng, đọc vai trò và kiểm tra quyền RBAC;
- Refresh Token chỉ được lưu dưới dạng SHA-256 hash trong database.

Ngoài phạm vi use case hiện tại:

- MFA và chính sách khóa tài khoản theo số lần đăng nhập sai;
- phát hiện replay theo token family sau khi một Refresh Token cũ bị tái sử dụng.

API quản trị manager user, role và permission đã được triển khai như các use case
RBAC riêng và được mô tả trong `app/domains/identity/README.md`.
