# POI — API địa điểm, nội dung và metadata audio

Phần này chuẩn bị API cho các nghiệp vụ nội bộ của POI, theo
[GROUP 2](../../../docs/database-design.md#22-group-2-point-of-interest-and-multilingual-narration-management).
Phạm vi ghi: `point_of_interest`, `poi_category_mapping`, `poi_content`, `content_audio`.
Không sửa frontend, Identity, Catalog, Listening, Offline hoặc Audit.
Dữ liệu tham chiếu ở domain khác chỉ được đọc. Tái sử dụng xác thực/phân quyền
Identity hiện có, không sửa login hoặc cấu hình tài khoản/token của người khác.
Các tích hợp storage/TTS, Audit và rebuild Offline vẫn chờ người phụ trách.

## Cách tổ chức tương tự Identity

```text
routers/poi.py             Endpoint public và quản trị, request/response schemas
routers/dependencies.py    Inject Session/service, dùng xác thực Identity hiện có
routers/http.py            Ánh xạ lỗi nghiệp vụ sang HTTP
schemas/point_of_interest.py DTO đọc public, tạo, sửa, trạng thái và đọc quản trị
services/poi.py            PoiService: đọc POI public
services/poi_management.py PoiAdminService: quản trị POI, transaction
services/poi_content.py    PoiContentService: nội dung và audio đi kèm, transaction
repositories/point_of_interest.py   Truy vấn/lưu POI, dùng chung public và quản trị
repositories/poi_category_mapping.py Truy vấn/thay mapping và đọc category tham chiếu
repositories/poi_content.py         Đọc content tiếng Anh đã publish, chặn xóa POI có content
repositories/content_audio.py       Kiểm tra metadata audio của content
exceptions.py             Lỗi nghiệp vụ
models/                   ORM POI hiện có
```

Luồng tạo mới: router kiểm tra quyền → schema validate body → service bắt đầu
transaction → repository kiểm tra region/category và dữ liệu trùng → thêm POI
và mapping → flush → commit → trả response. Lỗi sẽ rollback toàn bộ transaction.
PATCH/DELETE khóa dòng POI bằng `FOR UPDATE` để tuần tự hóa thay đổi cùng POI.
Session ghi tách khỏi Session xác thực, tương tự dependency quản trị Identity.

`app/route/api.py` chỉ được thêm đăng ký router mới. API public hiện có và các
service public được giữ nguyên. Repository POI có sẵn được mở rộng, giữ nguyên
hai truy vấn public `list_active()` và `get_active()`. Các repository chia theo
bảng như Identity; service phối hợp bốn repository cùng Session/transaction.
Schema và router được bổ sung trong các file có sẵn. Service được tách theo
trách nhiệm: `services/poi.py` giữ `PoiService` đọc public,
`services/poi_management.py` chứa `PoiAdminService` quản trị địa điểm,
`services/poi_content.py` chứa `PoiContentService` quản lý nội dung và audio.
Các class được export qua `services/__init__.py`. Trong `routers/poi.py`,
`router` và `admin_router` giữ hai nhóm endpoint với quyền truy cập riêng.

## Danh sách endpoint

Prefix: `/api/v1/admin/pois`.

| Method | Path | Quyền `POI Management` | Kết quả |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/pois` | read | 200, danh sách phân trang |
| GET | `/api/v1/admin/pois/options` | read | 200, region/category cho form |
| GET | `/api/v1/admin/pois/{id}` | read | 200, chi tiết |
| POST | `/api/v1/admin/pois` | create | 201, POI vừa tạo |
| PATCH | `/api/v1/admin/pois/{id}` | update | 200, POI sau cập nhật |
| PATCH | `/api/v1/admin/pois/{id}/status` | update | 200, POI sau đổi trạng thái |
| DELETE | `/api/v1/admin/pois/{id}` | delete | 204, không có body |

Tất cả endpoint yêu cầu Bearer token và session hợp lệ qua dependency Identity
hiện có; không mở public endpoint quản trị hoặc tắt phân quyền để chạy demo.
Code Identity và đăng nhập frontend vẫn được giữ nguyên. Các vấn đề hiện có
ở Identity (login query trước `session.begin()`, seed dùng hash giả, cấu hình RSA)
cần được người phụ trách Identity xử lý khi tích hợp đăng nhập thật.

### Danh sách, tìm kiếm và dữ liệu cho form

```http
GET /api/v1/admin/pois?offset=0&limit=20&search=museum&poi_status=INACTIVE
```

Filter tùy chọn: `search` theo ID/tên/địa chỉ/QR, `poi_status=ACTIVE|INACTIVE`,
`region_id`, `category_id`. Các filter kết hợp bằng AND; search không phân biệt
hoa thường và coi `%`, `_` là ký tự thường. Không chấp nhận search chỉ có khoảng
trắng. `offset >= 0`, `limit` từ 1 đến 100, mặc định 0/20. Thứ tự ổn định:
`created_at DESC, id ASC`. Không join category trực tiếp làm trùng POI khi đếm.

```json
{"items": [], "total": 0, "offset": 0, "limit": 20}
```

Mỗi item/response chi tiết gồm metadata POI, người tạo/cập nhật, `category_ids`,
`can_activate`. Decimal được trả dạng chuỗi JSON; timestamp có timezone.
`can_activate` chỉ phản ánh điều kiện content/audio, không phản ánh quyền người dùng.
`GET /options` trả `{"regions": [...], "categories": [...]}` với ID/tên/mã thật
trong Catalog, không tạo hoặc sửa các bản ghi này.

### Tạo POI

```json
{
  "region_id": "<ID region thật từ options>",
  "poi_name": "Bảo tàng",
  "poi_location": "Địa chỉ duy nhất của địa điểm",
  "poi_qr_code": "museum-example",
  "poi_image_url": "https://assets.example/poi/image.webp",
  "latitude": "10.776900",
  "longitude": "106.700900",
  "trigger_radius_meter": "50.00",
  "category_ids": ["<ID category thật từ options>"]
}
```

- Sinh ID `poi-ddmmyy-xxxxxxxx`, timestamp UTC và người thao tác ở backend.
- POI mới luôn INACTIVE. Gửi `poi_status=ACTIVE` khi tạo sẽ nhận 422.
- Region/category phải tồn tại, category không được trùng, tối đa 100 ID.
- QR/địa chỉ duy nhất; vĩ độ `[-90,90]`, kinh độ `[-180,180]`, bán kính > 0.
- Tọa độ tối đa 6 chữ số thập phân; bán kính tối đa 2, phù hợp cột NUMERIC.
- Ảnh bắt buộc là URL HTTP(S) không chứa thông tin đăng nhập, tối đa 1000 ký tự.
  `image_checksum_sha256` tùy chọn, nhận null hoặc 64 ký tự hex.
- Field không khai báo bị từ chối; không nhận `created_by`, timestamp hoặc ID từ web.

### Sửa và đổi trạng thái

PATCH chỉ cập nhật field được gửi. Không chấp nhận body rỗng; chỉ checksum ảnh
được nhận null. Không gửi `category_ids` thì giữ mapping; gửi `[]` thì bỏ hết.
Đổi URL ảnh mà không gửi checksum mới sẽ xóa checksum cũ.

Có thể đổi trạng thái trong PATCH chung hoặc endpoint `/status`:

```json
{"poi_status": "ACTIVE"}
```

Muốn ACTIVE phải có content ngôn ngữ `en` đã PUBLISHED và audio có URL HTTP(S),
kích thước/thời lượng dương, checksum SHA-256 hợp lệ, MIME audio được hỗ trợ,
nguồn RECORD/TTS. Kiểm tra chấp nhận tên nguồn seed cũ
`pre_generated`/`tts_generated` và trạng thái content không phân biệt hoa thường.
PATCH giữ POI ACTIVE cũng kiểm tra điều kiện này. Từ chối thì trả 409 và không
lưu một phần thay đổi. Không có request mạng đến storage trong transaction.

### Xóa và lỗi

POI còn content hoặc được lịch sử nghe/item offline tham chiếu không thể xóa.
Nên chuyển INACTIVE trong trường hợp này. Chỉ xóa POI độc lập và mapping của nó;
không cascade xóa dữ liệu của người khác qua API này.

| HTTP | Ý nghĩa |
| --- | --- |
| 401 | Token/session không hợp lệ, theo Identity hiện có |
| 403 | Thiếu permission tương ứng |
| 404 | Không có POI, region hoặc category được tham chiếu |
| 409 | QR/địa chỉ trùng, không đủ điều kiện active hoặc bị chặn xóa |
| 422 | Body/filter không hợp lệ |
| 503 | Thiếu cấu hình JWT theo dependency Identity |

Lỗi nghiệp vụ trả `{"detail":"..."}`. Lỗi validate request của FastAPI trả
`detail` dạng danh sách. Repository không commit; service xử lý các vi phạm
constraint đã biết sau rollback, không che lỗi database không liên quan.

## Migration và tương thích

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Revision `0005_poi_management` sau `0004_identity_constraints` chỉ tác động hai
bảng thuộc POI: thêm UNIQUE địa chỉ, CHECK tọa độ/bán kính và index tọa độ/category.
Không chạy migration ở startup. Dữ liệu cũ vi phạm ràng buộc làm migration thất
bại; không tự sửa địa chỉ hoặc xóa bản ghi. Không chỉnh lịch sử migration.

Những khác biệt với tài liệu được giữ để không phá contract hiện tại:

- API quản trị nhận/trả ACTIVE/INACTIVE, nhưng lưu `active`/`inactive`. Các giá trị
  cũ khác như `maintenance` được xem là INACTIVE; không đổi hàng loạt dữ liệu seed.
- API public `/api/v1/pois` vẫn chỉ trả bản ghi có `poi_status='active'`, schema và
  phân trang như trước. Không thêm CHECK uppercase lên cột trạng thái hiện có.
- Không siết nullability của ảnh/người cập nhật cho bản ghi cũ. API tạo mới yêu
  cầu ảnh và tự điền người thao tác; response vẫn đọc được bản ghi cũ thiếu ảnh.

## Phần phối hợp sau này

- API nhận metadata của ảnh đã upload; chưa upload ảnh hoặc tính/xác minh checksum
  từ bytes. Caller phải dùng asset mới tại URL bất biến; không ghi đè file cũ.
- `can_activate` kiểm tra metadata audio, chưa xác minh file thực trên storage.
- Rebuild Offline Package khi metadata/category thay đổi cần tích hợp với domain
  Offline. API hiện chưa đánh dấu/tạo job rebuild hay tăng `package_version`.
- Chưa tự ghi AuditLog. API content/audio được mô tả ở phần bên dưới.
- Chưa gọi API ở web, chưa sửa CORS, đăng nhập hoặc cấu hình token của frontend.

Khi viết tiếp, làm từng use case theo thứ tự schema → repository → service →
dependency/router → đăng ký route, giống Identity. Các thao tác thay content/audio
đều khóa cùng dòng POI và giữ điều kiện tiếng Anh khả dụng cho POI ACTIVE.

## API nội dung và phiên bản

Prefix `/api/v1/admin/poi-contents`; quyền thuộc `Narration Content Management`.

| Method | Path sau prefix | Quyền | Chức năng |
| --- | --- | --- | --- |
| GET | đường dẫn gốc | read | Danh sách, phân trang, tìm kiếm |
| GET | `/options` | read | POI và Language cho form (chỉ đọc Catalog) |
| GET | `/{id}` | read | Chi tiết kèm metadata audio nếu có |
| POST | đường dẫn gốc | create | Tạo DRAFT, tự cấp số phiên bản |
| POST | `/{id}/versions` | create | Tạo DRAFT mới từ bản cũ, không sao chép audio |
| PATCH | `/{id}` | update | Chỉ sửa DRAFT/REJECTED |
| DELETE | `/{id}` | delete | Chỉ xóa DRAFT/REJECTED chưa được tham chiếu |
| POST | `/{id}/submit` | update | DRAFT/REJECTED → WAITING_APPROVAL |
| POST | `/{id}/approve` | approve | WAITING_APPROVAL → APPROVED |
| POST | `/{id}/reject` | approve | WAITING_APPROVAL → REJECTED |
| POST | `/{id}/publish` | publish | APPROVED → PUBLISHED khi audio hợp lệ |

Danh sách trả `{items,total,offset,limit}`, mặc định 0/20, limit tối đa 100.
Filter: `poi_id`, `language_id`, `content_status`, `search` theo ID/tiêu đề.
Status API dùng chữ hoa; đọc được trạng thái chữ thường trong seed cũ.

Body tạo mới:

```json
{
  "poi_id": "<ID POI thật>",
  "language_id": "<ID language thật>",
  "narration_title": "Tên bài thuyết minh",
  "narration_script": "Nội dung thuyết minh"
}
```

Backend cấp ID, phiên bản và người tạo; không nhận trạng thái/version/actor từ
client. Script không rỗng, tối đa 100.000 ký tự. Language mới phải SUPPORTED hoặc
giá trị tương thích `active` của seed. Khi nhân bản, gửi `{}` để dùng lại văn bản
hoặc gửi title/script thay thế. Version được cấp `max + 1` trong phạm vi
POI–Language dưới khóa POI, chống hai request trùng version.

Không sửa/xóa bản WAITING_APPROVAL/APPROVED/PUBLISHED/ARCHIVED; tạo phiên bản mới
khi cần chỉnh sửa. Sửa văn bản DRAFT/REJECTED xóa metadata audio cũ không còn
khớp nếu chưa được package tham chiếu; không xóa file storage. Lưu REJECTED đưa
về DRAFT; có thể gửi lại trực tiếp từ REJECTED. Trường duyệt/xuất bản cũ được xóa
khi gửi lại. Tác giả không tự phê duyệt, phù hợp luồng duyệt prototype web.
Reject chưa nhận ghi chú vì schema hiện không lưu lý do; việc lưu reviewer/lý do
từ chối chi tiết chờ thiết kế Audit, không nhận rồi bỏ dữ liệu.

Publish chỉ dùng audio hợp lệ đã có, chưa gọi TTS. Thiếu audio trả 409 và giữ
APPROVED; bản PUBLISHED cũ vẫn phục vụ. Khi thành công, archive bản cũ cùng
POI–Language và publish bản mới trong một transaction. Không publish bản thấp
hơn version đang phân phối. ARCHIVED giữ nội dung/audio cho tham chiếu lịch sử.

## API metadata audio

Quyền cũng thuộc `Narration Content Management`:

| Method | Endpoint | Quyền |
| --- | --- | --- |
| GET | `/api/v1/admin/audios` | read |
| GET | `/api/v1/admin/audios/{audio_id}` | read |
| GET | `/api/v1/admin/poi-contents/{id}/audio` | read |
| PUT | `/api/v1/admin/poi-contents/{id}/audio` | update |
| DELETE | `/api/v1/admin/poi-contents/{id}/audio` | delete |

Danh sách có cùng phân trang; filter `poi_id`, `language_id`, `poi_content_id`,
`audio_source_type=RECORD|TTS`, `search` theo ID/tiêu đề content. PUT trả 200 khi
thêm hoặc thay metadata; mỗi content có tối đa một audio:

```json
{
  "audio_url": "https://assets.example/audio/<checksum>.mp3",
  "audio_size": 100000,
  "audio_source_type": "RECORD",
  "audio_duration_sec": 30,
  "audio_mime_type": "audio/mpeg",
  "audio_checksum_sha256": "<64 ký tự hex SHA-256 thật của file>"
}
```

PUT yêu cầu đủ metadata của file đã upload/xác minh trước đó: URL HTTP(S) không
chứa credentials, size/duration dương, checksum hợp lệ. MIME hỗ trợ: audio/mpeg,
audio/aac, audio/ogg, audio/wav, audio/mp4, audio/webm. Size dùng bigint, duration
dùng integer. Source TTS chỉ mô tả asset TTS đã có, không tạo TTS mới.

Cho phép gắn/thay metadata khi DRAFT/REJECTED/APPROVED/PUBLISHED; đóng băng khi
WAITING_APPROVAL và ARCHIVED. Thay audio PUBLISHED là đổi metadata nguyên tử sang
asset mới hợp lệ, giữ ID bản ghi audio. Checksum đổi bắt buộc URL mới. Không xóa
audio PUBLISHED/ARCHIVED; bản khác chỉ xóa nếu chưa có item offline tham chiếu.
Các thao tác không làm POI ACTIVE mất audio tiếng Anh khả dụng. Không tự thay
package hoặc xóa file storage. Giữ UNIQUE checksum của schema hiện có: đăng ký
cùng checksum cho hai audio sẽ nhận 409; cần thống nhất riêng nếu muốn nhiều
phiên bản dùng chung asset, không đổi natural key của seed trong đợt này.

## Chọn thuyết minh online và fallback

```http
GET /api/v1/pois/{poi_id}/narration?language_code=vi
```

Endpoint public chỉ phục vụ POI `active`. Chọn PUBLISHED của ngôn ngữ yêu cầu
có audio hợp lệ và language đang được hỗ trợ; nếu không có thì dùng tiếng Anh.
Mặc định en. Không có cả hai thì 404; POI ẩn/không tồn tại cũng 404. Response có
`requested_language_code`, `language_code`, `is_fallback`, nội dung, version và
metadata audio; không trả người tạo/phê duyệt hoặc dữ liệu tài khoản.

## Migration nội dung/audio và điểm chờ tích hợp

Revision `0006_poi_content_audio` chỉ thay hai bảng POI: CHECK version/trạng thái/
thời gian, mỗi cặp POI–Language tối đa một PUBLISHED bằng partial unique index,
mỗi content tối đa một audio, CHECK audio size/duration/source, bigint cho size
và index nguồn audio. Giá trị seed cũ vẫn được chấp nhận. Dữ liệu xung đột làm
migration thất bại, không tự xóa bản ghi. Downgrade về integer từ chối size vượt
giới hạn integer, không cắt dữ liệu. Không reset database phát triển.

Phần nội bộ POI đã thực hiện; các việc sau còn chờ bên phụ trách:

| Điểm tích hợp | Hiện tại |
| --- | --- |
| Identity | Dùng dependency/quyền hiện có; không sửa login, tài khoản hay khóa JWT |
| Catalog | Chỉ đọc; chưa xử lý cascade khi bên Catalog đổi trạng thái |
| Storage/upload | Chưa upload/đọc bytes, xác minh checksum/MIME thực hoặc dọn asset |
| TTS | Chưa chọn provider, gọi API sinh audio, retry job hoặc tính phí |
| Offline | Chưa đánh dấu/rebuild package khi dữ liệu đổi, không tăng package_version |
| Audit | Chưa ghi sự kiện, reviewer/lý do từ chối hoặc lịch sử thao tác |
| Frontend | Chưa gọi API hoặc sửa giao diện/đăng nhập |

Khi nối các phần này, dùng service collaborator rõ ràng và giữ transaction/khóa
POI; không dùng endpoint giả thành công hoặc bỏ kiểm tra quyền thay cho tích hợp.
