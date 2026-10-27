# Identity domain

Domain `identity` quản lý tài khoản quản trị, vai trò, quyền, đăng nhập và vòng
đời phiên. Domain này sở hữu các entity:

- `manager_user`;
- `user_session`;
- `role`;
- `role_permission`;
- `permission`;
- `management_function`;
- `action`.

## Cấu trúc thư mục

```text
identity/
├── models/                 SQLAlchemy ORM, mỗi bảng một file
│   └── manager_user.py     ManagerUserModel và ManagerUserStatus
├── schemas/                Pydantic request/response DTO
│   └── authentication.py   DTO cho login và Access Token
├── repositories/           Truy vấn database bằng Session được inject
├── services/
│   └── identity.py         Nghiệp vụ, transaction và điều phối repository/provider
├── security/
│   ├── password.py         Hash và xác minh mật khẩu bằng Argon2id
│   ├── jwt.py              Ký và xác minh Access Token RS256
│   └── refresh_token.py    Sinh Refresh Token opaque và SHA-256 hash
├── routers/
│   ├── identity.py         Khai báo các HTTP endpoint
│   ├── dependencies.py     FastAPI dependency và dependency injection
│   └── http.py             Cookie, lỗi xác thực và quy ước HTTP dùng chung
├── utils/
│   └── identity.py         Đồng hồ UTC và sinh ID dạng prefix-ddmmyy-xxxxxxxx
└── exceptions/
    ├── authentication.py   Lỗi credential và Access Token
    ├── manager_user.py     Lỗi tài khoản quản trị
    ├── role.py             Lỗi vai trò
    └── user_session.py     Lỗi phiên và Refresh Token
```

## Trách nhiệm từng tầng

### `models/`

Chỉ mô tả dữ liệu được lưu bằng SQLAlchemy: cột, khóa ngoại, enum và constraint.
Model không xác thực HTTP, không mở transaction và không chứa logic cấp token.
Enum chỉ phục vụ một entity được đặt cạnh entity đó; vì vậy
`ManagerUserStatus` nằm trong `models/manager_user.py` thay vì một file enum chung.

### `schemas/`

Định nghĩa dữ liệu vào/ra của API bằng Pydantic. Response schema không được chứa
`password_hash`, Refresh Token, Refresh Token hash hoặc khóa ký.

### `repositories/`

Chỉ thực hiện truy vấn bằng `Session` được truyền vào constructor. Repository có
thể `add()` hoặc thực hiện câu lệnh khóa bản ghi, nhưng không được `commit()` và
không được biết `Request`, `Response`, cookie hay HTTP status.

### `services/`

Chứa business rule và sở hữu transaction của write use case. `IdentityService`
điều phối đăng nhập, xác thực Access Token, refresh, logout và kiểm tra quyền.
`ManagerUserService` quản lý tài khoản; `RoleService` cung cấp các ca sử dụng đọc
vai trò và quyền.

Service chỉ làm việc với kiểu dữ liệu domain và các provider protocol. Service
không đọc header/cookie và không trả `HTTPException`.

### `security/`

Chứa các provider bảo mật cụ thể và protocol tương ứng:

- mật khẩu được hash một chiều bằng Argon2id;
- Access Token là JWT được ký bằng RS256, không phải dữ liệu mã hóa;
- Refresh Token là chuỗi opaque ngẫu nhiên, database chỉ lưu SHA-256 hash.

Khóa JWT thật phải được cấp qua cấu hình môi trường hoặc secret manager, không đặt
khóa mặc định trong source code.

### `routers/identity.py`

Chỉ giữ các controller HTTP:

- nhận và validate request schema;
- gọi service đã được inject;
- chuyển kết quả sang response schema;
- ánh xạ business exception sang HTTP response;
- đọc hoặc cập nhật Refresh Token cookie qua hàm hỗ trợ HTTP.

Mỗi endpoint là một hàm riêng theo cách tổ chức thông thường của FastAPI. Đây
không phải business logic; số hàm endpoint tương ứng với số API được công khai.

