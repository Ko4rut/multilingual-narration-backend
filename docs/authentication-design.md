# Thiết kế xác thực, JWT và quản lý phiên đăng nhập

Luồng nghiệp vụ tổng thể từ đăng nhập đến đăng xuất được mô tả tại
[usecase/authentication-session.md](usecase/authentication-session.md).

## 1. Phạm vi và trạng thái triển khai

Tài liệu này mô tả hợp đồng bảo mật mục tiêu cho người dùng quản trị
(`manager_user`), gồm đăng nhập, cấp Access Token, làm mới token, đăng xuất,
thu hồi phiên, đổi mật khẩu và kiểm tra quyền.

Hiện tại domain Identity đã có:

- `ManagerUserModel`, `UserSessionModel` và các repository tương ứng;
- Argon2id password provider dùng để hash, verify và nâng cấp password hash;
- JWT provider ký và kiểm tra Access Token bằng `RS256`, `kid`, issuer, audience
  và các claim thời gian bắt buộc;
- kiểm tra trạng thái tài khoản `ACTIVE`/`INACTIVE`;
- tạo, kiểm tra và thu hồi phiên đăng nhập;
- thu hồi toàn bộ phiên khi tài khoản bị vô hiệu hóa hoặc đổi mật khẩu;
- truy vấn quyền theo role, function và action.

Các phần sau **chưa được triển khai** và được mô tả như hợp đồng mục tiêu:

- HTTP endpoint cho login, refresh, logout và thông tin người dùng hiện tại;
- cấu hình khóa ký, cookie, issuer, audience và thời hạn token;
- dependency xác thực request và ánh xạ lỗi HTTP;
- refresh-token rotation và xử lý tranh chấp khi refresh đồng thời.

## 2. Nguyên tắc bảo mật

1. Mật khẩu không được mã hóa hai chiều và không được lưu dạng rõ. Mật khẩu phải
   được **hash một chiều** bằng Argon2id với salt ngẫu nhiên cho từng mật khẩu.
2. Access Token là JWT được **ký**, không phải dữ liệu được mã hóa. Client có thể
   đọc payload; vì vậy không đặt mật khẩu, refresh token hoặc dữ liệu bí mật trong
   JWT.
3. Refresh Token là chuỗi opaque sinh ngẫu nhiên bằng CSPRNG. Database chỉ lưu
   SHA-256 của token, không lưu token gốc.
4. Tất cả endpoint xác thực chỉ hoạt động qua HTTPS trong môi trường thật.
5. Access Token có thời hạn ngắn. Refresh Token có thời hạn dài hơn nhưng gắn với
   một bản ghi `user_session` có thể bị thu hồi.
6. Không log mật khẩu, JWT hoàn chỉnh, refresh token hoặc khóa ký.
7. Lỗi đăng nhập dùng cùng một thông báo cho email không tồn tại và mật khẩu sai
   để tránh dò tìm tài khoản.

## 3. Các loại credential

| Credential    | Định dạng đề xuất             | Thời hạn mặc định    | Lưu phía server                                       |
| ------------- | ----------------------------- | -------------------- | ----------------------------------------------------- |
| Password      | Argon2id encoded hash         | Đến khi đổi mật khẩu | `manager_user.password_hash`                          |
| Access Token  | JWT ký bằng `RS256`           | 15 phút              | Không lưu token; kiểm tra `sid` với session           |
| Refresh Token | 32 byte ngẫu nhiên, Base64URL | 30 ngày              | Chỉ lưu SHA-256 tại `user_session.refresh_token_hash` |

Các thời hạn phải lấy từ cấu hình, không hard-code trong router hoặc service.

## 4. Nội dung Access Token

JWT Access Token sử dụng header tối thiểu:

```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "auth-key-2026-01"
}
```

Payload đề xuất:

```json
{
  "iss": "mnr-backend",
  "aud": "mnr-admin-web",
  "sub": "user-261026-12345678",
  "sid": "sess-261026-12345678",
  "role_id": "role-12345678",
  "type": "access",
  "jti": "random-unique-token-id",
  "iat": 1793001600,
  "nbf": 1793001600,
  "exp": 1793002500
}
```

Ý nghĩa các claim:

