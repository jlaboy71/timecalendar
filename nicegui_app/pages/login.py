from nicegui import ui, app
from src.services.user_service import UserService
from src.database import get_db


def login_page():
    """Create a centered login page with Material Design styling."""
    
    with ui.column().classes('w-full h-screen flex items-center justify-center bg-gray-50'):
        with ui.card().classes('w-96 p-8'):
            ui.label('Login').classes('text-2xl font-bold text-center mb-6')
            
            # Username input
            username_input = ui.input('Username', placeholder='Enter your username').classes('w-full mb-4')
            
            # Password input
            password_input = ui.input('Password', placeholder='Enter your password', password=True).classes('w-full mb-4')
            
            # Error message area (hidden by default)
            error_message = ui.label('').classes('text-red-500 text-sm mb-4')
            error_message.set_visibility(False)
            
            # Login button
            ui.button('Login', on_click=lambda: authenticate(username_input, password_input, error_message)).classes('w-full bg-blue-500 text-white')


def authenticate(username_input, password_input, error_message):
    """Authenticate user credentials and handle login."""
    
    print("Attempting login...")
    
    # Get values from inputs
    username = username_input.value.strip()
    password = password_input.value
    
    print(f"Username: {username}, Password length: {len(password)}")
    
    # Validate inputs
    if not username or not password:
        error_message.text = 'Please enter both username and password'
        error_message.set_visibility(True)
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create user service and authenticate
        user_service = UserService(db)
        user = user_service.authenticate_user(username, password)
        
        if user:
            print("User authenticated successfully!")
            # Store user in app storage and redirect
            app.storage.general['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'department_id': user.department_id
            }
            ui.navigate.to('/dashboard')
        else:
            # Show error message
            error_message.text = 'Invalid credentials'
            error_message.set_visibility(True)
            
    except Exception as e:
        # Handle any database or service errors
        print(f"Authentication failed: {e}")
        error_message.text = 'Login failed. Please try again.'
        error_message.set_visibility(True)
    finally:
        db.close()
