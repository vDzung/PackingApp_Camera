# Hướng Dẫn Đăng Nhập - PackingApp

## 🎯 Tổng Quan

Giao diện đăng nhập đã được cải thiện với:
- ✅ **Fullscreen support** - Nhấn F11 để fullscreen
- ✅ **Responsive design** - Tự động điều chỉnh theo kích thước màn hình
- ✅ **Offline mode** - Đăng nhập không cần server (để test UI)
- ✅ **Tài khoản admin mặc định** - Sẵn sàng để test

## 🚀 Cài Đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy ứng dụng
```bash
python -m PackingApp.main_app
```

## 🔐 Tài Khoản Admin Mặc Định (Offline Mode)

Khi chưa có server, bạn có thể sử dụng tài khoản admin mặc định:

### Thông tin đăng nhập:
- **Email/Phone/Username**: 
  - `admin@packing.com` HOẶC
  - `admin` HOẶC
  - `0123456789`
- **Mật khẩu**: `admin123`
- **Key xác thực**: 
  - `KEY_ADMIN_TEST_1234567890ABCDEF` HOẶC
  - `KEY_TEST` HOẶC
  - Bất kỳ key nào bắt đầu bằng `KEY_` (để test)

## 🎨 Tính Năng Giao Diện

### 1. Fullscreen Mode
- Nhấn **F11** để bật/tắt fullscreen
- Nhấn **ESC** để thoát fullscreen

### 2. Responsive Design
- Tự động điều chỉnh theo kích thước cửa sổ
- Form tự động căn giữa
- Tối ưu cho mọi kích thước màn hình

### 3. Keyboard Shortcuts
- **Enter** trong email field → Focus password
- **Enter** trong password field → Focus key
- **Enter** trong key field → Đăng nhập
- **F11** → Toggle fullscreen
- **ESC** → Thoát fullscreen

## ⚙️ Cấu Hình

### File `config.py`

Bạn có thể chỉnh sửa file `config.py` để thay đổi cấu hình:

```python
# Chế độ offline (không cần server)
OFFLINE_MODE = True  # True = offline, False = online

# URL của Web App (khi online mode)
WEB_APP_URL = 'http://localhost:3000'

# Kích thước cửa sổ mặc định
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 700
```

### Environment Variables

Hoặc sử dụng environment variables:

```bash
# Windows
set OFFLINE_MODE=true
set WEB_APP_URL=http://localhost:3000

# Linux/Mac
export OFFLINE_MODE=true
export WEB_APP_URL=http://localhost:3000
```

## 🔄 Chế Độ Offline vs Online

### Offline Mode (Mặc định)
- ✅ Không cần server
- ✅ Sử dụng tài khoản admin mặc định
- ✅ Phù hợp để test UI và phát triển
- ✅ Tự động fallback nếu không kết nối được server

### Online Mode
- ✅ Kết nối với Web App thật
- ✅ Xác thực với database thật
- ✅ Sử dụng keys thật từ Web App

## 📝 Quy Trình Đăng Nhập

### Offline Mode:
```
1. Nhập: admin@packing.com / admin123 / KEY_TEST
   ↓
2. Kiểm tra với tài khoản mặc định
   ↓
3. Lưu session
   ↓
4. Mở app chính
```

### Online Mode:
```
1. Nhập: email/phone + password + key
   ↓
2. Gửi request đến /api/auth/login
   ↓
3. Gửi request đến /api/auth/verify-key
   ↓
4. Lưu session
   ↓
5. Mở app chính
```

## 🎨 Giao Diện

### Layout:
- **Header**: Logo và tiêu đề
- **Form**: 
  - Email/Phone input
  - Password input
  - Key input
  - Status message
  - Login button
- **Footer**: Thông tin tài khoản mặc định và hướng dẫn

### Màu sắc:
- **Primary**: Blue (#2196F3)
- **Accent**: Orange (#FF9800)
- **Success**: Green (#4CAF50)
- **Error**: Red (#F44336)
- **Background**: Light Gray (#F5F5F5)

## 🐛 Troubleshooting

### Lỗi "Lỗi kết nối đến server"
- **Giải pháp**: App tự động chuyển sang offline mode
- Hoặc set `OFFLINE_MODE=true` trong `config.py`

### Không thể fullscreen
- Kiểm tra F11 có bị conflict với hệ thống không
- Thử nhấn ESC để thoát fullscreen

### Session không được lưu
- Kiểm tra quyền ghi file trong thư mục PackingApp
- Kiểm tra file `.session.json` có bị lock không

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra `config.py` đã đúng chưa
2. Kiểm tra console log
3. Kiểm tra file `.session.json`
4. Thử xóa `.session.json` và đăng nhập lại

## 🎯 Next Steps

Sau khi đăng nhập thành công:
1. App sẽ tự động mở giao diện chính
2. Session được lưu, lần sau chỉ cần nhập mật khẩu
3. Có thể tiếp tục phát triển các tính năng khác