| Claim     | Bắt buộc | Ý nghĩa                                                  |
| --------- | -------- | -------------------------------------------------------- |
| `iss`     | Có       | Dịch vụ phát hành token                                  |
| `aud`     | Có       | Ứng dụng được phép sử dụng token                         |
| `sub`     | Có       | ID của `manager_user`                                    |
| `sid`     | Có       | ID của `user_session`                                    |
| `role_id` | Có       | Role tại thời điểm phát hành; không thay thế kiểm tra DB |
| `type`    | Có       | Phải bằng `access`, ngăn dùng nhầm loại token            |
| `jti`     | Có       | ID duy nhất của JWT, phục vụ audit/tracing an toàn       |
| `iat`     | Có       | Thời điểm phát hành                                      |
| `nbf`     | Có       | Thời điểm token bắt đầu hợp lệ                           |
| `exp`     | Có       | Thời điểm token hết hạn                                  |

Không đưa toàn bộ permission vào JWT. Quyền có thể thay đổi trong thời gian token
còn hiệu lực; service phải kiểm tra quyền hiện tại từ database hoặc cache có thời
hạn ngắn và cơ chế invalidation rõ ràng.

## 5. Quy trình đăng nhập

Endpoint mục tiêu:

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@mnr.local",
  "password": "user supplied password"
}
```

Quy trình xử lý:

1. Router kiểm tra request schema rồi gọi `IdentityService`; router không truy vấn
   database và không tự ký token.
2. Service chuẩn hóa email bằng cách trim và chuyển về chữ thường.
3. Trong một transaction, repository tìm tài khoản theo email.
4. Password provider dùng Argon2id để verify mật khẩu với `password_hash`.
5. Nếu email hoặc mật khẩu sai, trả cùng lỗi `InvalidCredentials`.
6. Nếu `user_status != ACTIVE`, từ chối đăng nhập.
7. Sinh ID phiên `sess-ddmmyy-xxxxxxxx`.
8. Sinh Refresh Token bằng ít nhất 32 byte ngẫu nhiên, tính SHA-256 và chỉ lưu hash
   vào `user_session` cùng `expires_at`, `created_at`, `revoked_at = NULL`.
9. Cập nhật `manager_user.last_login_at`.
10. Sau khi transaction thành công, token provider ký JWT Access Token chứa `sub`
    và `sid` của phiên vừa tạo.
11. Trả Access Token và gửi Refresh Token bằng cookie bảo mật.

Response body đề xuất:

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "user-261026-12345678",
    "role_id": "role-12345678",
    "email": "admin@mnr.local",
    "full_name": "Administrator",
    "user_status": "ACTIVE"
  }
}
```

Refresh Token không xuất hiện trong JSON nếu ứng dụng web dùng cookie. Cookie đề
xuất:

```text
HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
```

Access Token nên giữ trong memory của ứng dụng web, không lưu vào `localStorage`.

## 6. Xác thực request bằng Access Token

Client gửi:

```http
Authorization: Bearer <access-token>
```

Dependency xác thực thực hiện theo thứ tự:

1. Chỉ chấp nhận thuật toán nằm trong allowlist cấu hình; không tin giá trị `alg`
   từ token để tự chọn thuật toán.
2. Chọn public key theo `kid` và kiểm tra chữ ký.
3. Kiểm tra `iss`, `aud`, `type`, `exp`, `nbf`, `iat`, `sub` và `sid`.
4. Đọc `user_session` theo `sid`; phiên phải tồn tại, chưa hết hạn và chưa bị thu
   hồi.
5. Đọc `manager_user` theo `sub`; tài khoản phải tồn tại và có trạng thái `ACTIVE`.
6. Bảo đảm `user_session.user_id == sub`.
7. Với endpoint yêu cầu quyền, gọi RBAC bằng role hiện tại trong database, không
   chỉ tin `role_id` trong JWT.

Việc kiểm tra session trên mỗi request cho phép logout, đổi mật khẩu hoặc vô hiệu
hóa tài khoản có hiệu lực ngay. Nếu sau này tối ưu bằng cache, thời hạn cache phải
ngắn và phải có cơ chế xóa cache khi thu hồi session.

Quy ước lỗi:

- `401 Unauthorized`: thiếu token, token sai/hết hạn, session sai/hết hạn/bị thu
  hồi, hoặc tài khoản không còn hoạt động;
- `403 Forbidden`: đã xác thực nhưng không có permission cần thiết;
- response `401` kèm `WWW-Authenticate: Bearer`;
- không trả chi tiết chữ ký, claim hoặc bước xác thực bị lỗi cho client.

## 7. Làm mới Access Token

Endpoint mục tiêu:

