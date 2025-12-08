# config.py
# File cấu hình cho PackingApp

import os

# ============================================
# CẤU HÌNH KẾT NỐI SERVER
# ============================================

# URL của FastAPI Backend (PostgreSQL) - Đây là API chính
# ⚠️ QUAN TRỌNG: Nếu FastAPI chạy trên server khác, phải dùng IP của server đó
# Ví dụ: FASTAPI_URL = 'http://192.168.1.10:8000' (thay 192.168.1.10 bằng IP thực tế)
# Hoặc set environment variable: export FASTAPI_URL=http://192.168.1.10:8000
FASTAPI_URL = os.getenv('FASTAPI_URL', 'http://localhost:8000')

# Debug: In ra API URL để kiểm tra
print(f"🔍 [Config] FASTAPI_URL = {FASTAPI_URL}")

# URL của Web App Frontend (Next.js) - Chỉ dùng cho web browser
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://localhost:3000')

# Chế độ offline (không cần server)
# Set environment variable: OFFLINE_MODE=true hoặc false
# Hoặc sửa dòng dưới thành True/False
# True = Dùng tài khoản mặc định (không cần Web App)
# False = Kết nối với Web App (cần Web App chạy)
OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'

# ============================================
# TÀI KHOẢN ADMIN MẶC ĐỊNH (Offline Mode)
# ============================================

DEFAULT_ADMIN_EMAIL = 'admin@packing.com'
DEFAULT_ADMIN_PHONE = '0123456789'
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'

# ============================================
# KEYS MẶC ĐỊNH (Offline Mode)
# ============================================

DEFAULT_ADMIN_KEY = 'KEY_ADMIN_TEST_1234567890ABCDEF'
DEFAULT_TEST_KEY = 'KEY_TEST'

# ============================================
# CẤU HÌNH CAMERA (QUAN TRỌNG)
# ============================================

# URL/chỉ số của các luồng camera để HIỂN THỊ (preview)
# - Dùng số (0, 1, ...): cho webcam mặc định của máy tính (0 là cái đầu tiên)
# - Dùng chuỗi: cho camera IP (ví dụ: 'rtsp://user:pass@192.168.1.64/stream1')
CAMERA_PREVIEW_URLS = [0]

# URL/chỉ số của các luồng camera để GHI HÌNH (record)
# Thường giống với luồng preview, nhưng có thể khác nếu camera cung cấp 2 luồng (phụ và chính)
CAMERA_RECORD_URLS = [0]

# Kích thước khung hình hiển thị trên giao diện
CAMERA_PREVIEW_WIDTH = 640
CAMERA_PREVIEW_HEIGHT = 480
FPS = 30.0


# ============================================
# CẤU HÌNH GIAO DIỆN
# ============================================

# Cho phép fullscreen
ALLOW_FULLSCREEN = True

# Kích thước cửa sổ mặc định
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 700

# ============================================
# CẤU HÌNH KHÁC
# ============================================

# Timeout cho API requests (giây)
API_TIMEOUT = 10

# Retry attempts
API_RETRY_ATTEMPTS = 3

