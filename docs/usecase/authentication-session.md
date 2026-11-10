# UC-IDENTITY-01 — Đăng nhập, sử dụng phiên và đăng xuất hệ thống quản trị

| Use case number: | UC-IDENTITY-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Đăng nhập, sử dụng phiên và đăng xuất hệ thống quản trị |  |
| **Actor(s):** | Người dùng quản trị (Management User), Admin Web |  |
| **Maturity:** | Specified — đặc tả nghiệp vụ trước khi triển khai giao diện quản trị |  |
| **Summary:** | Người dùng quản trị nhập thông tin đăng nhập để truy cập các chức năng được phân quyền. Hệ thống kiểm tra tài khoản, quản lý hiệu lực phiên, kiểm tra quyền trước mỗi thao tác và kết thúc phiên khi người dùng đăng xuất. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Người dùng quản trị truy cập trang quản trị. |  |
|  |  | 2\. Hệ thống hiển thị biểu mẫu đăng nhập với trường **Email**, **Mật khẩu** và nút **Đăng nhập**. |
|  | 3\. Người dùng nhập email, mật khẩu và chọn **Đăng nhập**. |  |
|  |  | 4\. Hệ thống kiểm tra dữ liệu bắt buộc và định dạng thông tin đăng nhập. **E1** |
|  |  | 5\. Hệ thống kiểm tra thông tin tài khoản và đối chiếu mật khẩu. **E2** |
|  |  | 6\. Hệ thống kiểm tra tài khoản đang được phép sử dụng hệ thống quản trị. **E2** |
|  |  | 7\. Hệ thống tạo và lưu phiên đăng nhập có thời hạn, gắn với tài khoản đã xác thực. **E3** |
|  |  | 8\. Hệ thống cấp thông tin truy cập cho phiên đăng nhập. **E4** |
|  |  | 9\. Hệ thống hiển thị thông báo “Đăng nhập thành công.” và chuyển người dùng đến trang quản trị phù hợp với vai trò. |
|  | 10\. Người dùng chọn một chức năng quản trị trong hệ thống. **A2** |  |
|  |  | 11\. Hệ thống xác minh phiên còn hiệu lực, kiểm tra vai trò và quyền hiện tại trước khi thực hiện chức năng được chọn. **A1, A3, E5, E6** |
|  | 12\. Người dùng chọn **Đăng xuất**. |  |
|  |  | 13\. Hệ thống thu hồi phiên đăng nhập, xóa thông tin truy cập trên trình duyệt, hiển thị “Đăng xuất thành công.” và đưa người dùng về màn hình đăng nhập. **E7** |
| **Alternative Paths:** | **A1 — Gia hạn phiên đăng nhập:** Tại bước 11, nếu phiên truy cập cần được gia hạn nhưng phiên đăng nhập tổng thể vẫn hợp lệ, hệ thống thực hiện gia hạn thông tin truy cập mà không kéo dài thời hạn tối đa của phiên. Nếu thành công, quay lại bước 11 để kiểm tra quyền và tiếp tục thao tác; nếu thất bại do phiên không còn hợp lệ, chuyển sang E5 và kết thúc luồng.<br><br>**A2 — Đóng trình duyệt:** Tại bước 10, nếu người dùng đóng trình duyệt thay vì chọn Đăng xuất, hệ thống không tự coi phiên là đã được thu hồi. Khi người dùng truy cập lại, hệ thống kiểm tra hiệu lực phiên trước khi cho phép thao tác. Kết thúc lượt tương tác hiện tại.<br><br>**A3 — Quyền hoặc vai trò thay đổi:** Tại bước 11, nếu vai trò hoặc quyền của tài khoản đã thay đổi, hệ thống kiểm tra lại quyền hiện tại, không sử dụng quyền cũ để xử lý thao tác. Nếu phiên vẫn hợp lệ và còn quyền, quay lại bước 10 để người dùng chọn thao tác phù hợp; nếu không đủ quyền, chuyển sang E6; nếu cần xác thực lại, chuyển sang E5 và kết thúc luồng. |  |
| **Exception Paths:** | **E1 — Thông tin đăng nhập không hợp lệ:** Tại bước 4, nếu bỏ trống email hoặc mật khẩu, hệ thống hiển thị “Vui lòng nhập email và mật khẩu.”; nếu email sai định dạng, hiển thị “Email không đúng định dạng.”; nếu mật khẩu vi phạm quy tắc nhập liệu, hiển thị “Mật khẩu không hợp lệ.”. Không gửi yêu cầu xác thực. Quay lại bước 3 để người dùng chỉnh sửa.<br><br>**E2 — Đăng nhập thất bại:** Tại bước 5 hoặc bước 6, nếu email không tồn tại, mật khẩu không đúng hoặc tài khoản không được phép đăng nhập, hệ thống không tiết lộ nguyên nhân cụ thể và hiển thị “Email hoặc mật khẩu không chính xác, hoặc tài khoản không khả dụng.”. Không tạo phiên đăng nhập. Quay lại bước 3 để người dùng thử lại.<br><br>**E3 — Không thể tạo phiên đăng nhập:** Tại bước 7, nếu hệ thống không thể lưu phiên đăng nhập, hệ thống hủy thao tác tạo phiên, không cấp thông tin truy cập và hiển thị “Không thể đăng nhập lúc này. Vui lòng thử lại sau.”. Quay lại bước 2.<br><br>**E4 — Dịch vụ xác thực tạm thời không khả dụng:** Tại bước 8, nếu hệ thống không thể hoàn tất việc cấp thông tin xác thực, hệ thống không cho phép truy cập trang quản trị và hiển thị “Hệ thống đăng nhập tạm thời không khả dụng. Vui lòng thử lại sau.”. Quay lại bước 2.<br><br>**E5 — Phiên đăng nhập không hợp lệ hoặc hết hạn:** Tại bước 11, nếu thông tin xác thực sai, phiên không tồn tại, hết hạn, đã bị thu hồi hoặc không thể gia hạn, hệ thống từ chối thao tác đang yêu cầu, xóa thông tin truy cập cục bộ và hiển thị “Phiên đăng nhập đã hết hạn hoặc không còn hợp lệ. Vui lòng đăng nhập lại.”. Quay lại bước 2; luồng sử dụng phiên hiện tại kết thúc.<br><br>**E6 — Không đủ quyền thực hiện thao tác:** Tại bước 11, nếu phiên hợp lệ nhưng người dùng không có quyền thực hiện chức năng đã chọn, hệ thống không thực hiện thao tác và hiển thị “Bạn không có quyền thực hiện thao tác này.”. Phiên đăng nhập vẫn được giữ. Quay lại bước 10 để người dùng chọn chức năng khác.<br><br>**E7 — Không thể xác nhận thu hồi phiên khi đăng xuất:** Tại bước 13, nếu hệ thống không thể xác nhận việc thu hồi phiên trên máy chủ, Admin Web vẫn xóa thông tin truy cập cục bộ, đưa người dùng về màn hình đăng nhập và hiển thị “Đã thoát khỏi thiết bị này, nhưng chưa thể xác nhận đăng xuất trên hệ thống.”. Không thông báo rằng phiên máy chủ đã được thu hồi thành công. Kết thúc luồng. |  |
| **Extension Points:** | Có thể mở rộng xác thực đa yếu tố (MFA), giới hạn số lần đăng nhập sai, đăng xuất trên tất cả thiết bị hoặc cảnh báo đăng nhập bất thường theo yêu cầu trong tương lai. |  |
| **Triggers:** | Người dùng quản trị muốn đăng nhập, truy cập chức năng được bảo vệ hoặc kết thúc phiên đăng nhập. |  |
| **Assumptions:** | Hệ thống có khả năng truy cập dữ liệu tài khoản, vai trò, quyền và lưu trữ phiên; các thành phần xác thực hoạt động an toàn; người dùng có kết nối đến hệ thống quản trị. |  |
| **Preconditions:** | Hệ thống quản trị có dữ liệu người dùng và phân quyền tương ứng; người dùng có thể truy cập trang đăng nhập. Trạng thái tài khoản được kiểm tra tại bước 6, không mặc định mọi tài khoản đều đang hoạt động. |  |
| **Post Conditions:** | **Thành công:** Người dùng đăng nhập có phiên hợp lệ và chỉ sử dụng được chức năng được phân quyền; đăng xuất thành công thì phiên bị thu hồi và trình duyệt xóa thông tin truy cập. **Thất bại:** Không tạo phiên khi đăng nhập thất bại, không thực hiện thao tác khi không đủ quyền; nếu thu hồi phiên lỗi, chỉ xác nhận đã xóa thông tin trên thiết bị. |  |
| **Preferences:** | Không hiển thị hay ghi log mật khẩu và thông tin xác thực bí mật; thông báo đăng nhập thất bại không tiết lộ email có tồn tại hay trạng thái tài khoản; việc kiểm tra quyền phải diễn ra tại hệ thống, không chỉ dựa vào việc ẩn chức năng trên giao diện. |  |
| **Author(s):** | MNR Backend Team |  |
| **Date:** | 10-11-2026 |  |

## Quy ước thông báo và phạm vi tài liệu

Các thông báo được đặt trong dấu ngoặc kép là **nội dung giao diện đề xuất trong đặc tả nghiệp vụ**; không được xem là xác nhận rằng giao diện hiện tại đã triển khai đúng từng câu chữ.

Use Case này mô tả **hành vi tương tác giữa người dùng và hệ thống**, không quy định đường dẫn API, phương thức HTTP, mã lỗi HTTP, cấu trúc token, thuật toán băm hay cấu hình máy chủ. Những chi tiết triển khai được quản lý trong tài liệu kỹ thuật riêng.