```http
POST /api/v1/auth/refresh
Cookie: refresh_token=<opaque-token>
```

Quy trình:

1. Hash token nhận được bằng SHA-256.
2. Tìm `user_session` theo `refresh_token_hash` và khóa bản ghi trong transaction
   để hai request refresh đồng thời không cùng thành công.
3. Kiểm tra session tồn tại, chưa hết hạn, chưa bị thu hồi.
4. Kiểm tra tài khoản sở hữu session vẫn là `ACTIVE`.
5. Sinh Refresh Token mới, cập nhật hash và thời hạn theo chính sách rotation.
6. Phát hành Access Token mới với cùng `sub`, `sid`, role hiện tại và `jti` mới.
7. Commit transaction rồi thay cookie Refresh Token.

Refresh Token cũ hết hiệu lực ngay sau khi rotation thành công. Với schema hiện
tại, token cũ dùng lại sẽ được xem là token không hợp lệ. Nếu cần phát hiện replay
và thu hồi toàn bộ “token family”, phải bổ sung bảng lịch sử/token family bằng một
migration riêng; không nên giả lập tính năng đó chỉ bằng `user_session` hiện tại.

## 8. Đăng xuất và thu hồi phiên

### Đăng xuất thiết bị hiện tại

`POST /api/v1/auth/logout` nhận Refresh Token từ cookie, tìm session bằng hash và
đặt `revoked_at` bằng thời điểm hiện tại. Endpoint phải idempotent và luôn xóa
cookie phía client.

### Đăng xuất tất cả thiết bị

`POST /api/v1/auth/logout-all` xác thực người dùng rồi cập nhật `revoked_at` cho
mọi session đang hoạt động của `user_id`.

### Thu hồi tự động

Tất cả session đang hoạt động phải bị thu hồi khi:

- tài khoản chuyển từ `ACTIVE` sang `INACTIVE`;
- mật khẩu được thay đổi hoặc reset;
- quản trị viên thực hiện thao tác thu hồi toàn bộ phiên;
- hệ thống phát hiện refresh-token replay khi đã có token-family tracking.

Access Token đã cấp cũng bị chặn ngay vì dependency kiểm tra `sid` và trạng thái
tài khoản trên mỗi request.

## 9. Hash mật khẩu

Password provider production dùng `pwdlib` với Argon2id. Không tự cài đặt thuật
toán hash.
Provider cần có hai hàm độc lập:

```python
def hash_password(plain_password: str) -> str: ...
def verify_password(plain_password: str, encoded_hash: str) -> bool: ...
```

Quy tắc:

- salt được thư viện sinh ngẫu nhiên cho từng mật khẩu;
- tham số memory/time/parallelism lấy từ cấu hình bảo mật và được benchmark trên
  hạ tầng triển khai;
- giới hạn hợp lý độ dài password trước khi hash để tránh yêu cầu tài nguyên bất
  thường;
- khi thông số hash cũ không còn đạt chính sách, rehash sau lần đăng nhập thành
  công;
- không trim hoặc đổi hoa/thường mật khẩu do người dùng nhập;
- password reset dùng token ngẫu nhiên một lần, thời hạn ngắn, chỉ lưu hash;
- không đưa `password_hash` vào response schema, audit snapshot hoặc log.

SHA-256 phù hợp để tra cứu Refresh Token có entropy cao, nhưng **không phù hợp để
hash mật khẩu** vì quá nhanh và dễ bị brute force.

## 10. Quản lý khóa JWT

JWT provider hiện thực dùng `RS256`:

- private key chỉ có dịch vụ phát hành token được đọc;
- public key dùng để kiểm tra chữ ký;
- khóa không được commit vào Git, image hoặc `.env.example` dưới dạng giá trị thật;
- production lấy khóa từ secret manager;
- mỗi khóa có `kid` riêng;
- khi rotate, key mới dùng để ký; public key cũ được giữ đến khi mọi Access Token
  cũ hết hạn rồi mới loại bỏ;
- không dùng cùng một secret cho database, JWT và các dịch vụ khác.

JWT ký chỉ bảo đảm tính toàn vẹn và nguồn phát hành. Payload không bí mật. Nếu có
nhu cầu bảo mật payload, phải đánh giá JWE riêng; với các claim định danh tối thiểu
trong tài liệu này, JWE không cần thiết.

## 11. Cấu hình dự kiến

Các setting sau nên được thêm vào `app/core/config.py` khi triển khai provider:

