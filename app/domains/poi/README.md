# POI — API địa điểm, nội dung và metadata audio

Phần này chuẩn bị API cho các nghiệp vụ nội bộ của POI, theo
[GROUP 2](../../../docs/database-design.md#22-group-2-point-of-interest-and-multilingual-narration-management).
Phạm vi ghi: `point_of_interest`, `poi_category_mapping`, `poi_content`, `content_audio`.
Không sửa frontend, Identity, Catalog, Listening, Offline hoặc Audit.
Dữ liệu tham chiếu ở domain khác chỉ được đọc. Tái sử dụng xác thực/phân quyền
Identity hiện có, không sửa login hoặc cấu hình tài khoản/token của người khác.
TTS hiện dùng gTTS và persistent local volume gắn tại `assets/audio/tts` ở thư
mục gốc backend; các file MP3 sinh lúc chạy không được commit.
Object storage production, Audit và rebuild Offline vẫn chờ triển khai.

## Cách tổ chức tương tự Identity

```text
routers/poi.py             Endpoint public và quản trị, request/response schemas
routers/dependencies.py    Inject Session/service, dùng xác thực Identity hiện có
routers/http.py            Ánh xạ lỗi nghiệp vụ sang HTTP
schemas/point_of_interest.py DTO đọc public, tạo, sửa, trạng thái và đọc quản trị
services/point_of_interest.py PublicPointOfInterestService và
                            PointOfInterestService: POI public/quản trị
services/poi_content.py    PoiContentService: vòng đời nội dung thuyết minh
services/content_audio.py  ContentAudioService: metadata audio của content
repositories/point_of_interest.py   Truy vấn/lưu POI, dùng chung public và quản trị
repositories/poi_category_mapping.py Đọc và thay toàn bộ category mapping của POI
repositories/poi_content.py         Truy vấn nội dung thuyết minh và ngôn ngữ
repositories/content_audio.py       Kiểm tra metadata audio của content
providers/tts.py          Sinh TTS và lưu file audio cục bộ
providers/qr_code.py      Sinh payload và render ảnh QR của POI
providers/image_checksum.py Tải ảnh an toàn và tính checksum SHA-256
providers/audio_asset.py Tải audio an toàn và tự xác minh metadata/checksum
exceptions/               Lỗi nghiệp vụ và public exports của domain
utils/utils.py            Sinh ID, escape LIKE và đọc tên database constraint
models/                   ORM POI hiện có
```

Luồng tạo mới: router kiểm tra quyền → schema validate body → service bắt đầu
transaction → repository POI/Catalog kiểm tra region/category → thêm POI
và mapping → flush → commit → trả response. Lỗi sẽ rollback toàn bộ transaction.
PATCH khóa dòng POI bằng `FOR UPDATE` để tuần tự hóa thay đổi cùng POI.
Session ghi tách khỏi Session xác thực, tương tự dependency quản trị Identity.

`app/route/api.py` chỉ được thêm đăng ký router mới. API public hiện có và các
service public được giữ nguyên. Repository POI dùng `get_all()` chung cho danh sách
public, quản trị và dữ liệu chọn; `get_by_id(active_only=True)` bảo vệ API public.
Các repository chia theo
bảng như Identity; service phối hợp repository POI với repository Catalog đọc-only
bằng cùng Session/transaction. Repository mapping không truy vấn trực tiếp bảng
`poi_category`.
Schema và router được bổ sung trong các file có sẵn. Tên file service bám theo
repository tương ứng: `point_of_interest.py`, `poi_content.py` và
`content_audio.py`. File `point_of_interest.py` có hai class để tách API public
khỏi nghiệp vụ quản trị nhưng vẫn cùng tài nguyên/repository.
`poi_category_mapping` không có service riêng vì đây là bảng liên kết được điều
phối trong `PointOfInterestService`, không phải một use case độc lập.
Các class được export qua `services/__init__.py`. Trong `routers/poi.py`,
`router` và `admin_router` giữ hai nhóm endpoint với quyền truy cập riêng.
Mọi endpoint danh sách có `offset/limit` trả cùng cấu trúc
`{"items": [], "total": 0, "offset": 0, "limit": 20}`; frontend không tự
đếm từ một trang dữ liệu.

## Các luồng nghiệp vụ quan trọng

### 1. Tạo POI mới

1. Web lấy Region và Category từ `GET /api/v1/admin/pois/options`.
2. Web gửi thông tin POI và `category_ids`; không gửi ID, QR, checksum hoặc trạng thái ACTIVE.
3. Router xác thực Bearer token và quyền `POI Management:create`.
4. Pydantic kiểm tra URL ảnh, tọa độ, bán kính và dữ liệu bắt buộc.
5. Backend tải ảnh ngoài transaction, chặn địa chỉ private/loopback và tính SHA-256 từ bytes thật.
6. Service mở transaction, kiểm tra Region/Category còn tồn tại và khóa phạm vi ghi cần thiết.
7. Backend sinh ID, deep-link QR, timestamp, người tạo và đặt trạng thái `INACTIVE`.
8. Repository thêm POI và category mapping; database kiểm tra FK/UNIQUE/CHECK.
9. Thành công thì commit và trả `201`; lỗi thì rollback toàn bộ.

### 2. Cập nhật POI

1. Router xác thực quyền `POI Management:update` và schema từ chối body rỗng.
2. Nếu URL ảnh được gửi, backend tải ảnh và tính checksum mới trước transaction.
3. Service khóa POI bằng `FOR UPDATE` để tránh hai request ghi đè nhau.
4. Backend kiểm tra Region/Category mới và chỉ thay các field có trong PATCH.
5. Nếu POI sẽ tiếp tục `ACTIVE`, backend kiểm tra lại content tiếng Anh và audio.
6. Category mapping chỉ bị thay khi request có `category_ids`; `[]` nghĩa là bỏ hết.
7. Backend cập nhật người sửa/thời gian sửa khi dữ liệu thực sự thay đổi rồi commit.

### 3. Đăng ký audio thu âm

1. File audio phải được upload tới một URL HTTP(S) công khai và bất biến trước.
2. Web gửi `audio_url` và `audio_source_type=RECORD` tới endpoint audio của content.
3. Router xác thực quyền `Narration Content Management:update`.
4. Backend tải audio ngoài transaction, chặn mạng private/loopback và redirect, giới hạn 100 MiB.
5. Backend kiểm tra MIME, đọc thời lượng, tính kích thước và SHA-256 từ bytes thật.
6. Service khóa POI và content; chỉ chấp nhận trạng thái content được phép gắn audio.
7. Repository tạo ContentAudio bằng metadata đã xác minh; client không quyết định checksum.
8. Nếu POI đang ACTIVE, service kiểm tra thay đổi không làm mất audio tiếng Anh khả dụng.

### 4. Tạo và quản lý phiên bản nội dung

1. Người soạn tạo content mới với POI, Language, tiêu đề và kịch bản đầy đủ.
2. Service khóa POI cha, kiểm tra Language đang SUPPORTED và cấp `content_version = max + 1`.
3. Content mới luôn ở `DRAFT`; backend tự sinh ID, người tạo và thời điểm tạo.
4. `DRAFT` hoặc `REJECTED` chưa có audio có thể PATCH trực tiếp; lưu REJECTED đưa về DRAFT.
5. Content đã có audio hoặc đã qua các trạng thái tiếp theo phải tạo phiên bản mới để chỉnh sửa.
6. Không xóa phiên bản cũ; `ARCHIVED` tiếp tục được giữ cho lịch sử và offline reference.

### 5. Submit và review nội dung

1. Tác giả submit `DRAFT/REJECTED`, content chuyển sang `WAITING_APPROVAL`.
2. Reviewer cần quyền `approve` và không được duyệt content do chính mình tạo.
3. Quyết định `APPROVE` chuyển content sang `APPROVED`, ghi người và thời điểm duyệt.
4. Quyết định `REJECT` chuyển content sang `REJECTED` và xóa metadata duyệt/xuất bản cũ.
5. Mọi bước khóa cùng POI/content để tránh submit, review và update chạy chồng nhau.

### 6. Publish và sinh TTS

1. Chỉ content `APPROVED` của Language đang SUPPORTED được publish.
2. Nếu đã có audio RECORD/TTS hợp lệ, backend bỏ qua bước sinh TTS.
3. Nếu chưa có audio, backend chụp snapshot nội dung rồi gọi gTTS ngoài transaction ghi.
4. MP3 được lưu theo checksum vào storage; URL asset không thay đổi theo tên content.
5. Service khóa lại POI/content và xác minh snapshot chưa bị sửa trong lúc tạo TTS.
6. Backend tạo ContentAudio nguồn `TTS`, archive bản PUBLISHED cũ cùng POI–Language.
7. Content mới chuyển sang `PUBLISHED`, ghi người/thời điểm publish rồi commit.
8. Nếu TTS hoặc storage lỗi, request trả lỗi và content vẫn giữ `APPROVED`.

### 7. Kích hoạt hoặc vô hiệu hóa POI

1. POI mới luôn `INACTIVE`; quản trị viên kích hoạt qua PATCH trạng thái.
2. Service khóa POI và tìm content tiếng Anh `PUBLISHED`.
3. Content tiếng Anh phải có audio hợp lệ với URL, MIME, size, duration và checksum.
4. Đủ điều kiện thì chuyển sang `ACTIVE`; thiếu điều kiện trả `409` và rollback.
5. Chuyển về `INACTIVE` không xóa POI, content, audio hoặc lịch sử nghe.

### 8. Lấy narration cho mobile

1. Mobile gọi `GET /api/v1/pois/{poi_id}/narration?language_code=<code>`.
2. Backend chỉ chấp nhận POI đang `ACTIVE`; POI ẩn được trả như không tồn tại.
3. Backend ưu tiên bản `PUBLISHED` có audio hợp lệ của ngôn ngữ yêu cầu.
4. Nếu không có, backend fallback sang tiếng Anh.
5. Response trả nội dung, version, metadata audio và cờ `is_fallback`; không trả dữ liệu quản trị.

### 9. Phân giải QR online cho mobile

1. Mobile gửi payload đã quét tới `POST /api/v1/pois/qr/resolve` cùng mã ngôn ngữ.
2. Backend chỉ chấp nhận định dạng `mnr://pois/poi-ddmmyy-xxxxxxxx`; QR khác hệ
   thống trả 422.
3. Backend chỉ trả POI đang `ACTIVE`; POI không tồn tại hoặc `INACTIVE` trả 404.
4. Backend chọn content `PUBLISHED` có audio hợp lệ theo ngôn ngữ yêu cầu và
   fallback tiếng Anh giống endpoint narration.
5. Response gộp dữ liệu POI công khai và narration sẵn sàng phát. Mobile, player
   và xử lý offline không thuộc endpoint này.

## Danh sách endpoint

Prefix: `/api/v1/admin/pois`.

| Method | Path | Quyền `POI Management` | Kết quả |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/pois` | read | 200, danh sách phân trang |
| GET | `/api/v1/admin/pois/options` | read | 200, region/category cho form |
| GET | `/api/v1/admin/pois/{id}` | read | 200, chi tiết |
| GET | `/api/v1/admin/pois/{id}/qr-code` | read | 200, ảnh QR PNG |
| POST | `/api/v1/admin/pois` | create | 201, POI vừa tạo |
| PATCH | `/api/v1/admin/pois/{id}` | update | 200, POI sau cập nhật |
| PATCH | `/api/v1/admin/pois/{id}/status` | update | 200, POI sau đổi trạng thái |

Endpoint public không yêu cầu Bearer token:

| Method | Path | Kết quả |
| --- | --- | --- |
| GET | `/api/v1/pois` | Danh sách POI ACTIVE |
| GET | `/api/v1/pois/{id}` | Chi tiết POI ACTIVE |
| GET | `/api/v1/pois/{id}/narration` | Narration PUBLISHED có audio hợp lệ |
| POST | `/api/v1/pois/qr/resolve` | POI ACTIVE và narration từ payload QR |

Body phân giải QR:

```json
{
  "qr_code": "mnr://pois/poi-111126-12345678",
  "language_code": "vi"
}
```

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
  "poi_image_url": "https://assets.example/poi/image.webp",
  "latitude": "10.776900",
  "longitude": "106.700900",
  "trigger_radius_meter": "50.00",
  "category_ids": ["<ID category thật từ options>"]
}
```

- Sinh ID `poi-ddmmyy-xxxxxxxx`, timestamp UTC và người thao tác ở backend.
- Backend tự gán `poi_qr_code = mnr://pois/{poi_id}`; client không gửi hoặc sửa
  trường này. Response quản trị trả `qr_code_url` để tải ảnh PNG tại
  `GET /api/v1/admin/pois/{poi_id}/qr-code`. Ảnh được render bằng thư viện
  Python `qrcode` với Pillow và yêu cầu quyền đọc POI.
- POI mới luôn INACTIVE. Gửi `poi_status=ACTIVE` khi tạo sẽ nhận 422.
- Region/category phải tồn tại, category không được trùng, tối đa 100 ID.
- Payload QR/địa chỉ duy nhất; vĩ độ `[-90,90]`, kinh độ `[-180,180]`, bán kính > 0.
- Tọa độ tối đa 6 chữ số thập phân; bán kính tối đa 2, phù hợp cột NUMERIC.
- Ảnh bắt buộc là URL HTTP(S) không chứa thông tin đăng nhập, tối đa 1000 ký tự.
  Backend tải tối đa 10 MiB từ địa chỉ mạng công khai, yêu cầu MIME `image/*`
  và tự tính `image_checksum_sha256`; client không gửi checksum. URL redirect,
  mạng private/loopback, response rỗng hoặc không phải ảnh đều bị từ chối.
- Field không khai báo bị từ chối; không nhận `created_by`, timestamp hoặc ID từ web.

### Sửa và đổi trạng thái

PATCH chỉ cập nhật field được gửi và không chấp nhận body rỗng. Client không gửi
checksum ảnh. Không gửi `category_ids` thì giữ mapping; gửi `[]` thì bỏ hết.
Khi gửi URL ảnh trong PATCH, backend tải lại ảnh và tự cập nhật checksum mới.

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

### Vô hiệu hóa và lỗi

Phiên bản hiện tại không cung cấp endpoint hard delete POI. Khi một địa điểm
không còn được sử dụng, quản trị viên đổi trạng thái sang `INACTIVE` để giữ lịch
sử nghe, nội dung thuyết minh và dữ liệu offline liên quan.

| HTTP | Ý nghĩa |
| --- | --- |
| 401 | Token/session không hợp lệ, theo Identity hiện có |
| 403 | Thiếu permission tương ứng |
| 404 | Không có POI, region hoặc category được tham chiếu |
| 409 | QR/địa chỉ trùng hoặc không đủ điều kiện active |
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

Revision `0007_poi_schema_alignment` bổ sung các constraint/index POI ban đầu;
revision `0009_poi_contract` chuẩn hóa trạng thái thành `ACTIVE`/`INACTIVE`, nguồn
audio thành `RECORD`/`TTS`, siết ảnh và người cập nhật POI thành NOT NULL, đồng thời
thêm CHECK MIME. Migration tự điền `last_updated_by` từ `created_by`, nhưng sẽ dừng
nếu POI cũ thiếu URL ảnh thật hoặc audio có MIME không được hỗ trợ. Phải bổ sung dữ
liệu hợp lệ rồi chạy lại; migration không tự tạo URL giả hoặc xóa bản ghi.

Checksum audio dùng để kiểm tra toàn vẹn và tái sử dụng asset, không phải khóa định
danh nên có thể trùng giữa nhiều content. Quan hệ một audio cho mỗi content vẫn
được bảo đảm bởi UNIQUE `poi_content_id`. URL và checksum của một audio đã lưu là
bất biến; thay asset cần một quy trình upload/import có xác minh riêng thay vì sửa
URL trong màn hình metadata.

## Phần phối hợp sau này

- API chưa upload ảnh/audio trực tiếp; asset phải tồn tại tại URL công khai trước.
  Backend đã tải và xác minh bytes/checksum khi đăng ký asset.
- `can_activate` kiểm tra metadata audio đã xác minh lúc đăng ký, nhưng không tải
  lại file từ storage trong mỗi lần kích hoạt.
- Rebuild Offline Package khi metadata/category thay đổi cần tích hợp với domain
  Offline. API hiện chưa đánh dấu/tạo job rebuild hay tăng `package_version`.
- Chưa tự ghi AuditLog. API content/audio được mô tả ở phần bên dưới.
- Web đã gọi API quản trị; CORS và cấu hình triển khai vẫn phụ thuộc môi trường.

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
| PATCH | `/{id}` | update | Chỉ sửa DRAFT/REJECTED |
| POST | `/{id}/submit` | update | DRAFT/REJECTED → WAITING_APPROVAL |
| POST | `/{id}/review` | approve | APPROVE hoặc REJECT content đang WAITING_APPROVAL |
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
giá trị tương thích `active` của seed. Mỗi request tạo mới phải gửi đầy đủ tiêu đề
và nội dung; backend không sao chép dữ liệu từ content cũ. Version được cấp
`max + 1` trong phạm vi POI–Language dưới khóa POI, chống hai request trùng version.

Không cung cấp endpoint xóa content. Với WAITING_APPROVAL/APPROVED/PUBLISHED/
ARCHIVED, cần tạo phiên bản mới khi chỉnh sửa. DRAFT/REJECTED chỉ được sửa trực
tiếp khi chưa có audio; nếu đã có audio thì cũng phải tạo phiên bản mới để giữ
nguyên metadata và lịch sử. Lưu REJECTED đưa về DRAFT; có thể gửi lại trực tiếp
từ REJECTED. Trường duyệt/xuất bản cũ được xóa khi gửi lại. Endpoint review nhận
`{"decision":"APPROVE"}` hoặc `{"decision":"REJECT"}`; tác giả không được tự
review content của mình.
Reject chưa nhận ghi chú vì schema hiện không lưu lý do; việc lưu reviewer/lý do
từ chối chi tiết chờ thiết kế Audit, không nhận rồi bỏ dữ liệu.

Publish ưu tiên audio RECORD/TTS hợp lệ đã có. Nếu content chưa có audio hợp lệ,
backend dùng gTTS tạo MP3 từ tiêu đề và script, lưu file bất biến theo checksum,
tạo/cập nhật ContentAudio nguồn TTS rồi mới publish. Lời gọi TTS chạy ngoài
transaction ghi; trước khi lưu, backend khóa content và xác minh nội dung chưa bị
thay đổi. TTS/storage lỗi trả 503 và content vẫn APPROVED. Khi thành công, archive
bản cũ cùng POI–Language và publish bản mới. Không publish bản thấp hơn version
đang phân phối. ARCHIVED giữ nội dung/audio cho tham chiếu lịch sử.

## API metadata audio

Quyền cũng thuộc `Narration Content Management`:

| Method | Endpoint | Quyền |
| --- | --- | --- |
| GET | `/api/v1/admin/audios` | read |
| GET | `/api/v1/admin/audios/{audio_id}` | read |
| GET | `/api/v1/admin/poi-contents/{id}/audio` | read |
| PUT | `/api/v1/admin/poi-contents/{id}/audio` | update |

Danh sách có cùng phân trang; filter `poi_id`, `language_id`, `poi_content_id`,
`audio_source_type=RECORD|TTS`, `search` theo ID/tiêu đề content. PUT trả 200 khi
đăng ký asset đã được backend xác minh; mỗi content có tối đa một audio:

```json
{
  "audio_url": "https://assets.example/audio/recording.mp3",
  "audio_source_type": "RECORD"
}
```

Backend chặn URL private/loopback và redirect, tải tối đa 100 MiB, kiểm tra MIME,
đọc thời lượng và tự tính kích thước/checksum SHA-256 từ bytes thực tế trước khi
mở transaction ghi. MIME hỗ trợ: audio/mpeg, audio/aac, audio/ogg, audio/wav,
audio/mp4, audio/webm. Audio sinh tự động được phục vụ tại
`/api/v1/assets/audio/{checksum}.mp3`.

Cho phép gắn/thay metadata khi DRAFT/REJECTED/APPROVED/PUBLISHED; đóng băng khi
WAITING_APPROVAL và ARCHIVED. Thay audio PUBLISHED là đổi metadata nguyên tử sang
asset mới hợp lệ, giữ ID bản ghi audio. Checksum đổi bắt buộc URL mới. Không cung
cấp endpoint xóa audio; metadata cũ được giữ để bảo toàn lịch sử và tham chiếu
offline. Các thao tác không làm POI ACTIVE mất audio tiếng Anh khả dụng. Không tự
thay package hoặc xóa file storage. Hai content có thể đăng ký cùng checksum khi
cùng tham chiếu một asset vật lý; checksum không thay thế ID của bản ghi audio.

## Chọn thuyết minh online và fallback

```http
GET /api/v1/pois/{poi_id}/narration?language_code=vi
```

Endpoint public chỉ phục vụ POI `ACTIVE`. Chọn PUBLISHED của ngôn ngữ yêu cầu
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
| Storage/upload | Đã đọc/xác minh audio từ URL; chưa có endpoint upload hoặc dọn asset |
| TTS | Đang dùng gTTS đồng bộ; production nên thay bằng provider có SLA/job retry |
| Offline | Chưa đánh dấu/rebuild package khi dữ liệu đổi, không tăng package_version |
| Audit | Chưa ghi sự kiện, reviewer/lý do từ chối hoặc lịch sử thao tác |
| Frontend | Đã gọi API; form audio cần gửi contract rút gọn URL + source |

Khi nối các phần này, dùng service collaborator rõ ràng và giữ transaction/khóa
POI; không dùng endpoint giả thành công hoặc bỏ kiểm tra quyền thay cho tích hợp.
