# auth.py
# Module xử lý authentication với Web App

import requests
import json
import os
from datetime import datetime, timedelta

# Import config
try:
    from . import config
    # Sử dụng FastAPI URL cho API calls (PostgreSQL backend)
    API_BASE_URL = getattr(config, 'FASTAPI_URL', 'http://localhost:8000')
    OFFLINE_MODE = config.OFFLINE_MODE
except ImportError:
    # Fallback nếu không có config
    # Mặc định dùng FastAPI (localhost:8000) thay vì Next.js (localhost:3000)
    API_BASE_URL = os.getenv('FASTAPI_URL', 'http://localhost:8000')
    OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'

# ✅ [2] Debug: Log API_BASE_URL để kiểm tra
print(f"🔍 [Auth] API_BASE_URL = {API_BASE_URL}")
print(f"🔍 [Auth] OFFLINE_MODE = {OFFLINE_MODE}")

# API Endpoints - Gọi trực tiếp đến FastAPI Backend (PostgreSQL)
API_ENDPOINTS = {
    'login': f'{API_BASE_URL}/api/auth/login',
    'activate_key': f'{API_BASE_URL}/api/auth/activate-key',  # Kích hoạt key để sử dụng app (lần đầu)
    'verify_key': f'{API_BASE_URL}/api/auth/verify-key',
    'check_auth': f'{API_BASE_URL}/api/auth/check',
    'validate_user': f'{API_BASE_URL}/api/auth/validate-user',
    'license_info': f'{API_BASE_URL}/license-info'  # Get license info real-time (no prefix)
}

# Debug: Log license endpoint
print(f"🔍 [Auth] License info endpoint: {API_ENDPOINTS['license_info']}")

# Tài khoản admin mặc định (chỉ dùng khi OFFLINE_MODE = true)
DEFAULT_ADMIN_ACCOUNTS = {
    'admin@packing.com': {
        'password': 'admin123',
        'phone': '0123456789',
        'is_admin': True,
        'user_id': 1
    },
    'admin': {
        'password': 'admin123',
        'phone': '0123456789',
        'is_admin': True,
        'user_id': 1
    },
    '0123456789': {
        'password': 'admin123',
        'phone': '0123456789',
        'is_admin': True,
        'user_id': 1
    }
}

# Keys mặc định (chỉ dùng khi OFFLINE_MODE = true)
DEFAULT_KEYS = {
    'KEY_ADMIN_TEST_1234567890ABCDEF': {
        'phone': '0123456789',
        'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
        'is_active': True
    },
    'KEY_TEST': {
        'phone': '0123456789',
        'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
        'is_active': True
    }
}

# File lưu session
SESSION_FILE = os.path.join(os.path.dirname(__file__), '.session.json')

class AuthError(Exception):
    """Custom exception cho authentication errors"""
    pass

