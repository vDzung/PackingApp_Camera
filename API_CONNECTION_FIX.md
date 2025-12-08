# 🔧 Fix: Kết Nối Python App với FastAPI Backend

## ✅ Đã Sửa

### 1. **Cấu hình API URL**
- **File:** `config.py`
- **Thay đổi:** Thêm `FASTAPI_URL = 'http://localhost:8000'` (FastAPI Backend)
- **Giữ lại:** `WEB_APP_URL = 'http://localhost:3000'` (Next.js Frontend - chỉ dùng cho web browser)

### 2. **Sửa auth.py để gọi FastAPI**
- **File:** `auth.py`
- **Thay đổi:** 
  - `API_BASE_URL` giờ dùng `config.FASTAPI_URL` thay vì `config.WEB_APP_URL`
  - Endpoints giờ gọi trực tiếp đến FastAPI: `http://localhost:8000/api/auth/*`
  - Parse response đúng format FastAPI: `{detail: "..."}` cho errors, `{success: true, ...}` cho success

### 3. **Response Format Handling**
- **Login:** Parse `userId`, `isAdmin` từ FastAPI response
- **Verify Key:** Parse `phone`, `expires_at` từ FastAPI response
- **Error Handling:** Parse `detail` từ FastAPI HTTPException

## 🎯 Endpoints

Python App giờ gọi trực tiếp đến FastAPI:
- `POST http://localhost:8000/api/auth/login`
- `POST http://localhost:8000/api/auth/verify-key`
- `GET http://localhost:8000/api/auth/check`
- `POST http://localhost:8000/api/auth/validate-user`

## 📝 Lưu Ý

1. **FastAPI phải chạy:** Đảm bảo FastAPI server đang chạy ở `http://localhost:8000`
2. **PostgreSQL phải kết nối:** Đảm bảo FastAPI đã kết nối với PostgreSQL
3. **Tài khoản phải có trong DB:** Tài khoản tạo trên webapp phải có trong PostgreSQL

## 🧪 Test

1. **Khởi động FastAPI:**
   ```bash
   cd FastAPI_Backend
   python main.py
   ```

2. **Khởi động Python App:**
   ```bash
   cd PackingApp
   python main_app.py
   ```

3. **Đăng nhập:**
   - Dùng email/phone và password đã tạo trên webapp
   - App sẽ gọi trực tiếp đến FastAPI
   - Nếu thành công, sẽ lưu session và cho phép kích hoạt key

4. **Kích hoạt key:**
   - Nhập key đã được tạo trên webapp (admin dashboard)
   - App sẽ verify key với FastAPI
   - Nếu hợp lệ, sẽ lưu vào session và cho phép sử dụng app

