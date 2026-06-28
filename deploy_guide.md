# CẨM NANG HƯỚNG DẪN ĐƯA WEB APP LÊN INTERNET

Tài liệu này hướng dẫn chi tiết các bước đưa **Hệ thống Kiểm soát Khép kín Vòng đời Gói thầu Thi công** lên mạng Internet hoàn toàn miễn phí, bảo mật SSL (HTTPS) để truy cập từ xa qua điện thoại hoặc máy tính khác.

---

## 🚀 PHƯƠNG ÁN 1: NETLIFY DROP (Khuyên dùng - Nhanh nhất & Dễ nhất)
*Không cần cài đặt Git, Nodejs hay viết bất kỳ dòng lệnh nào. Phù hợp nhất cho người dùng văn phòng.*

### Các bước thực hiện:
1.  **Chuẩn bị thư mục**: Mở thư mục dự án của bạn: `d:\AI Thực chiến\Phòng kinh tế kế hoạch\Kế hoạch VSV\he_thong_quan_ly` trên máy tính.
2.  **Truy cập Netlify Drop**: Dùng trình duyệt (Chrome, Edge) truy cập vào trang: **[https://app.netlify.com/drop](https://app.netlify.com/drop)**.
3.  **Kéo thả thư mục**: Kéo thư mục `he_thong_quan_ly` thả trực tiếp vào vùng nét đứt màu xanh lá trên giao diện Netlify Drop (nơi ghi chữ *Drag and drop your site folder here*).
4.  **Nhận link Web**: Hệ thống sẽ tải lên và khởi tạo trang web của bạn chỉ sau 5 giây. Bạn sẽ nhận được một đường dẫn công khai chạy trực tuyến có dạng: `https://[ten-ngau-nhien].netlify.app`.
5.  **Cấu hình tên miền (Tùy chọn)**:
    *   Bấm **Sign up** để đăng ký tài khoản Netlify miễn phí (để quản lý trang web này).
    *   Sau khi đăng nhập, chọn **Site configuration** -> **Domain management** -> **Change site name** để đổi tên miền tùy chỉnh theo ý bạn (Ví dụ: `https://vsv-tender-system.netlify.app`).

---

## 🐙 PHƯƠNG ÁN 2: GITHUB PAGES (Bền vững & Quản lý phiên bản)
*Lưu trữ vĩnh viễn và tự động đồng bộ mã nguồn của bạn.*

### Các bước thực hiện:
1.  **Tạo tài khoản & Kho chứa (Repository)**:
    *   Truy cập **[https://github.com](https://github.com)** và đăng ký tài khoản (nếu chưa có).
    *   Bấm **New** để tạo một Repository mới. Đặt tên kho chứa (Ví dụ: `vsv-tender-system`). Chọn chế độ **Public** (công khai).
2.  **Tải mã nguồn lên GitHub**:
    *   Tại giao diện Repository mới tạo, bấm vào dòng **uploading an existing file**.
    *   Chọn toàn bộ các tệp tin trong thư mục `he_thong_quan_ly` (bao gồm: `index.html`, `styles.css`, `app.js`, `data_mock.js`) kéo thả vào trình duyệt.
    *   Bấm **Commit changes** ở cuối trang để xác nhận tải lên.
3.  **Kích hoạt GitHub Pages**:
    *   Vào mục **Settings** (Cấu hình) ở thanh menu trên cùng của Repository của bạn.
    *   Tại menu bên trái, tìm và nhấp chọn mục **Pages**.
    *   Tại phần **Build and deployment** -> **Branch**, nhấp vào dropdown đang ghi là *None*, đổi sang nhánh **main** (hoặc `master`), giữ nguyên thư mục gốc `/ (root)`, sau đó bấm **Save**.
4.  **Hoàn thành**: Đợi khoảng 1-2 phút, GitHub sẽ cấp cho bạn một đường dẫn chạy trực tuyến ở phía trên cùng của trang Settings này, có dạng: `https://[ten-tai-khoan].github.io/[ten-repository]`.

---

## ⚡ PHƯƠNG ÁN 3: VERCEL (Tốc độ tối ưu & Tích hợp liên tục - CI/CD)
*Tự động deploy lại ứng dụng mỗi khi bạn cập nhật code trên GitHub.*

### Các bước thực hiện:
1.  **Đưa mã nguồn lên GitHub** như các bước ở **Phương án 2**.
2.  **Đăng nhập Vercel**: Truy cập **[https://vercel.com](https://vercel.com)** và đăng nhập bằng tài khoản GitHub của bạn.
3.  **Import dự án**:
    *   Tại Dashboard của Vercel, bấm nút **Add New** -> **Project**.
    *   Vercel sẽ tự động hiển thị danh sách các Repository trên GitHub của bạn. Nhấp nút **Import** bên cạnh dự án `vsv-tender-system`.
4.  **Triển khai**:
    *   Giữ nguyên toàn bộ cấu hình mặc định (Vercel tự nhận diện đây là ứng dụng HTML/CSS/JS tĩnh).
    *   Bấm nút **Deploy**.
    *   Chờ khoảng 30 giây để hệ thống biên dịch và cấp đường dẫn vĩnh viễn (Ví dụ: `https://vsv-tender-system.vercel.app`).

---

## 🔒 AN TOÀN VÀ BẢO MẬT DỮ LIỆU
*   **Bảo mật API Key**: Toàn bộ API Key Gemini mà bạn nhập và lưu trên Web App được lưu trữ trực tiếp trong bộ nhớ `localStorage` của trình duyệt của bạn. **Nó không bao giờ được gửi đi bất cứ đâu** ngoại trừ gọi trực tiếp qua giao thức bảo mật SSL đến máy chủ REST API của Google (`https://generativelanguage.googleapis.com`). Bạn hoàn toàn có thể yên tâm khi chia sẻ trang web cho người khác sử dụng với API Key riêng của họ.
*   **Bảo mật Dữ liệu**: Dữ liệu công trình do bạn nhập thủ công, Import Excel hay bóc tách từ AI đều được lưu trữ **cục bộ 100%** trên trình duyệt của thiết bị đang mở. Người khác khi truy cập vào đường dẫn web sẽ thấy dữ liệu mẫu ban đầu, họ chỉ thấy dữ liệu của bạn nếu bạn dùng tính năng **Export JSON/Excel** gửi tệp tin cho họ tải lên máy của họ.