class AuthManager:
    """Quản lý authentication với Web App"""
    
    def __init__(self):
        self.session_data = None
        self.load_session()
    
    def load_session(self):
        """Load session từ file"""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    self.session_data = json.load(f)
            except Exception as e:
                print(f"Lỗi khi đọc session: {e}")
                self.session_data = None
    
    def save_session(self, data):
        """Lưu session vào file"""
        try:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.session_data = data
        except Exception as e:
            print(f"Lỗi khi lưu session: {e}")
            raise AuthError(f"Không thể lưu session: {e}")
    
    def clear_session(self):
        """Xóa session"""
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception as e:
                print(f"Lỗi khi xóa session: {e}")
        self.session_data = None
    
    def login(self, email_or_phone, password):
        """
        Đăng nhập với email/phone và password
        Returns: (success: bool, message: str, data: dict)
        """
        # Chế độ offline - sử dụng tài khoản mặc định
        if OFFLINE_MODE:
            account = DEFAULT_ADMIN_ACCOUNTS.get(email_or_phone)
            if account and account['password'] == password:
                session_info = {
                    'email_or_phone': email_or_phone,
                    'user_id': account['user_id'],
                    'is_admin': account['is_admin'],
                    'logged_in_at': datetime.now().isoformat()
                }
                self.save_session(session_info)
                return True, 'Đăng nhập thành công! (Offline Mode)', session_info
            else:
                return False, 'Email/Số điện thoại hoặc mật khẩu không đúng', None
        
        # Chế độ online - kết nối với server
        try:
            response = requests.post(
                API_ENDPOINTS['login'],
                json={
                    'email_or_phone': email_or_phone,
                    'password': password,
                    'source': 'app'  # Mark as desktop app login (check is_activated)
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Kiểm tra status code trước khi parse JSON
            if response.status_code != 200:
                try:
                    data = response.json()
                    # FastAPI trả về {detail: "..."} cho HTTP errors
                    error_msg = data.get('detail') or data.get('error') or f'Lỗi server (HTTP {response.status_code})'
                except:
                    error_msg = f'Lỗi server (HTTP {response.status_code})'
                return False, error_msg, None
            
            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                return False, f'Lỗi định dạng response từ server: {str(e)}', None
            
            # FastAPI trả về format: {success: true, message: "...", isAdmin: bool, userId: int, access_token: "..."}
            # Hoặc có thể có nested 'data' key từ Next.js proxy
            if data.get('success'):
                # Lấy data từ response (có thể nằm trong 'data' key hoặc ở root level)
                response_data = data.get('data', data)
                
                # Lưu thông tin đăng nhập
                # FastAPI trả về: userId, isAdmin (camelCase)
                user_id = response_data.get('userId') or response_data.get('user_id') or data.get('userId')
                is_admin = response_data.get('isAdmin') or response_data.get('is_admin') or data.get('isAdmin', False)
                
                if not user_id:
                    return False, 'Response thiếu thông tin userId', None
                
                # Lấy access_token từ response để dùng cho API calls
                access_token = response_data.get('access_token') or data.get('access_token')
                
                session_info = {
                    'email_or_phone': email_or_phone,
                    'user_id': user_id,
                    'is_admin': is_admin,
                    'access_token': access_token,  # Lưu token để gọi API license-info
                    'logged_in_at': datetime.now().isoformat()
                }
                self.save_session(session_info)
                message = response_data.get('message') or data.get('message', 'Đăng nhập thành công!')
                return True, message, session_info
            else:
                # Lỗi từ API - FastAPI trả về {detail: "..."} hoặc {error: "..."}
                error_msg = data.get('detail') or data.get('error') or data.get('message', 'Đăng nhập thất bại')
                return False, error_msg, None
                
        except requests.exceptions.ConnectionError as e:
            # Nếu không kết nối được server, tự động chuyển sang offline mode
            account = DEFAULT_ADMIN_ACCOUNTS.get(email_or_phone)
            if account and account['password'] == password:
                session_info = {
                    'email_or_phone': email_or_phone,
                    'user_id': account['user_id'],
                    'is_admin': account['is_admin'],
                    'logged_in_at': datetime.now().isoformat(),
                    'offline_mode': True
                }
                self.save_session(session_info)
                return True, 'Đăng nhập thành công! (Offline Mode - Server không khả dụng)', session_info
            else:
                return False, f"Lỗi kết nối đến server và tài khoản không khớp với admin mặc định", None
        except requests.exceptions.RequestException as e:
            return False, f"Lỗi kết nối đến server: {str(e)}", None
        except Exception as e:
            return False, f"Lỗi không xác định: {str(e)}", None
    
    def activate_account(self, email_or_phone, password, key):
        """
        Kích hoạt key để sử dụng app (lần đầu nhập key vào app)
        - Key chỉ dùng 1 lần (set is_used=1)
        - Sau khi kích hoạt, user chỉ cần email/password để login app
        Returns: (success: bool, message: str, data: dict)
        """
        # Chế độ offline - không hỗ trợ activation
        if OFFLINE_MODE:
            return False, 'Chế độ offline không hỗ trợ kích hoạt key', None
        
        # Chế độ online - kết nối với server
        try:
            response = requests.post(
                API_ENDPOINTS['activate_key'],
                json={
                    'email_or_phone': email_or_phone,
                    'password': password,
                    'key': key.strip()
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Kiểm tra status code trước khi parse JSON
            if response.status_code != 200:
                try:
                    data = response.json()
                    # FastAPI trả về {detail: "..."} cho HTTP errors
                    error_msg = data.get('detail') or data.get('error') or f'Lỗi server (HTTP {response.status_code})'
                except:
                    error_msg = f'Lỗi server (HTTP {response.status_code})'
                return False, error_msg, None
            
            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                return False, f'Lỗi định dạng response từ server: {str(e)}', None
            
            # FastAPI trả về format: {success: true, message: "...", isAdmin: bool, userId: int, access_token: "..."}
            if data.get('success'):
                # Lấy data từ response
                response_data = data.get('data', data)
                
                # Lưu thông tin đăng nhập
                user_id = response_data.get('userId') or response_data.get('user_id') or data.get('userId')
                is_admin = response_data.get('isAdmin') or response_data.get('is_admin') or data.get('isAdmin', False)
                
                if not user_id:
                    return False, 'Response thiếu thông tin userId', None
                
                # Lấy access_token và key_expires_at từ response (nếu có)
                access_token = response_data.get('access_token') or data.get('access_token')
                key_expires_at = response_data.get('key_expires_at') or data.get('key_expires_at')
                
                session_info = {
                    'email_or_phone': email_or_phone,
                    'user_id': user_id,
                    'is_admin': is_admin,
                    'access_token': access_token,  # Lưu token để gọi API license-info
                    'key_activated': True,  # Đánh dấu key đã được kích hoạt (is_used=1)
                    'key_expires_at': key_expires_at,  # Lưu key expiration (fallback)
                    'logged_in_at': datetime.now().isoformat()
                }
                self.save_session(session_info)
                message = response_data.get('message') or data.get('message', 'Kích hoạt key thành công!')
                return True, message, session_info
            else:
                # Lỗi từ API
                error_msg = data.get('detail') or data.get('error') or data.get('message', 'Kích hoạt thất bại')
                return False, error_msg, None
                
        except requests.exceptions.ConnectionError as e:
            return False, f"Lỗi kết nối đến server: {str(e)}", None
        except requests.exceptions.RequestException as e:
            return False, f"Lỗi kết nối đến server: {str(e)}", None
        except Exception as e:
            return False, f"Lỗi không xác định: {str(e)}", None
    
    def verify_key(self, key):
        """
        Xác thực key với Web App
        Returns: (success: bool, message: str, key_data: dict)
        """
        # Chế độ offline - sử dụng keys mặc định
        if OFFLINE_MODE or (self.session_data and self.session_data.get('offline_mode')):
            key_info = DEFAULT_KEYS.get(key.upper())
            if key_info:
                key_data = {
                    'phone': key_info['phone'],
                    'expires_at': key_info['expires_at']
                }
                # Cập nhật session với thông tin key
                if self.session_data:
                    self.session_data['key'] = key.upper()
                    self.session_data['key_phone'] = key_info['phone']
                    self.session_data['key_expires_at'] = key_info['expires_at']
                    self.session_data['key_verified_at'] = datetime.now().isoformat()
                    self.session_data['key_activated'] = True  # Đánh dấu đã kích hoạt
                    self.save_session(self.session_data)
                
                return True, 'Key hợp lệ! (Offline Mode)', key_data
            else:
                # Cho phép bất kỳ key nào nếu bắt đầu bằng KEY_ (để test)
                if key.upper().startswith('KEY_'):
                    key_data = {
                        'phone': self.session_data.get('email_or_phone', '0123456789') if self.session_data else '0123456789',
                        'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
                    }
                    if self.session_data:
                        self.session_data['key'] = key.upper()
                        self.session_data['key_phone'] = key_data['phone']
                        self.session_data['key_expires_at'] = key_data['expires_at']
                        self.session_data['key_verified_at'] = datetime.now().isoformat()
                        self.session_data['key_activated'] = True  # Đánh dấu đã kích hoạt
                        self.save_session(self.session_data)
                    return True, 'Key hợp lệ! (Offline Mode - Test Key)', key_data
                return False, 'Key không hợp lệ. Sử dụng KEY_ADMIN_TEST_1234567890ABCDEF hoặc KEY_TEST', None
        
        # Chế độ online - kết nối với server
        try:
            response = requests.post(
                API_ENDPOINTS['verify_key'],
                json={'key': key},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Kiểm tra status code trước khi parse JSON
            if response.status_code != 200:
                try:
                    data = response.json()
                    # FastAPI trả về {detail: "..."} cho HTTP errors
                    error_msg = data.get('detail') or data.get('error') or f'Lỗi server (HTTP {response.status_code})'
                except:
                    error_msg = f'Lỗi server (HTTP {response.status_code})'
                return False, error_msg, None
            
            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                return False, f'Lỗi định dạng response từ server: {str(e)}', None
            
            # FastAPI trả về format: {success: true, phone: "...", expires_at: "..."}
            # Hoặc có thể có nested 'data' key từ Next.js proxy
            if data.get('success'):
                # Lấy data từ response (có thể nằm trong 'data' key hoặc ở root level)
                response_data = data.get('data', data)
                
                # FastAPI trả về: phone, expires_at
                phone = response_data.get('phone') or data.get('phone')
                expires_at = response_data.get('expires_at') or data.get('expires_at')
                
                if not phone or not expires_at:
                    return False, 'Response thiếu thông tin phone hoặc expires_at', None
                
                # Cập nhật session với thông tin key
                if self.session_data:
                    self.session_data['key'] = key
                    self.session_data['key_phone'] = phone
                    self.session_data['key_expires_at'] = expires_at
                    self.session_data['key_verified_at'] = datetime.now().isoformat()
                    self.session_data['key_activated'] = True  # Đánh dấu đã kích hoạt
                    self.save_session(self.session_data)
                
                # Trả về key_data với format chuẩn
                key_data = {
                    'phone': phone,
                    'expires_at': expires_at
                }
                return True, 'Key hợp lệ!', key_data
            else:
                # FastAPI trả về {detail: "..."} cho errors
                error_msg = data.get('detail') or data.get('error', 'Key không hợp lệ')
                return False, error_msg, None
                
        except requests.exceptions.ConnectionError:
            # Nếu không kết nối được, tự động chuyển sang offline mode
            if key.upper().startswith('KEY_'):
                key_data = {
                    'phone': self.session_data.get('email_or_phone', '0123456789') if self.session_data else '0123456789',
                    'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
                }
                if self.session_data:
                    self.session_data['key'] = key.upper()
                    self.session_data['key_phone'] = key_data['phone']
                    self.session_data['key_expires_at'] = key_data['expires_at']
                    self.session_data['key_verified_at'] = datetime.now().isoformat()
                    self.session_data['key_activated'] = True  # Đánh dấu đã kích hoạt
                    self.session_data['offline_mode'] = True
                    self.save_session(self.session_data)
                return True, 'Key hợp lệ! (Offline Mode - Server không khả dụng)', key_data
            return False, 'Lỗi kết nối đến server và key không hợp lệ', None
        except requests.exceptions.RequestException as e:
            return False, f"Lỗi kết nối đến server: {str(e)}", None
        except Exception as e:
            return False, f"Lỗi không xác định: {str(e)}", None
    
    def check_key_status(self):
        """Kiểm tra trạng thái key trong session"""
        if not self.session_data or 'key' not in self.session_data:
            return False, "Chưa có key trong session"
        
        expires_at = self.session_data.get('key_expires_at')
        if not expires_at:
            return False, "Không có thông tin hết hạn"
        
        try:
            expires_date = datetime.fromisoformat(expires_at)
            now = datetime.now()
            
            if now > expires_date:
                return False, "Key đã hết hạn"
            
            remaining = expires_date - now
            return True, f"Key còn hạn ({remaining.days} ngày)"
        except Exception as e:
            return False, f"Lỗi kiểm tra key: {str(e)}"
    
    def is_authenticated(self):
        """Kiểm tra xem đã đăng nhập và có key chưa (hoặc là admin hoặc đã kích hoạt)"""
        if not self.session_data:
            return False
        
        has_login = 'email_or_phone' in self.session_data
        is_admin = self.session_data.get('is_admin', False)
        has_key = 'key' in self.session_data
        key_activated = self.session_data.get('key_activated', False)
        
        if not has_login:
            return False
        
        # Admin không cần key
        if is_admin:
            return True
        
        # Nếu đã kích hoạt key rồi, không cần kiểm tra key nữa
        if key_activated:
            return True
        
        # User thường chưa kích hoạt cần key
        if not has_key:
            return False
        
        # Kiểm tra key còn hạn không
        is_valid, _ = self.check_key_status()
        return is_valid
    
    def is_key_activated(self):
        """Kiểm tra xem key đã được kích hoạt chưa"""
        if not self.session_data:
            return False
        return self.session_data.get('key_activated', False)
    
    def get_session_info(self):
        """Lấy thông tin session hiện tại"""
        return self.session_data
    
    def get_license_info(self):
        """
        Lấy thông tin license real-time từ API /license-info
        Returns: (success: bool, license_data: dict, error: str)
        """
        if OFFLINE_MODE or (self.session_data and self.session_data.get('offline_mode')):
            # Offline mode - return từ session
            session = self.get_session_info()
            if session and session.get('key_expires_at'):
                return True, {
                    'key': session.get('key'),
                    'expire_at': session.get('key_expires_at'),
                    'days_left': None,  # Calculate if needed
                    'status': 'active' if session.get('key_activated') else 'expired'
                }, None
            return False, None, "Chưa có key trong session"
        
        # Online mode - gọi API
        session = self.get_session_info()
        if not session:
            return False, None, "Chưa đăng nhập"
        
        access_token = session.get('access_token')
        if not access_token:
            return False, None, "Không có access token"
        
        # Debug: Log API URL và token format
        license_url = API_ENDPOINTS['license_info']
        print(f"🔍 [get_license_info] API URL: {license_url}")
        print(f"🔍 [get_license_info] API_BASE_URL: {API_BASE_URL}")
        print(f"🔍 [get_license_info] Token present: {bool(access_token)}")
        print(f"🔍 [get_license_info] Token length: {len(access_token) if access_token else 0}")
        
        try:
            # Đảm bảo Authorization header đúng format: "Bearer {token}"
            auth_header = f"Bearer {access_token}".strip()
            print(f"🔍 [get_license_info] Authorization header: Bearer {access_token[:20]}...")
            
            response = requests.get(
                license_url,
                headers={
                    "Authorization": auth_header,  # Đảm bảo chữ hoa đúng
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            print(f"🔍 [get_license_info] Response status: {response.status_code}")
            
            if response.status_code == 401:
                # ✅ Check KEY_EXPIRED từ middleware
                try:
                    error_data = response.json()
                    if error_data.get('detail') == 'KEY_EXPIRED':
                        # Key hết hạn → trigger auto logout
                        print(f"❌ KEY_EXPIRED detected - triggering auto logout")
                        # Clear session
                        self.clear_session()
                        return False, None, "KEY_EXPIRED"
                except:
                    pass
                
                # Token expired - cần đăng nhập lại
                return False, None, "Token đã hết hạn. Vui lòng đăng nhập lại."
            
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    # ✅ Check KEY_EXPIRED trong error response
                    if error_data.get('detail') == 'KEY_EXPIRED':
                        print(f"❌ KEY_EXPIRED detected - triggering auto logout")
                        self.clear_session()
                        return False, None, "KEY_EXPIRED"
                    
                    error_msg = error_data.get('detail') or error_data.get('error') or f'Lỗi server (HTTP {response.status_code})'
                except:
                    error_msg = f'Lỗi server (HTTP {response.status_code})'
                return False, None, error_msg
            
            # Parse response
            try:
                license_data = response.json()
                print(f"🔍 [get_license_info] Response data: {license_data}")
                
                # ✅ [3] UPDATE SESSION ngay sau khi nhận data từ API
                if license_data:
                    # Cập nhật session với data mới nhất
                    if self.session_data:
                        self.session_data['key_expires_at'] = license_data.get('expire_at')
                        self.session_data['key'] = license_data.get('key')
                        self.session_data['license_status'] = license_data.get('status')
                        self.session_data['license_days_left'] = license_data.get('days_left')
                        # Lưu session
                        self.save_session(self.session_data)
                        print(f"✅ [get_license_info] Session updated with license data")
                
                return True, license_data, None
            except ValueError as e:
                print(f"❌ [get_license_info] JSON parse error: {e}")
                return False, None, f'Lỗi định dạng response: {str(e)}'
                
        except requests.exceptions.ConnectionError:
            return False, None, "Lỗi kết nối đến server"
        except requests.exceptions.RequestException as e:
            return False, None, f"Lỗi kết nối: {str(e)}"
        except Exception as e:
            return False, None, f"Lỗi không xác định: {str(e)}"
    
    def handle_api_response(self, response):
        """
        ✅ Wrapper để handle KEY_EXPIRED từ mọi API response
        Returns: (is_key_expired: bool, error_message: str)
        """
        if response.status_code == 401:
            try:
                error_data = response.json()
                if error_data.get('detail') == 'KEY_EXPIRED':
                    print(f"❌ KEY_EXPIRED detected in API response - triggering auto logout")
                    self.clear_session()
                    return True, "KEY_EXPIRED"
            except:
                pass
        return False, None
    
    def validate_session_with_server(self):
        """
        Xác thực session với server để đảm bảo user vẫn tồn tại
        Returns: (is_valid: bool, message: str)
        """
        # Chế độ offline - không cần validate
        if OFFLINE_MODE or (self.session_data and self.session_data.get('offline_mode')):
            return True, "Offline mode - không cần validate"
        
        # Không có session
        if not self.session_data or not self.session_data.get('email_or_phone'):
            return False, "Chưa đăng nhập"
        
        email_or_phone = self.session_data.get('email_or_phone')
        user_id = self.session_data.get('user_id')
        
        # Kiểm tra user có tồn tại trên server không
        try:
            response = requests.post(
                API_ENDPOINTS['validate_user'],
                json={
                    'email_or_phone': email_or_phone,
                    'user_id': user_id
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # ✅ Check KEY_EXPIRED từ middleware
            is_expired, expired_msg = self.handle_api_response(response)
            if is_expired:
                return False, "Key đã hết hạn. Vui lòng liên hệ admin để gia hạn."
            
            # Parse response
            try:
                data = response.json()
            except ValueError:
                # Nếu không parse được JSON, check status code
                if response.status_code == 404:
                    return False, "Tài khoản không tồn tại hoặc đã bị xóa"
                elif response.status_code == 403:
                    return False, "Tài khoản đã bị đình chỉ"
                elif response.status_code == 401:
                    # Có thể là KEY_EXPIRED
                    return False, "Key đã hết hạn. Vui lòng liên hệ admin để gia hạn."
                else:
                    # Lỗi khác - cho phép tiếp tục (fallback)
                    return True, f"Không thể validate với server (HTTP {response.status_code}) - cho phép tiếp tục"
            
            # Kiểm tra response
            if response.status_code == 403:
                # User bị suspended - không cho phép tiếp tục
                error_detail = data.get('detail', 'Tài khoản đã bị đình chỉ')
                return False, error_detail
            elif response.status_code == 200:
                # Check if user exists
                exists = data.get('exists', False)
                success = data.get('success', False)
                
                if not exists or not success:
                    # User không tồn tại - đã bị xóa
                    message = data.get('message', 'Tài khoản không tồn tại hoặc đã bị xóa')
                    return False, message
                else:
                    # User vẫn tồn tại trên server và không bị suspended
                    return True, "User vẫn tồn tại trên server"
            else:
                # Status code khác - user không tồn tại hoặc lỗi
                if response.status_code == 404:
                    return False, "Tài khoản không tồn tại hoặc đã bị xóa"
                else:
                    # Lỗi khác - cho phép tiếp tục (fallback)
                    return True, f"Không thể validate với server (HTTP {response.status_code}) - cho phép tiếp tục"
                
        except requests.exceptions.ConnectionError:
            # Không kết nối được server - cho phép tiếp tục nếu có session
            return True, "Không kết nối được server - sử dụng session local"
        except requests.exceptions.RequestException as e:
            # Lỗi kết nối - cho phép tiếp tục (fallback)
            return True, f"Lỗi kết nối đến server: {str(e)} - cho phép tiếp tục"
        except Exception as e:
            # Lỗi khác - cho phép tiếp tục (fallback)
            return True, f"Lỗi không xác định: {str(e)} - cho phép tiếp tục"

