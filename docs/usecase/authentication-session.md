# UC-AUTH-01 — Đăng nhập, duy trì phiên và đăng xuất

| Use case number: | UC-AUTH-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Đăng nhập, duy trì phiên và đăng xuất khỏi hệ thống quản trị |  |
| **Actor(s):** | Người dùng quản trị (Manager User), Ứng dụng quản trị web (Admin Web), MNR Backend |  |
| **Maturity:** | Focused |  |
| **Summary:** | Người dùng quản trị đăng nhập bằng email và mật khẩu, nhận Access Token và Refresh Token, sử dụng Access Token để truy cập các chức năng được phân quyền, làm mới Access Token khi cần và đăng xuất để thu hồi phiên. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Người dùng truy cập trang đăng nhập của hệ thống quản trị. |  |
|  |  | 2\. Admin Web hiển thị biểu mẫu gồm email và mật khẩu. |
|  | 3\. Người dùng nhập email, mật khẩu và chọn **Đăng nhập**. |  |
|  |  | 4\. Admin Web kiểm tra dữ liệu bắt buộc và gửi yêu cầu `POST /api/v1/auth/login` qua HTTPS. **E1** |
|  |  | 5\. MNR Backend chuẩn hóa email, tìm `manager_user` theo email và dùng password provider để đối chiếu mật khẩu với `password_hash`. **E2** |
|  |  | 6\. MNR Backend kiểm tra tài khoản tồn tại và có `user_status = ACTIVE`. **E3** |
|  |  | 7\. Trong một transaction, MNR Backend sinh Refresh Token ngẫu nhiên, chỉ lưu SHA-256 của token vào `user_session`, đặt thời hạn phiên và cập nhật `last_login_at`. **E4** |
|  |  | 8\. MNR Backend ký JWT Access Token chứa `sub` là user ID, `sid` là session ID cùng các claim bắt buộc; trả Access Token và đặt Refresh Token trong cookie `HttpOnly`, `Secure`, `SameSite`. |
|  |  | 9\. Admin Web giữ Access Token trong memory, không lưu vào `localStorage`, sau đó hiển thị màn hình phù hợp với người dùng. |
|  | 10\. Người dùng chọn một chức năng trong hệ thống quản trị. |  |
|  |  | 11\. Admin Web gửi request kèm `Authorization: Bearer <access-token>`. MNR Backend kiểm tra chữ ký và claim JWT, session, trạng thái tài khoản và permission hiện tại. **E5, E6** |
|  |  | 12\. MNR Backend thực hiện nghiệp vụ và trả kết quả cho Admin Web. Khi Access Token hết hạn, hệ thống thực hiện luồng làm mới token. **A1** |
|  | 13\. Sau khi hoàn thành công việc, người dùng chọn **Đăng xuất**. |  |
|  |  | 14\. Admin Web gửi `POST /api/v1/auth/logout` kèm Refresh Token cookie. |
|  |  | 15\. MNR Backend hash Refresh Token, tìm đúng `user_session` và cập nhật `revoked_at` trong transaction. Thao tác đăng xuất có tính idempotent. **E7** |
|  |  | 16\. MNR Backend yêu cầu xóa Refresh Token cookie. Admin Web xóa Access Token trong memory và chuyển người dùng về trang đăng nhập. |
| **Alternative Paths:** | **A1 — Làm mới Access Token:** Tại bước 12, nếu Access Token hết hạn, Admin Web gửi `POST /api/v1/auth/refresh` bằng Refresh Token cookie. MNR Backend hash token, khóa và kiểm tra session, kiểm tra tài khoản vẫn `ACTIVE`, rotate Refresh Token, cập nhật hash trong transaction và cấp Access Token mới. Quy trình quay lại bước 10. **E7, E8**.<br><br>**A2 — Đăng xuất tất cả thiết bị:** Thay cho bước 13, người dùng chọn đăng xuất tất cả thiết bị. MNR Backend thu hồi mọi session đang hoạt động của user, xóa cookie hiện tại và yêu cầu đăng nhập lại trên tất cả thiết bị.<br><br>**A3 — Access Token còn hiệu lực:** Tại bước 12, nếu Access Token chưa hết hạn, Admin Web tiếp tục dùng token hiện tại cho các request tiếp theo. Quy trình quay lại bước 10. |  |
| **Exception Paths:** | **E1 — Dữ liệu đăng nhập không hợp lệ:** Tại bước 4, nếu thiếu email/mật khẩu hoặc email sai định dạng, Admin Web hiển thị lỗi validation. Quy trình quay lại bước 3.<br><br>**E2 — Sai thông tin xác thực:** Tại bước 5, nếu email không tồn tại hoặc mật khẩu sai, MNR Backend trả cùng một thông báo “Email hoặc mật khẩu không hợp lệ”, không tiết lộ tài khoản có tồn tại hay không. Quy trình quay lại bước 3.<br><br>**E3 — Tài khoản không hoạt động:** Tại bước 6, nếu `user_status != ACTIVE`, MNR Backend từ chối đăng nhập. Người dùng liên hệ quản trị viên; quy trình kết thúc.<br><br>**E4 — Không thể tạo phiên hoặc ký token:** Tại bước 7 hoặc 8, nếu database hoặc token provider gặp lỗi, transaction tạo phiên bị rollback khi còn hiệu lực và hệ thống không trả credential cho client. Hệ thống hiển thị lỗi tạm thời; quy trình quay lại bước 3.<br><br>**E5 — Access Token hoặc session không hợp lệ:** Tại bước 11, nếu JWT sai chữ ký/claim, session hết hạn/bị thu hồi hoặc tài khoản không còn `ACTIVE`, MNR Backend trả `401 Unauthorized`. Admin Web thử A1 khi có thể; nếu refresh không hợp lệ thì xóa credential và chuyển về trang đăng nhập.<br><br>**E6 — Không đủ quyền:** Tại bước 11, nếu người dùng đã xác thực nhưng không có permission cần thiết, MNR Backend trả `403 Forbidden`. Người dùng vẫn đăng nhập và có thể chọn chức năng khác tại bước 10.<br><br>**E7 — Refresh Token không hợp lệ:** Tại bước 15 hoặc A1, nếu Refresh Token không tồn tại, hết hạn hoặc session đã bị thu hồi, MNR Backend không cấp token mới. Admin Web xóa credential và chuyển về trang đăng nhập.<br><br>**E8 — Refresh đồng thời:** Trong A1, nếu nhiều request cùng làm mới một session, chỉ request khóa và rotate token thành công đầu tiên được chấp nhận; các request dùng token cũ bị từ chối theo E7. |  |
| **Extension Points:** | Quên/reset mật khẩu; xác thực đa yếu tố (MFA); quản lý danh sách thiết bị/phiên; phát hiện Refresh Token replay theo token family; khóa tạm thời hoặc CAPTCHA sau nhiều lần đăng nhập thất bại. |  |
| **Triggers:** | Người dùng quản trị cần truy cập hệ thống; Access Token hết hạn trong lúc sử dụng; hoặc người dùng muốn kết thúc phiên đăng nhập. |  |
| **Assumptions:** | Kết nối sử dụng HTTPS; password provider và JWT provider đã được cấu hình; private key được quản lý bằng secret manager; thời gian giữa các thành phần hệ thống được đồng bộ; browser hỗ trợ cookie bảo mật. |  |
| **Preconditions:** | Tài khoản quản trị đã tồn tại, có role hợp lệ và đang ở trạng thái `ACTIVE`; MNR Backend kết nối được PostgreSQL; khóa ký JWT và chính sách thời hạn token đã được cấu hình. |  |
| **Post Conditions:** | Sau đăng nhập thành công, một `user_session` hợp lệ được lưu và client nhận credential tương ứng. Sau đăng xuất, session hiện tại có `revoked_at`, Refresh Token cookie và Access Token phía client bị xóa; credential của phiên không thể tiếp tục truy cập hệ thống. |  |
| **Preferences:** | Access Token có thời hạn mặc định 15 phút; Refresh Token có thời hạn mặc định 30 ngày; Refresh Token được rotate khi làm mới; password dùng Argon2id; JWT ký bằng `RS256`; lỗi xác thực không làm lộ thông tin nhạy cảm. |  |
| **Related data:** | `manager_user`, `user_session`, `role`, `role_permission`, `permission`, `management_function`, `action`, `audit_log`. |  |
| **Author(s):** | MNR Backend Team |  |
| **Date:** | 27-10-2026 |  |

## Trạng thái hiện thực

Use case trên là hợp đồng mục tiêu của luồng xác thực hoàn chỉnh.

Hiện tại `IdentityService` đã hỗ trợ kiểm tra tài khoản bằng Argon2id, tạo và kiểm
tra session, logout, kiểm tra permission và thu hồi session khi tài khoản bị vô
hiệu hóa hoặc đổi mật khẩu. Các HTTP endpoint, JWT provider, cookie handling và
refresh-token rotation vẫn cần được triển khai.

Thiết kế kỹ thuật chi tiết được trình bày tại
[authentication-design.md](../authentication-design.md).
