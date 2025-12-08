# Hướng Dẫn Kết Nối Python App với Web App

## 📋 Tổng Quan

Python App (`PackingApp`) có thể kết nối với Web App (Next.js) để:
- Đăng nhập với tài khoản đã đăng ký trên Web App
- Xác thực key license từ Web App
- Đồng bộ thông tin user và license

## 🔧 Cấu Hình

### 1. Tắt Offline Mode

Mở file `PackingApp/config.py` và sửa:

```python
# Tắt offline mode để kết nối với Web App
OFFLINE_MODE = False
```

Hoặc set environment variable:
```bash
# Windows PowerShell
$env:OFFLINE_MODE="false"

# Windows CMD
set OFFLINE_MODE=false

# Linux/Mac
export OFFLINE_MODE=false
```

### 2. Cấu Hình URL Web App

Mặc định Web App chạy ở `http://localhost:3000`. Nếu Web App chạy ở port khác, sửa trong `config.py`:

```python
WEB_APP_URL = 'http://localhost:3000'  # Thay đổi port nếu cần
```

Hoặc set environment variable:
```bash
$env:WEB_APP_URL="http://localhost:3000"
```

## 🚀 Chạy Web App

Trước khi chạy Python App, đảm bảo Web App đang chạy:

```bash
cd Web_PackingApp
npm run dev
```

Web App sẽ chạy ở `http://localhost:3000`

## 📡 API Endpoints

Python App kết nối với các API sau:

### 1. Đăng Nhập
- **Endpoint:** `POST /api/auth/login`
- **Request:**
  ```json
  {
    "email_or_phone": "user@example.com",
    "password": "password123"
  }
  ```
- **Response (Success):**
  ```json
  {
    "success": true,
    "data": {
      "message": "Đăng nhập thành công!",
      "isAdmin": false,
      "userId": 1
    }
  }
  ```
- **Response (Error):**
  ```json
  {
    "success": false,
    "error": "Email/Số điện thoại hoặc mật khẩu không đúng"
  }
  ```

### 2. Xác Thực Key
- **Endpoint:** `POST /api/auth/verify-key`
- **Request:**
  ```json
  {
    "key": "KEY_ABC123..."
  }
  ```
- **Response (Success):**
  ```json
  {
    "success": true,
    "phone": "0123456789",
    "expires_at": "2025-12-31T23:59:59.000Z"
  }
  ```
- **Response (Error):**
  ```json
  {
    "success": false,
    "error": "Key không hợp lệ"
  }
  ```

## 🔄 Flow Kết Nối

### Lần Đầu Sử Dụng (User):
```
1. User mở Python App
2. Nhập email/phone + password (đã đăng ký trên Web App)
3. Đăng nhập thành công → Lưu session
4. Hệ thống kiểm tra license → Chưa kích hoạt
5. Hiển thị Activate Window
6. User nhập key (được tạo từ Web App Admin)
7. Xác thực key thành công → Lưu thông tin license
8. Vào app
```

### Lần Sau (User đã kích hoạt):
```
1. User mở Python App
2. Nhập email/phone + password
3. Đăng nhập thành công
4. Hệ thống kiểm tra license → Đã kích hoạt + còn hạn
5. Vào app ngay (không cần nhập key)
```

### Admin:
```
1. Admin mở Python App
2. Nhập email/phone + password
3. Đăng nhập thành công
4. Hệ thống kiểm tra → Admin (không cần license)
5. Vào app ngay
```

## 🛠️ Troubleshooting

### Lỗi: "Lỗi kết nối đến server"
- **Nguyên nhân:** Web App không chạy hoặc URL sai
- **Giải pháp:**
  1. Kiểm tra Web App đang chạy: `http://localhost:3000`
  2. Kiểm tra `WEB_APP_URL` trong `config.py`
  3. Kiểm tra firewall/antivirus không chặn kết nối

### Lỗi: "Email/Số điện thoại hoặc mật khẩu không đúng"
- **Nguyên nhân:** Tài khoản chưa đăng ký trên Web App
- **Giải pháp:**
  1. Đăng ký tài khoản trên Web App: `http://localhost:3000`
  2. Hoặc dùng tài khoản admin mặc định (nếu có)

### Lỗi: "Key không hợp lệ"
- **Nguyên nhân:** Key chưa được tạo trên Web App hoặc đã hết hạn
- **Giải pháp:**
  1. Admin tạo key trên Web App: `/admin/dashboard`
  2. Kiểm tra key còn hạn không
  3. Đảm bảo key chưa bị đình chỉ

### Fallback Offline Mode
Nếu không kết nối được Web App, Python App sẽ tự động chuyển sang offline mode (nếu tài khoản khớp với admin mặc định).

## 📝 Notes

- Session được lưu trong file `.session.json` trong thư mục `PackingApp`
- Key chỉ cần kích hoạt 1 lần, sau đó không cần nhập lại
- Admin không cần key để đăng nhập
- Tất cả API calls đều có timeout 10 giây
- Nếu server không khả dụng, app sẽ fallback về offline mode (nếu có tài khoản admin mặc định)

## 🔐 Bảo Mật

- Password không được lưu trong session
- Key được lưu local nhưng không gửi lên server (chỉ verify)
- Session file (`.session.json`) nên được bảo vệ (không commit vào git)

