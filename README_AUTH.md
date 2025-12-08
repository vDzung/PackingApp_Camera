# Hướng Dẫn Đăng Nhập - PackingApp

## 📋 Tổng Quan

PackingApp yêu cầu đăng nhập với:
1. **Tài khoản/Mật khẩu** - Đã đăng ký từ Web App
2. **Key xác thực** - Key được cấp từ Web App

## 🚀 Cài Đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình Web App URL
Mặc định app sẽ kết nối đến `http://localhost:3000`

Để thay đổi, set environment variable:
```bash
# Windows
set WEB_APP_URL=http://your-web-app-url:3000

# Linux/Mac
export WEB_APP_URL=http://your-web-app-url:3000
```

Hoặc sửa trong file `auth.py`:
```python
API_BASE_URL = 'http://your-web-app-url:3000'
```

## 🔐 Đăng Nhập

### Bước 1: Chạy ứng dụng
```bash
python -m PackingApp.main_app
```

### Bước 2: Nhập thông tin đăng nhập
1. **Email hoặc Số điện thoại**: Nhập email hoặc số điện thoại đã đăng ký trên Web App
2. **Mật khẩu**: Nhập mật khẩu tài khoản
3. **Key xác thực**: Nhập key được cấp từ Web App (format: `KEY_...`)

### Bước 3: Nhấn "ĐĂNG NHẬP"
- App sẽ kiểm tra tài khoản/mật khẩu với Web App
- Sau đó xác thực key
- Nếu thành công, app chính sẽ được mở

## 💾 Session Management

- Session được lưu trong file `.session.json` trong thư mục PackingApp
- Session bao gồm:
  - Thông tin đăng nhập (email/phone)
  - Key xác thực
  - Thời gian hết hạn key
  - Thời gian đăng nhập

### Tự động đăng nhập lại
- Nếu session còn hợp lệ (key chưa hết hạn), app sẽ tự động điền email và key
- Bạn chỉ cần nhập mật khẩu và đăng nhập lại

## ⚠️ Xử Lý Lỗi

### Lỗi kết nối
- Kiểm tra Web App đã chạy chưa
- Kiểm tra URL trong `auth.py` hoặc environment variable
- Kiểm tra firewall/network

### Lỗi đăng nhập
- Kiểm tra email/phone và mật khẩu đúng chưa
- Kiểm tra tài khoản đã được đăng ký trên Web App chưa

### Lỗi key
- Kiểm tra key đúng format chưa (bắt đầu bằng `KEY_`)
- Kiểm tra key còn hạn chưa
- Kiểm tra key đã được kích hoạt trên Web App chưa

## 🔄 Quy Trình Đăng Nhập

```
1. User nhập email/phone + password + key
   ↓
2. App gửi request đến /api/auth/login
   ↓
3. Web App xác thực tài khoản/mật khẩu
   ↓
4. App gửi request đến /api/auth/verify-key
   ↓
5. Web App xác thực key
   ↓
6. Lưu session vào .session.json
   ↓
7. Mở app chính
```

## 📝 API Endpoints Sử Dụng

### POST /api/auth/login
```json
{
  "email_or_phone": "user@example.com",
  "password": "password123"
}
```

Response:
```json
{
  "success": true,
  "message": "Đăng nhập thành công!",
  "userId": 1,
  "isAdmin": false
}
```

### POST /api/auth/verify-key
```json
{
  "key": "KEY_ABC123..."
}
```

Response:
```json
{
  "success": true,
  "phone": "0123456789",
  "expires_at": "2024-12-31T23:59:59.000Z"
}
```

## 🛠️ Troubleshooting

### App không kết nối được Web App
1. Kiểm tra Web App đang chạy: `http://localhost:3000`
2. Kiểm tra `API_BASE_URL` trong `auth.py`
3. Kiểm tra firewall/antivirus

### Session không được lưu
1. Kiểm tra quyền ghi file trong thư mục PackingApp
2. Kiểm tra file `.session.json` có bị lock không

### Key hết hạn
- Liên hệ admin để gia hạn key trên Web App
- Đăng nhập lại sau khi key được gia hạn

## 📞 Hỗ Trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra log trong console
2. Kiểm tra file `.session.json`
3. Liên hệ admin Web App

