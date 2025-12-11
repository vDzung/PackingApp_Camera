# account_widgets.py
# Widgets cho trang Tài khoản

import customtkinter as ctk
from datetime import datetime, timedelta
from . import utils
from . import auth

def _create_account_frame(app):
    """Khung Tài khoản - Hiển thị thông tin user"""
    app.account_frame = ctk.CTkFrame(app.main_content_frame, fg_color=utils.COLOR_BACKGROUND)
    app.frames["account"] = app.account_frame
    app.account_frame.grid_columnconfigure(0, weight=1)
    app.account_frame.grid_rowconfigure(1, weight=1) # Cho phép mở rộng chiều dọc
    
    # Tiêu đề
    title_label = ctk.CTkLabel(
        app.account_frame,
        text="👤 THÔNG TIN TÀI KHOẢN",
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color="#333"
    )
    title_label.grid(row=0, column=0, pady=(30, 20), sticky="n")
    
    # Container chính
    main_container = ctk.CTkFrame(app.account_frame, fg_color="white", corner_radius=15)
    main_container.grid(row=1, column=0, padx=40, pady=(0, 20), sticky="nsew")
    main_container.grid_rowconfigure(0, weight=1)
    main_container.grid_columnconfigure(0, weight=1)
    
    # Nội dung
    content_frame = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
    content_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
    
    # Button container
    button_container = ctk.CTkFrame(app.account_frame, fg_color="transparent")
    button_container.grid(row=2, column=0, pady=(0, 30), sticky="s")
    
    # Hàm để cập nhật thông tin
    def update_account_info():
        """Cập nhật thông tin tài khoản - REAL-TIME CHECK với server"""
        # Xóa các widget cũ
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        auth_manager = auth.AuthManager()
        session = auth_manager.get_session_info()
        
        if not session:
            error_label = ctk.CTkLabel(
                content_frame,
                text="Không tìm thấy thông tin tài khoản",
                font=ctk.CTkFont(size=16),
                text_color=utils.COLOR_RED_EXIT
            )
            error_label.pack(pady=20)
            return
        
        # REAL-TIME CHECK: Validate với server để đảm bảo user vẫn tồn tại
        is_valid, validation_message = auth_manager.validate_session_with_server()
        if not is_valid:
            # User đã bị xóa hoặc suspended - tự động logout
            import tkinter.messagebox as messagebox
            try:
                messagebox.showerror(
                    "Tài khoản không hợp lệ",
                    f"{validation_message}\n\nỨng dụng sẽ đóng để bảo mật."
                )
            except:
                pass
            
            # Xóa session và đóng app
            auth_manager.clear_session()
            import sys
            sys.exit(0)
            return
        
        # Thông tin cơ bản
        info_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        info_section.pack(fill="x", pady=(0, 20))
        
        # Email/Phone
        email_label = ctk.CTkLabel(
            info_section,
            text="📧 Email/Số điện thoại:",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        email_label.pack(pady=(0, 5), padx=10, fill="x")
        
        email_value = ctk.CTkLabel(
            info_section,
            text=session.get('email_or_phone', 'N/A'),
            font=ctk.CTkFont(size=15),
            text_color="#333",
            anchor="w"
        )
        email_value.pack(pady=(0, 15), padx=20, fill="x")
        
        # Loại tài khoản
        account_type_label = ctk.CTkLabel(
            info_section,
            text="🔑 Loại tài khoản:",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        account_type_label.pack(pady=(0, 5), padx=10, fill="x")
        
        is_admin = session.get('is_admin', False)
        account_type_value = ctk.CTkLabel(
            info_section,
            text="Admin" if is_admin else "Người dùng",
            font=ctk.CTkFont(size=15),
            text_color=utils.COLOR_ORANGE_ACCENT if is_admin else utils.COLOR_BLUE_ACTION,
            anchor="w"
        )
        account_type_value.pack(pady=(0, 15), padx=20, fill="x")
        
        # Gọi API /license-info để lấy data real-time (gọi 1 lần cho cả key và expiration)
        license_success, license_data, license_error = auth_manager.get_license_info()
        
        # ✅ Check KEY_EXPIRED và auto logout
        if license_error == "KEY_EXPIRED":
            # Key hết hạn → tự động đăng xuất
            import tkinter.messagebox as messagebox
            try:
                messagebox.showerror(
                    "Key đã hết hạn",
                    "Key đã hết hạn hoặc bị xóa. Vui lòng liên hệ admin để gia hạn.\n\nỨng dụng sẽ đóng."
                )
            except:
                pass
            
            # Clear session và đóng app
            auth_manager.clear_session()
            import sys
            sys.exit(0)
            return
        
        # Key (nếu có) - Hiển thị từ license_info API
        key_value_display = None
        if license_success and license_data and license_data.get('key'):
            key_value_display = license_data.get('key')
        elif session.get('key'):
            key_value_display = session.get('key')
        
        if key_value_display:
            key_section = ctk.CTkFrame(content_frame, fg_color="#F0F8FF", corner_radius=10)
            key_section.pack(fill="x", pady=(0, 20))
            
            key_label = ctk.CTkLabel(
                key_section,
                text="🔐 Key xác thực:",
                font=ctk.CTkFont(size=16, weight="bold"),
                anchor="w"
            )
            key_label.pack(pady=(15, 5), padx=15, fill="x")
            
            key_value = ctk.CTkEntry(
                key_section,
                fg_color="white",
                border_width=1,
                font=ctk.CTkFont(size=14, family="Courier"),
                text_color="#333"
            )
            key_value.insert(0, key_value_display)
            key_value.configure(state="readonly")
            key_value.pack(pady=(0, 15), padx=15, fill="x")
            
            # ✅ Trạng thái kích hoạt - check từ license_info API
            if license_success and license_data:
                status = license_data.get('status', 'expired')
                if status == 'active':
                    status_text = "✅ Đã kích hoạt"
                    status_color = utils.COLOR_GREEN_SUCCESS
                elif status == 'suspended':
                    status_text = "⛔ Đã bị đình chỉ"
                    status_color = utils.COLOR_RED_EXIT
                else:
                    status_text = "❌ Chưa kích hoạt hoặc hết hạn"
                    status_color = utils.COLOR_RED_EXIT
            else:
                # Fallback về session
                activated = session.get('key_activated', False)
                status_text = f"{'✅ Đã kích hoạt' if activated else '❌ Chưa kích hoạt'}"
                status_color = utils.COLOR_GREEN_SUCCESS if activated else utils.COLOR_RED_EXIT
            
            status_label = ctk.CTkLabel(
                key_section,
                text=f"Trạng thái: {status_text}",
                font=ctk.CTkFont(size=14),
                text_color=status_color,
                anchor="w"
            )
            status_label.pack(pady=(0, 15), padx=15, fill="x")
        
        # Thời gian hết hạn - REAL-TIME từ API /license-info
        expires_section = ctk.CTkFrame(content_frame, fg_color="#FFF8E1", corner_radius=10)
        expires_section.pack(fill="x", pady=(0, 20))
        
        expires_label = ctk.CTkLabel(
            expires_section,
            text="⏰ Thời gian hết hạn:",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        expires_label.pack(pady=(15, 5), padx=15, fill="x")
        
        # ✅ [3] UPDATE SESSION sau khi nhận data (đã được update trong get_license_info, nhưng đảm bảo)
        if license_success and license_data:
            # Session đã được update trong get_license_info(), nhưng reload để đảm bảo
            auth_manager.load_session()
            session = auth_manager.get_session_info()  # Reload session mới nhất
            # Có data từ API - hiển thị real-time
            expire_at = license_data.get('expire_at')
            days_left = license_data.get('days_left')
            status = license_data.get('status', 'expired')
            key_value = license_data.get('key')
            
            if expire_at and status != 'expired' and status != 'suspended':
                try:
                    expires_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
                    # Format ngày hết hạn
                    expires_str = expires_date.strftime("%d/%m/%Y %H:%M:%S")
                    
                    expires_value = ctk.CTkLabel(
                        expires_section,
                        text=f"{expires_str}",
                        font=ctk.CTkFont(size=15),
                        text_color="#333",
                        anchor="w"
                    )
                    expires_value.pack(pady=(0, 5), padx=15, fill="x")
                    
                    # Số ngày còn lại (từ API hoặc tính toán)
                    if days_left is not None:
                        remaining_days = days_left
                    else:
                        now = datetime.now()
                        remaining = expires_date - now
                        remaining_days = remaining.days
                    
                    if remaining_days > 0:
                        remaining_color = utils.COLOR_GREEN_SUCCESS if remaining_days > 7 else utils.COLOR_ORANGE_ACCENT
                        remaining_text = f"Còn lại: {remaining_days} ngày"
                    else:
                        remaining_color = utils.COLOR_RED_EXIT
                        remaining_text = "Đã hết hạn"
                    
                    remaining_label = ctk.CTkLabel(
                        expires_section,
                        text=remaining_text,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        text_color=remaining_color,
                        anchor="w"
                    )
                    remaining_label.pack(pady=(0, 15), padx=15, fill="x")
                except Exception as e:
                    error_label = ctk.CTkLabel(
                        expires_section,
                        text=f"Lỗi đọc thời gian hết hạn: {str(e)}",
                        font=ctk.CTkFont(size=14),
                        text_color=utils.COLOR_RED_EXIT,
                        anchor="w"
                    )
                    error_label.pack(pady=(0, 15), padx=15, fill="x")
            elif status == 'expired':
                # Key đã hết hạn
                expired_label = ctk.CTkLabel(
                    expires_section,
                    text="Key đã hết hạn – vui lòng liên hệ Admin để gia hạn",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=utils.COLOR_RED_EXIT,
                    anchor="w"
                )
                expired_label.pack(pady=(0, 15), padx=15, fill="x")
            elif status == 'suspended':
                # Key bị đình chỉ
                suspended_label = ctk.CTkLabel(
                    expires_section,
                    text="Key đã bị đình chỉ – vui lòng liên hệ Admin",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=utils.COLOR_RED_EXIT,
                    anchor="w"
                )
                suspended_label.pack(pady=(0, 15), padx=15, fill="x")
            else:
                # Không có thông tin
                no_expires_label = ctk.CTkLabel(
                    expires_section,
                    text="Không có thông tin hết hạn (Admin hoặc chưa kích hoạt key)",
                    font=ctk.CTkFont(size=14),
                    text_color=utils.COLOR_GRAY_ACCENT,
                    anchor="w"
                )
                no_expires_label.pack(pady=(0, 15), padx=15, fill="x")
        else:
            # Không lấy được từ API - fallback về session
            expires_at = session.get('key_expires_at')
            if expires_at:
                try:
                    expires_date = datetime.fromisoformat(expires_at)
                    now = datetime.now()
                    remaining = expires_date - now
                    remaining_days = remaining.days
                    
                    # Format ngày hết hạn
                    expires_str = expires_date.strftime("%d/%m/%Y %H:%M:%S")
                    
                    expires_value = ctk.CTkLabel(
                        expires_section,
                        text=f"{expires_str}",
                        font=ctk.CTkFont(size=15),
                        text_color="#333",
                        anchor="w"
                    )
                    expires_value.pack(pady=(0, 5), padx=15, fill="x")
                    
                    # Số ngày còn lại
                    if remaining_days > 0:
                        remaining_color = utils.COLOR_GREEN_SUCCESS if remaining_days > 7 else utils.COLOR_ORANGE_ACCENT
                        remaining_text = f"Còn lại: {remaining_days} ngày"
                    else:
                        remaining_color = utils.COLOR_RED_EXIT
                        remaining_text = "Đã hết hạn"
                    
                    remaining_label = ctk.CTkLabel(
                        expires_section,
                        text=remaining_text,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        text_color=remaining_color,
                        anchor="w"
                    )
                    remaining_label.pack(pady=(0, 15), padx=15, fill="x")
                except Exception as e:
                    error_label = ctk.CTkLabel(
                        expires_section,
                        text=f"Lỗi đọc thời gian hết hạn: {str(e)}",
                        font=ctk.CTkFont(size=14),
                        text_color=utils.COLOR_RED_EXIT,
                        anchor="w"
                    )
                    error_label.pack(pady=(0, 15), padx=15, fill="x")
            else:
                # Hiển thị lỗi hoặc thông báo
                if license_error:
                    error_text = f"Không thể lấy thông tin license: {license_error}"
                else:
                    error_text = "Không có thông tin hết hạn (Admin hoặc chưa kích hoạt key)"
                
                no_expires_label = ctk.CTkLabel(
                    expires_section,
                    text=error_text,
                    font=ctk.CTkFont(size=14),
                    text_color=utils.COLOR_GRAY_ACCENT,
                    anchor="w"
                )
                no_expires_label.pack(pady=(0, 15), padx=15, fill="x")
        
        # Thông tin đăng nhập
        login_info_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        login_info_section.pack(fill="x", pady=(0, 10))
        
        login_time = session.get('logged_in_at')
        if login_time:
            try:
                login_date = datetime.fromisoformat(login_time)
                login_str = login_date.strftime("%d/%m/%Y %H:%M:%S")
                
                login_label = ctk.CTkLabel(
                    login_info_section,
                    text=f"🕐 Đăng nhập lần cuối: {login_str}",
                    font=ctk.CTkFont(size=12),
                    text_color=utils.COLOR_GRAY_ACCENT,
                    anchor="w"
                )
                login_label.pack(pady=(0, 5), padx=10, fill="x")
            except:
                pass
    
    # Button container
    button_container = ctk.CTkFrame(main_container, fg_color="transparent")
    button_container.grid(row=1, column=0, pady=(0, 20))
    
    # Nút làm mới
    refresh_button = ctk.CTkButton(
        button_container,
        text="🔄 Làm mới",
        command=update_account_info,
        fg_color=utils.COLOR_BLUE_ACTION,
        width=200,
        height=50,
        font=ctk.CTkFont(size=16, weight="bold")
    )
    refresh_button.pack(side="left", padx=(0, 10))
    
    # Nút đăng xuất
    def handle_logout():
        """Xử lý đăng xuất"""
        import sys
        import os
        from . import auth
        
        # Xác nhận đăng xuất - Sử dụng tkinter.messagebox
        try:
            import tkinter.messagebox as messagebox
            result = messagebox.askyesno(
                "Xác nhận đăng xuất",
                "Bạn có chắc chắn muốn đăng xuất?\nBạn sẽ cần đăng nhập lại để sử dụng ứng dụng.",
                icon='question'
            )
        except Exception as e:
            # Fallback nếu messagebox không hoạt động - dùng CTkMessagebox hoặc tự tạo
            print(f"Lỗi hiển thị dialog: {e}")
            # Tạo dialog đơn giản với CTk
            try:
                import customtkinter as ctk
                dialog = ctk.CTkToplevel(app)
                dialog.title("Xác nhận đăng xuất")
                dialog.geometry("400x200")
                dialog.transient(app)
                dialog.grab_set()
                
                result_var = [False]  # Use list to modify in nested function
                
                label = ctk.CTkLabel(
                    dialog,
                    text="Bạn có chắc chắn muốn đăng xuất?",
                    font=ctk.CTkFont(size=14)
                )
                label.pack(pady=30)
                
                def confirm():
                    result_var[0] = True
                    dialog.destroy()
                
                def cancel():
                    result_var[0] = False
                    dialog.destroy()
                
                button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                button_frame.pack(pady=20)
                
                ctk.CTkButton(
                    button_frame,
                    text="Xác nhận",
                    command=confirm,
                    fg_color=utils.COLOR_RED_EXIT,
                    width=100
                ).pack(side="left", padx=10)
                
                ctk.CTkButton(
                    button_frame,
                    text="Hủy",
                    command=cancel,
                    fg_color=utils.COLOR_GRAY_ACCENT,
                    width=100
                ).pack(side="left", padx=10)
                
                dialog.wait_window()
                result = result_var[0]
            except Exception as e2:
                print(f"Lỗi tạo dialog: {e2}")
                result = True  # Mặc định cho phép đăng xuất
        
        if not result:
            return
        
        # Xóa session
        try:
            auth_manager = auth.AuthManager()
            auth_manager.clear_session()
        except Exception as e:
            print(f"Lỗi khi xóa session: {e}")
        
        # Đóng app hiện tại một cách an toàn
        try:
            app.on_closing()
        except Exception as e:
            print(f"Lỗi khi đóng app: {e}")
            try:
                app.destroy()
            except:
                pass
        
        # Khởi động lại app (sẽ hiển thị login window) - Không hiển thị terminal
        try:
            import subprocess
            python_exe = sys.executable
            # Lấy thư mục gốc của project
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Khởi động lại app trong process mới - Không hiển thị console window
            if sys.platform == "win32":
                # Sử dụng CREATE_NO_WINDOW để không hiển thị terminal
                subprocess.Popen(
                    [python_exe, "-m", "PackingApp.main_app"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    cwd=project_root
                )
            else:
                # Trên Linux/Mac, dùng detach để chạy nền
                subprocess.Popen(
                    [python_exe, "-m", "PackingApp.main_app"],
                    cwd=project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
        except Exception as e:
            print(f"Lỗi khi khởi động lại app: {e}")
            # Nếu không thể khởi động lại, chỉ cần thoát
            pass
        
        # Thoát app hiện tại
        try:
            sys.exit(0)
        except:
            pass
    
    logout_button = ctk.CTkButton(
        button_container,
        text="🚪 Đăng xuất",
        command=handle_logout,
        fg_color=utils.COLOR_RED_EXIT,
        hover_color="#CC3329",
        width=200,
        height=50,
        font=ctk.CTkFont(size=16, weight="bold")
    )
    logout_button.pack(side="left")
    
    # Cập nhật thông tin lần đầu
    update_account_info()