### `routers/dependencies.py`

Đây là composition root của Identity tại HTTP boundary. File này tạo password,
JWT và Refresh Token provider; ghép repository với cùng một database `Session`;
tạo `IdentityService`; đồng thời cung cấp dependency xác thực Bearer token.

File này được đặt trong `routers/` vì phụ thuộc trực tiếp vào FastAPI. Không chuyển
nó vào `core`: cách làm đó sẽ khiến `core` biết chi tiết riêng của Identity.

### `routers/http.py`

Chứa các thao tác chỉ có ý nghĩa tại HTTP boundary:

- đặt và xóa Refresh Token cookie;
- tính `expires_in` cho response;
- tạo phản hồi `401 Unauthorized` thống nhất;
- nhóm các business exception được xem là lỗi xác thực.

File này không thuộc `security/`, vì cookie và HTTP status không phải thuật toán
bảo mật. Nó cũng không thuộc `utils/`, vì phụ thuộc FastAPI và cấu hình HTTP.

### `utils/`

Chỉ dành cho hàm thuần có thể dùng lại trong domain mà không phụ thuộc FastAPI,
SQLAlchemy hoặc hạ tầng web. Hiện file cung cấp thời gian UTC và sinh ID có tám ký
tự hex. Không chuyển dependency wiring hay HTTP helper vào đây.

### `exceptions/`

Chứa business exception được chia theo đối tượng hoặc ca sử dụng. Các tầng khác
nên import từ `app.domains.identity.exceptions`; `exceptions/__init__.py` chịu
trách nhiệm re-export các exception công khai để caller không phụ thuộc vào tên
file con.

## Hướng phụ thuộc

```text
HTTP request
    -> routers/identity.py
        -> routers/dependencies.py
            -> services/identity.py
                -> repositories/*
                -> security/* (qua provider protocol)
                -> models/*
        -> routers/http.py
        -> schemas/*
```

Quy tắc quan trọng:

- router không truy vấn database trực tiếp;
- service không import FastAPI;
- repository không commit transaction;
- security provider không đọc request/cookie;
- model không phụ thuộc router, service hoặc repository;
- module nghiệp vụ không import `app.main` hay router.

## API hiện có

Tất cả endpoint được đăng ký dưới prefix `/api/v1`:

| Method | Path                       | Chức năng                                  |
| ------ | -------------------------- | ------------------------------------------ |
| `POST` | `/api/v1/identity/login`   | Đăng nhập, tạo session và cấp token        |
| `POST` | `/api/v1/identity/refresh` | Rotate Refresh Token và cấp Access Token   |
| `POST` | `/api/v1/identity/logout`  | Thu hồi session hiện tại và xóa cookie     |
| `GET`  | `/api/v1/identity/me`      | Lấy thông tin người dùng đang đăng nhập    |

Refresh Token chỉ được gửi qua cookie `HttpOnly`. Access Token được gửi trong
response body và client sử dụng qua header `Authorization: Bearer <token>`.

## Ranh giới transaction

Mỗi write use case mở một transaction trước truy vấn đầu tiên và bao trùm toàn bộ
thao tác liên quan. Login tạo session và ký token trong cùng use case; refresh khóa
session bằng `SELECT ... FOR UPDATE` trước khi rotate token; logout cập nhật
`revoked_at`. Request cleanup chỉ đóng hoặc rollback session còn dang dở.

## Phần chưa triển khai

- logout tất cả thiết bị qua HTTP;
- endpoint quản trị user/role/permission;
- dependency HTTP kiểm tra permission và trả `403`;
- MFA, rate limiting và khóa tạm thời sau nhiều lần đăng nhập sai;
- phát hiện Refresh Token replay theo token family;
- cấp và xoay khóa JWT từ secret manager của hạ tầng production.

Thiết kế chi tiết của luồng xác thực nằm tại
[`docs/authentication-design.md`](../../../docs/authentication-design.md).
