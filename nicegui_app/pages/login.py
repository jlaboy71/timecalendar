from nicegui import ui, app
from src.services.user_service import UserService
from src.services.audit_service import AuditService
from src.services.rate_limiter import LoginRateLimiter
from src.services.year_end_service import YearEndService
from src.database import get_db
from nicegui_app.logo import LOGO_DATA_URL
from nicegui_app.components.theme import apply_dark_mode, validate_required


def login_page(timeout: str = None):
    """Create a centered login page with Material Design styling."""

    apply_dark_mode()

    with ui.column().classes('w-full h-screen flex items-center justify-center'):
        with ui.card().classes('w-96 p-8 animate-fade-in-up'):
            # Logo
            with ui.column().classes('w-full items-center mb-6'):
                ui.element('img').props(f'src="{LOGO_DATA_URL}"').style('height: 120px; width: auto;')

            # Show timeout message if session expired
            if timeout == '1':
                with ui.card().classes('w-full mb-4 p-3 border-l-4 border-amber-500'):
                    ui.label('Session Expired').classes('font-semibold text-amber-600')
                    ui.label('You were logged out due to inactivity. Please log in again.').classes('text-sm opacity-70')

            # Username input
            username_input = ui.input(label='Username').classes('w-full mb-4')

            # Password input
            password_input = ui.input(label='Password', password=True).classes('w-full mb-4')

            # Error message area (hidden by default)
            error_message = ui.label('').classes('text-red-500 text-sm mb-4')
            error_message.set_visibility(False)

            # Login button (TJM Gold gradient)
            login_btn = ui.button('Login', on_click=lambda: authenticate(username_input, password_input, error_message, login_btn)).classes('w-full btn-gold mb-4')

            # Support Enter key to submit login form
            def handle_enter():
                authenticate(username_input, password_input, error_message, login_btn)
            username_input.on('keydown.enter', handle_enter)
            password_input.on('keydown.enter', handle_enter)

            # Forgot password link
            ui.button('Forgot Password?', on_click=lambda: ui.navigate.to('/forgot-password')).props('flat dense').classes('w-full text-sm')


def authenticate(username_input, password_input, error_message, login_btn):
    """Authenticate user credentials and handle login."""
    # Validate inputs with visual feedback
    valid = True
    if not validate_required(username_input, 'Username'):
        valid = False
    if not validate_required(password_input, 'Password'):
        valid = False

    if not valid:
        error_message.set_visibility(False)
        return

    # Get values from inputs
    username = username_input.value.strip()
    password = password_input.value

    # Check if user is locked out due to too many failed attempts
    is_locked, minutes_remaining = LoginRateLimiter.is_locked_out(username)
    if is_locked:
        error_message.text = f'Account temporarily locked. Try again in {minutes_remaining} minute(s).'
        error_message.set_visibility(True)
        return

    # Show loading state
    login_btn.props('loading disabled')

    # Get database session
    db = next(get_db())

    try:
        # Create user service and authenticate
        user_service = UserService(db)
        user = user_service.authenticate_user(username, password)

        if user:
            # Clear failed attempts on successful login
            LoginRateLimiter.record_successful_login(username)

            # Log successful login
            AuditService.log_login(db, user.id, user.username, success=True)

            # Run automatic year-end processing if needed (runs once per year)
            try:
                year_end_service = YearEndService(db)
                year_end_service.check_and_run_auto_processing()
            except Exception as e:
                # Don't block login if year-end processing fails
                pass

            # Store user in app storage and redirect
            app.storage.user['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'department_id': user.department_id,
                'is_trusted': user.is_trusted  # For trusted employee auto-approve features
            }
            ui.navigate.to('/dashboard')
        else:
            # Record failed attempt and check if now locked out
            attempts_remaining, is_now_locked = LoginRateLimiter.record_failed_attempt(username)

            # Log failed login attempt
            AuditService.log(db, action='login_failed', username=username,
                           details={'attempts_remaining': attempts_remaining, 'locked_out': is_now_locked})

            # Show appropriate error message
            if is_now_locked:
                error_message.text = f'Too many failed attempts. Account locked for {LoginRateLimiter.LOCKOUT_MINUTES} minutes.'
            elif attempts_remaining <= 2:
                error_message.text = f'Invalid credentials. {attempts_remaining} attempt(s) remaining.'
            else:
                error_message.text = 'Invalid credentials'
            error_message.set_visibility(True)
            login_btn.props(remove='loading disabled')

    except Exception as e:
        # Handle any database or service errors
        error_message.text = 'Login failed. Please try again.'
        error_message.set_visibility(True)
        login_btn.props(remove='loading disabled')
    finally:
        db.close()
