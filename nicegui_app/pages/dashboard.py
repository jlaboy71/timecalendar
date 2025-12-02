from nicegui import ui, app


def dashboard_page():
    """Simple placeholder dashboard page."""
    
    # Check if user is logged in
    if not hasattr(app.storage, 'user') or not app.storage.user:
        ui.navigate.to('/')
        return
    
    # Get user's first name
    user_first_name = app.storage.user.get('first_name', 'User')
    
    with ui.card().classes('w-full max-w-md mx-auto mt-8'):
        ui.label(f'Welcome, {user_first_name}!').classes('text-2xl font-bold mb-4')
        ui.label('This is a placeholder dashboard. More features coming soon!').classes('text-gray-600 mb-4')
        
        def logout():
            """Clear user session and redirect to home."""
            if hasattr(app.storage, 'user'):
                delattr(app.storage, 'user')
            ui.navigate.to('/')
        
        ui.button('Logout', on_click=logout).classes('w-full')