```text
JWT_ALGORITHM=RS256
JWT_ISSUER=mnr-backend
JWT_AUDIENCE=mnr-admin-web
JWT_ACTIVE_KEY_ID=auth-key-2026-01
JWT_PRIVATE_KEY=<secret, không đặt trong .env.example>
JWT_PUBLIC_KEYS=<key set hoặc nguồn secret manager>
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=2592000
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=strict
```

Ứng dụng phải fail fast khi chạy production mà thiếu khóa hoặc dùng cấu hình yếu.
Không log `SecretStr` hay full connection/key material.

## 12. Transaction và trách nhiệm từng tầng

| Tầng              | Trách nhiệm                                                                     |
| ----------------- | ------------------------------------------------------------------------------- |
| Router            | Parse schema, cookie/header, dependency wiring, response model và HTTP status   |
| Service           | Quy tắc đăng nhập, transaction, tạo/thu hồi session và điều phối token provider |
| Repository        | Truy vấn SQLAlchemy bằng Session được inject; không commit                      |
| Password provider | Hash, verify và kiểm tra nhu cầu rehash                                         |
| Token provider    | Sinh refresh token, hash token, ký và verify JWT                                |
| Database          | UNIQUE/FK/CHECK/index và trạng thái phiên bền vững                              |

Một write use case sở hữu một transaction bao trùm toàn bộ read/write liên quan.
Không commit trong repository. Không phát hành token cho client nếu transaction tạo
hoặc rotate session chưa thành công.

## 13. Audit và giám sát

Có thể ghi nhận các sự kiện sau mà không chứa credential:

- login thành công/thất bại;
- refresh thành công/thất bại;
- logout, logout-all và session bị thu hồi;
- đổi/reset mật khẩu;
- tài khoản bị chuyển trạng thái;
- kiểm tra quyền bị từ chối.

Log kỹ thuật chỉ nên chứa request/correlation ID, user ID khi đã xác định, session
ID, loại sự kiện, thời điểm và kết quả. Không log email đầy đủ nếu không cần thiết;
không log password, JWT, Refresh Token, hash của credential hoặc private key.

Nên rate-limit login, refresh và reset-password theo IP và định danh tài khoản;
cảnh báo khi có nhiều lần thất bại, refresh token reuse hoặc hoạt động bất thường.

## 14. API mục tiêu

| Method | Path                      | Xác thực       | Mục đích                                     |
| ------ | ------------------------- | -------------- | -------------------------------------------- |
| `POST` | `/api/v1/auth/login`      | Không          | Đăng nhập, tạo session và cấp token          |
| `POST` | `/api/v1/auth/refresh`    | Refresh cookie | Rotate refresh token và cấp Access Token mới |
| `POST` | `/api/v1/auth/logout`     | Refresh cookie | Thu hồi session hiện tại                     |
| `POST` | `/api/v1/auth/logout-all` | Bearer token   | Thu hồi mọi session của người dùng           |
| `GET`  | `/api/v1/auth/me`         | Bearer token   | Trả thông tin tài khoản và role hiện tại     |

Các endpoint quản trị user/role phải yêu cầu permission phù hợp; không được xem
việc có JWT hợp lệ là đồng nghĩa với có quyền quản trị.

## 15. Tiêu chí kiểm thử khi triển khai

- login đúng tạo đúng một session và không trả password hash/refresh-token hash;
- email không tồn tại và password sai trả cùng một lỗi;
- tài khoản `INACTIVE` không thể login hoặc refresh;
- JWT sai chữ ký, sai issuer/audience/type, hết hạn hoặc chưa có hiệu lực bị từ chối;
- không chấp nhận thuật toán ngoài allowlist;
- refresh token chỉ được lưu dưới dạng SHA-256;
- refresh rotation vô hiệu hóa token cũ và xử lý đúng hai request đồng thời;
- logout chỉ thu hồi session hiện tại; logout-all thu hồi mọi session;
- đổi mật khẩu hoặc vô hiệu hóa tài khoản thu hồi mọi session;
- session hết hạn/bị thu hồi không thể dùng Access Token hoặc refresh;
- `401` và `403` được phân biệt đúng;
- permission được đọc theo dữ liệu hiện tại, không chỉ theo claim cũ trong JWT;
- cookie có `HttpOnly`, `Secure`, `SameSite` và `Path` đúng trong production;
- không có credential hoặc khóa bí mật trong log, response và audit snapshot.
