

| Use case number: | UC-01 |  |
| :---- | :---- | :---- |
| **Use case name:** | Xác thực và tra quyền lợi bảo hiểm (Eligibility) |  |
| **Actor(s):** | Dược sĩ (Pharmacist), Hệ thống bảo hiểm (Payer System) |  |
| **Maturity:** | Focused |  |
| **Summary:** | Dược sĩ kiểm tra hiệu lực và quyền lợi bảo hiểm bao gồm kết quả tính hợp lệ, phạm vi bảo hiểm và hạn mức của bệnh nhân. |  |
| **Basic Course of Events:** | **Actor action** | **System response** |
|  | 1\. Dược sĩ chọn chức năng kiểm tra quyền lợi bảo hiểm.  |  |
|  |  | 2\. Hệ thống bệnh viện hiện biểu mẫu nhập gồm thông tin của bệnh nhân (patient), tổ chức bảo hiểm (payer) và gói bảo hiểm (plan).  |
|  | 3\. Dược sĩ nhập thông tin bệnh nhân (ptient), tổ chức bảo hiểm (payer) và gói bảo hiểm (plan) và nhấn kiểm tra. |  |
|  |  | 4\. Hệ thống bệnh viện thực hiện xác thực dữ liệu trên biểu mẫu. **E1** |
|  |  | 5\. Hệ thống bệnh viện gửi yêu cầu kiểm tra quyền lợi bảo hiểm đến hệ thống cảu tổ chức bảo hiểm (Payer System). **A1, E2** |
|  |  | 6\. Hệ thống bệnh viện ghi nhận kết quả và và hiển thị kết quả về tính hợp lệ, phạm vi bảo hiểm, và hạn mức bảo hiểm. |
|  | 7\. Dược sĩ xem và xác nhận hiệu lực và quyền lợi bảo hiểm của bệnh nhân. |  |
| **Alternative Paths:** | **A1**. Tại bước 5, nếu có kết quả kiểm tra gần nhất hệ thống có thể sử dụng kết quả kiểm tra gần nhất. Đến bước 6 |  |
| **Exception Paths:** | **E1**. Tại bước 4, nếu thông tin đầu vào không hợp lệ (thiếu thông tin hoặc thông tin sai định dạng) hệ thống hiên thị thông báo lỗi và Dược sĩ có thể chỉnh sửa thông tin. Quy trình quay lại bước 3\.  **E2**. Tại bước 5, nếu hệ thống không thể kết nối đến hệ thống cảu tổ chức bảo hiểm, hệ thống hiển thị thông báo không thể kiểm tra quyền lợi tại thời điểm này. Quy trình quay lại bước 3\. |  |
| **Extension Points:** | … |  |
| **Triggers:** | Dược sĩ cần xác minh quyền lợi bảo hiểm của bệnh nhân trước khi tiến hành xử lý đơn thuốc. |  |
| **Assumptions:** | Hệ thống có khả năng kết nối với cơ sở dữ liệu bảo hiểm của tổ chức bảo hiểm. |  |
| **Preconditions:** | Dược sĩ đã thu thập được thông tin cảu bệnh nhân (patient), tổ chức bảo hiểm (payer) và gói bảo hiểm (plan). |  |
| **Post Conditions:** | Bảng ELIGIBILITY\_CHECK ghi nhận thông tin quyền lợi của bệnh nhân. |  |
| **Preferences:** | … |  |
| **Author(s):** | Phạm Đình Duy Thái  |  |
| **Date:** | 21-10-2026 |  |
