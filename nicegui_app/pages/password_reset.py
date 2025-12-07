"""
Password reset pages for self-service password reset.
"""
from nicegui import ui, app
from src.services.password_reset_service import PasswordResetService
from src.services.audit_service import AuditService
from src.database import get_db
from nicegui_app.logo import LOGO_DATA_URL


def password_reset_request_page():
    """Page for requesting a password reset (enter username/email)."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    with ui.column().classes('w-full h-screen flex items-center justify-center'):
        with ui.card().classes('w-96 p-8'):
            # Logo and title
            with ui.column().classes('w-full items-center mb-6'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 80px; width: auto; margin-bottom: 16px;')
                ui.label('PASSWORD RESET').classes('text-xl font-bold text-center').style('color: #5a6a72;')

            ui.label('Enter your username or email address to request a password reset.').classes('text-sm text-center mb-4 opacity-70')

            # Username/email input
            identifier_input = ui.input(label='Username or Email').classes('w-full mb-4')

            # Message area
            message_label = ui.label('').classes('text-sm mb-4')
            message_label.set_visibility(False)

            def request_reset():
                identifier = identifier_input.value.strip()
                if not identifier:
                    message_label.text = 'Please enter your username or email'
                    message_label.classes('text-red-500')
                    message_label.set_visibility(True)
                    return

                db = next(get_db())
                try:
                    reset_service = PasswordResetService(db)

                    # Try to find user by email or username
                    user = reset_service.get_user_by_email(identifier)
                    if not user:
                        user = reset_service.get_user_by_username(identifier)

                    if user:
                        # Create reset token
                        token, _ = reset_service.create_reset_token(user.id)

                        # Log the request
                        AuditService.log(
                            db, action='password_reset_requested',
                            user_id=user.id, username=user.username,
                            details={'method': 'self_service'}
                        )

                        # Show success with token (in production, this would be emailed)
                        message_label.text = f'Reset token generated. Please use this link to reset your password:'
                        message_label.classes('text-green-600', remove='text-red-500')
                        message_label.set_visibility(True)

                        # Show the reset link
                        with ui.column().classes('w-full mt-4 p-3 bg-gray-100 rounded'):
                            ui.label('Your reset link:').classes('text-xs opacity-60')
                            reset_url = f'/reset-password/{token}'
                            ui.link(reset_url, reset_url).classes('text-sm text-blue-600 break-all')
                            ui.label('This link expires in 24 hours.').classes('text-xs opacity-60 mt-2')
                    else:
                        # Don't reveal if user exists or not (security)
                        message_label.text = 'If an account exists with that username/email, a reset link has been generated.'
                        message_label.classes('text-green-600', remove='text-red-500')
                        message_label.set_visibility(True)

                except Exception as e:
                    message_label.text = 'Error processing request. Please try again.'
                    message_label.classes('text-red-500', remove='text-green-600')
                    message_label.set_visibility(True)
                finally:
                    db.close()

            ui.button('Request Reset', on_click=request_reset).classes('w-full mb-4')
            ui.button('Back to Login', on_click=lambda: ui.navigate.to('/')).props('flat').classes('w-full')


def password_reset_page(token: str):
    """Page for resetting password with a valid token."""

    # Apply dark mode if previously set
    dark_mode = ui.dark_mode()
    is_dark = app.storage.general.get('dark_mode', False)
    if is_dark:
        dark_mode.enable()

    with ui.column().classes('w-full h-screen flex items-center justify-center'):
        with ui.card().classes('w-96 p-8'):
            # Logo and title
            with ui.column().classes('w-full items-center mb-6'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 80px; width: auto; margin-bottom: 16px;')
                ui.label('SET NEW PASSWORD').classes('text-xl font-bold text-center').style('color: #5a6a72;')

            # Validate token first
            db = next(get_db())
            try:
                reset_service = PasswordResetService(db)
                is_valid, user, error_message = reset_service.validate_token(token)

                if not is_valid:
                    ui.label(error_message).classes('text-red-500 text-center mb-4')
                    ui.button('Request New Reset', on_click=lambda: ui.navigate.to('/forgot-password')).classes('w-full mb-2')
                    ui.button('Back to Login', on_click=lambda: ui.navigate.to('/')).props('flat').classes('w-full')
                    return

                ui.label(f'Resetting password for: {user.username}').classes('text-sm text-center mb-4 opacity-70')

                # Password inputs
                password_input = ui.input(label='New Password', password=True).classes('w-full mb-2')
                confirm_input = ui.input(label='Confirm Password', password=True).classes('w-full mb-4')

                # Requirements hint
                ui.label('Password must be at least 8 characters with a letter and number.').classes('text-xs opacity-60 mb-4')

                # Message area
                message_label = ui.label('').classes('text-sm mb-4')
                message_label.set_visibility(False)

                def reset_password():
                    password = password_input.value
                    confirm = confirm_input.value

                    # Validate password
                    if not password:
                        message_label.text = 'Please enter a password'
                        message_label.classes('text-red-500')
                        message_label.set_visibility(True)
                        return

                    if len(password) < 8:
                        message_label.text = 'Password must be at least 8 characters'
                        message_label.classes('text-red-500')
                        message_label.set_visibility(True)
                        return

                    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
                        message_label.text = 'Password must contain at least one letter and one number'
                        message_label.classes('text-red-500')
                        message_label.set_visibility(True)
                        return

                    if password != confirm:
                        message_label.text = 'Passwords do not match'
                        message_label.classes('text-red-500')
                        message_label.set_visibility(True)
                        return

                    db2 = next(get_db())
                    try:
                        reset_service2 = PasswordResetService(db2)
                        success, msg = reset_service2.reset_password(token, password)

                        if success:
                            # Log the reset
                            AuditService.log(
                                db2, action='password_reset_completed',
                                user_id=user.id, username=user.username
                            )

                            message_label.text = 'Password reset successfully! Redirecting to login...'
                            message_label.classes('text-green-600', remove='text-red-500')
                            message_label.set_visibility(True)

                            # Redirect to login after short delay
                            ui.timer(2.0, lambda: ui.navigate.to('/'), once=True)
                        else:
                            message_label.text = msg
                            message_label.classes('text-red-500')
                            message_label.set_visibility(True)

                    except Exception as e:
                        message_label.text = 'Error resetting password. Please try again.'
                        message_label.classes('text-red-500')
                        message_label.set_visibility(True)
                    finally:
                        db2.close()

                ui.button('Reset Password', on_click=reset_password).classes('w-full mb-4')
                ui.button('Back to Login', on_click=lambda: ui.navigate.to('/')).props('flat').classes('w-full')

            finally:
                db.close()
