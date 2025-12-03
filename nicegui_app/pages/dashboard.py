from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.database import get_db
from datetime import datetime


def dashboard_page():
    """Employee dashboard page with PTO balances, quick actions, and recent requests."""
    
    # Check if user is logged in
    if not app.storage.general.get('user'):
        ui.navigate.to('/')
        return
    
    # Get user info
    user_data = app.storage.general.get('user')
    user_first_name = user_data.get('first_name', 'User')
    user_id = user_data.get('id')
    
    db = None
    try:
        # Get database session
        db = next(get_db())
        balance_service = BalanceService(db)
        pto_service = PTOService(db)
        
        # Get user's current PTO balances for 2025
        balance = balance_service.get_or_create_balance(user_id, 2025)
        
        # Get user's recent requests (last 5)
        recent_requests = PTOService.get_user_requests(db, user_id)[:5]
        
        ui.label(f'Welcome, {user_first_name}!').classes('text-3xl font-bold mb-6')
        
        # Section A: PTO Balances
        with ui.card().classes('w-full mb-6'):
            ui.label('PTO Balances (2025)').classes('text-xl font-semibold mb-4')
            
            if balance:
                with ui.row().classes('w-full gap-4'):
                    # Vacation balance
                    with ui.column().classes('flex-1'):
                        ui.label('Vacation').classes('font-medium')
                        vacation_available = float(balance.vacation_available)
                        vacation_total = float(balance.vacation_total)
                        vacation_pct = vacation_available / vacation_total if vacation_total > 0 else 0
                        
                        ui.label(f'{vacation_available} available of {vacation_total} total')
                        
                        color = 'positive' if vacation_pct > 0.5 else 'warning' if vacation_pct > 0.25 else 'negative'
                        ui.linear_progress(vacation_pct, color=color).classes('w-full')
                    
                    # Sick balance
                    with ui.column().classes('flex-1'):
                        ui.label('Sick').classes('font-medium')
                        sick_available = float(balance.sick_available)
                        sick_total = float(balance.sick_total)
                        sick_pct = sick_available / sick_total if sick_total > 0 else 0
                        
                        ui.label(f'{sick_available} available of {sick_total} total')
                        
                        color = 'positive' if sick_pct > 0.5 else 'warning' if sick_pct > 0.25 else 'negative'
                        ui.linear_progress(sick_pct, color=color).classes('w-full')
                    
                    # Personal balance
                    with ui.column().classes('flex-1'):
                        ui.label('Personal').classes('font-medium')
                        personal_available = float(balance.personal_available)
                        personal_total = float(balance.personal_total)
                        personal_pct = personal_available / personal_total if personal_total > 0 else 0
                        
                        ui.label(f'{personal_available} available of {personal_total} total')
                        
                        color = 'positive' if personal_pct > 0.5 else 'warning' if personal_pct > 0.25 else 'negative'
                        ui.linear_progress(personal_pct, color=color).classes('w-full')
            else:
                ui.label('No balance data for 2025').classes('text-gray-600')
        
        # Section B: Quick Actions
        with ui.card().classes('w-full mb-6'):
            ui.label('Quick Actions').classes('text-xl font-semibold mb-4')
            
            with ui.row().classes('w-full gap-4'):
                ui.button('Submit PTO Request', on_click=lambda: ui.navigate.to('/submit-request'), color='primary').classes('flex-1')
                ui.button('View Calendar', on_click=lambda: ui.navigate.to('/calendar'), color='secondary').classes('flex-1')
                ui.button('Request History', on_click=lambda: ui.navigate.to('/requests'), color='secondary').classes('flex-1')
                
                # Add manager button if user has manager role
                if user_data.get('role') == 'manager':
                    ui.button('Manager Dashboard', on_click=lambda: ui.navigate.to('/manager'), color='accent').classes('flex-1')
        
        # Section C: Recent Requests
        with ui.card().classes('w-full mb-6'):
            ui.label('Recent Requests').classes('text-xl font-semibold mb-4')
            
            if recent_requests:
                columns = [
                    {'name': 'date', 'label': 'Date', 'field': 'start_date'},
                    {'name': 'type', 'label': 'Type', 'field': 'pto_type'},
                    {'name': 'days', 'label': 'Days', 'field': 'duration_days'},
                    {'name': 'status', 'label': 'Status', 'field': 'status'}
                ]
                
                rows = []
                for request in recent_requests:
                    rows.append({
                        'start_date': request.start_date.strftime('%m/%d/%Y'),
                        'pto_type': request.pto_type.title(),
                        'duration_days': request.duration_days,
                        'status': request.status.title()
                    })
                
                ui.table(columns=columns, rows=rows).classes('w-full')
            else:
                ui.label('No recent requests').classes('text-gray-600')
        
        # Logout button
        def logout():
            """Clear user session and redirect to home."""
            app.storage.general.pop('user', None)
            ui.navigate.to('/')
        
        ui.button('Logout', on_click=logout).classes('w-full max-w-xs')
        
    finally:
        if db:
            db.close()
