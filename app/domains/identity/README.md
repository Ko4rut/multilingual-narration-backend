# Identity domain

Domain `identity` quản lý dữ liệu người dùng quản trị, vai trò, quyền và các bản
ghi phiên được mô tả trong database design. Luồng xác thực hiện tại lưu phiên,
dùng JWT RS256 cho Access Token và cookie HttpOnly cho Refresh Token.

## Cấu trúc

```text
identity/
├── models/          ORM cho user, session, role và permission
├── repositories/    Truy vấn SQLAlchemy bằng Session được inject
├── schemas/         DTO công khai, không trả password_hash/token hash
├── security/        Argon2id, JWT RS256 và Refresh Token
├── services/
│   ├── authentication.py Đăng nhập, Access Token và vòng đời session
│   ├── manager_user.py  Tạo và cập nhật tài khoản quản trị
│   └── role.py          Quản lý role và tập permission
├── routers/         Login/refresh/logout/me, dependency và quy ước cookie
├── exceptions/      Lỗi nghiệp vụ của user, session và role
└── utils/           Chuẩn hóa dữ liệu, thời gian UTC và sinh business ID
```

## Trách nhiệm hiện tại

`ManagerUserService` nhận mật khẩu plaintext khi tạo hoặc đổi tài khoản, băm bằng
Argon2id rồi chỉ gán hash vào model trước khi lưu. Plaintext không được chuyển
cho repository hoặc ghi xuống database. Mật khẩu không được chứa dấu cách, tab,
ký tự xuống dòng hoặc bất kỳ ký tự khoảng trắng Unicode nào.

Các thuật toán bảo mật nằm trong `security/` và được inject vào service. Thư mục
này không quản lý transaction, không truy vấn database và không phụ thuộc HTTP.
Các helper thuần dùng lặp lại như chuẩn hóa email và kiểm tra chuỗi bắt buộc nằm
trong `utils/`; quy tắc transaction và quy tắc bảo mật không được đưa vào đây.

`AuthenticationService.authenticate_credentials()` chuẩn hóa email, lấy tài khoản và
dùng Argon2id `verify` để đối chiếu mật khẩu nhập vào với hash đã lưu. Khi login,
service tạo `user_session`, cập nhật `last_login_at`, chỉ lưu SHA-256 của Refresh
Token và ký Access Token chứa user ID, session ID (`sid`), role ID cùng các claim
thời gian bắt buộc trong một transaction.

`JwtAccessTokenSigner` nhận private/public key qua constructor, ký bằng private
key và xác minh bằng public key tương ứng với `kid`. JWT chỉ được ký, không được
mã hóa, nên payload không chứa mật khẩu hoặc hash. Khóa thật phải được inject từ
secret manager hoặc cấu hình triển khai; source code không cung cấp khóa mặc định.

`POST /api/v1/identity/login` trả Access Token và đặt Refresh Token vào cookie
`Secure`, `HttpOnly`, `SameSite=strict`. `POST /refresh` khóa session bằng
`FOR UPDATE`, xoay Refresh Token rồi cấp Access Token mới. `POST /logout` thu hồi
session và xóa cookie theo cách idempotent. `GET /me` xác minh chữ ký JWT, session,
trạng thái tài khoản và role hiện tại trước khi trả dữ liệu user công khai.

`AuthenticationService` cũng kiểm tra quyền theo cặp chức năng/hành động;
`ManagerUserService` quản lý tài khoản; `RoleService` quản lý metadata role và thay
thế tập permission theo transaction nguyên tử.

Ba service được đặt trong ba module riêng nhưng vẫn chia sẻ repository và security
component qua constructor injection; service không gọi lẫn nhau qua HTTP.

Mỗi request dùng Bearer token đều đối chiếu `sid` với session trong database. Vì
vậy session đã logout, hết hạn hoặc bị thu hồi do đổi mật khẩu/vô hiệu hóa tài
khoản sẽ làm Access Token mất hiệu lực ngay cả khi chữ ký JWT còn hạn.

## Quy tắc tầng

- Router không truy vấn database trực tiếp.
- Service sở hữu transaction của write use case.
- Repository không commit transaction.
- Repository dùng `get_by_*` để lấy một bản ghi và `get_all*` để lấy danh sách;
  các tên `exists`/`role_has_permission` được dành cho truy vấn boolean.
- Model không phụ thuộc router, service hoặc repository.
- Response schema không chứa `password_hash` hay `refresh_token_hash`.

## Route quản trị và RBAC

Tất cả route dưới đây yêu cầu Bearer token hợp lệ và permission thuộc chức năng
`User Management`; các path đều có prefix `/api/v1`:

| Method | Path | Permission | Mục đích |
| --- | --- | --- | --- |
| GET | `/manager-users` | `read` | Danh sách có phân trang; `search` tìm theo ID/email/họ tên và `user_status` lọc `ACTIVE`/`INACTIVE` |
| POST | `/manager-users` | `create` | Tạo tài khoản, băm mật khẩu |
| GET | `/manager-users/{user_id}` | `read` | Chi tiết tài khoản |
| PATCH | `/manager-users/{user_id}` | `update` | Sửa role, email, tên, trạng thái hoặc mật khẩu; đổi mật khẩu sẽ thu hồi mọi session |
| GET | `/roles` | `read` | Danh sách role; `search` tìm theo ID, tên hoặc mô tả |
| POST | `/roles` | `create` | Tạo role cùng tập quyền ban đầu |
| GET | `/roles/{role_id}` | `read` | Chi tiết role |
| PATCH | `/roles/{role_id}` | `update` | Sửa tên hoặc mô tả role |
| GET | `/roles/{role_id}/permissions` | `read` | Danh sách quyền của role |
| PUT | `/roles/{role_id}/permissions` | `update` | Thay toàn bộ tập quyền nguyên tử |
| GET | `/permissions` | `read` | Permission catalog để cấu hình role |

Không cung cấp hard-delete cho manager user hoặc role. Tài khoản được vô hiệu hóa
bằng trạng thái `INACTIVE` để giữ quan hệ dữ liệu và audit history.

## Chưa triển khai

- MFA, giới hạn số lần đăng nhập sai và cơ chế phát hiện replay theo token family.

Use case nghiệp vụ mục tiêu và giới hạn của phiên bản hiện tại được mô tả tại
[`docs/usecase/authentication-session.md`](../../../docs/usecase/authentication-session.md).
