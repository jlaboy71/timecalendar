from nicegui import ui, app
from src.services.balance_service import BalanceService
from src.services.pto_service import PTOService
from src.services.accrual_service import AccrualService
from src.services.user_service import UserService
from src.database import get_db
from datetime import datetime, date


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
    user_role = user_data.get('role')

    db = None
    try:
        # Get database session
        db = next(get_db())
        balance_service = BalanceService(db)
        pto_service = PTOService(db)
        accrual_service = AccrualService(db)
        user_service = UserService(db)

        # Get current user object for policy lookups
        current_user = user_service.get_user_by_id(user_id)
        
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
            
            with ui.row().classes('w-full gap-4 flex-wrap'):
                ui.button('Submit PTO Request', on_click=lambda: ui.navigate.to('/submit-request'), color='primary').classes('flex-1')
                ui.button('View Calendar', on_click=lambda: ui.navigate.to('/calendar'), color='secondary').classes('flex-1')
                ui.button('Request History', on_click=lambda: ui.navigate.to('/requests'), color='secondary').classes('flex-1')
                ui.button('Carryover Request', on_click=lambda: ui.navigate.to('/carryover'), color='secondary').classes('flex-1')

                # Add manager button if user has manager role
                if user_data.get('role') == 'manager':
                    ui.button('Manager Dashboard', on_click=lambda: ui.navigate.to('/manager'), color='accent').classes('flex-1')

                # Admin button (only for admin users)
                if user_role == 'admin':
                    ui.button('Admin Panel', on_click=lambda: ui.navigate.to('/admin'), color='red').classes('flex-1')
        
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

        # Section D: My Leave Policy (collapsible)
        with ui.expansion('My Leave Policy', icon='policy').classes('w-full mb-6'):
            if current_user:
                # Work Location
                with ui.row().classes('w-full mb-4'):
                    ui.icon('location_on').classes('text-gray-600')
                    location_text = ''
                    if current_user.location_city and current_user.location_state:
                        location_text = f'{current_user.location_city}, {current_user.location_state}'
                    elif current_user.location_state:
                        location_text = current_user.location_state
                    else:
                        location_text = 'Not Set'
                    ui.label(f'Work Location: {location_text}').classes('font-medium')

                if not current_user.location_state:
                    ui.label('Set your work location with HR to see your policy details').classes('text-amber-600 italic mb-4')
                else:
                    # Vacation Tier
                    with ui.card().classes('w-full mb-4 bg-blue-50'):
                        ui.label('Vacation').classes('font-semibold text-blue-800')
                        vacation_tier = accrual_service.get_vacation_tier(current_user)
                        years_of_service = accrual_service.get_years_of_service(current_user)

                        if vacation_tier:
                            tier_range = f'{vacation_tier.min_years_service}'
                            if vacation_tier.max_years_service:
                                tier_range += f'-{vacation_tier.max_years_service}'
                            else:
                                tier_range += '+'
                            ui.label(f'{vacation_tier.annual_days} days/year ({tier_range} years of service)').classes('text-sm')
                            ui.label(f'Your tenure: {years_of_service} years').classes('text-sm text-gray-600')
                        else:
                            ui.label('Vacation tier not found').classes('text-sm text-gray-600')

                        # Vacation carryover
                        vacation_policy = accrual_service.get_policy_for_employee(current_user, 'VACATION')
                        if vacation_policy:
                            if vacation_policy.max_carryover_hours and float(vacation_policy.max_carryover_hours) > 0:
                                ui.label(f'Carryover: Up to {vacation_policy.max_carryover_hours} hrs').classes('text-sm')
                            else:
                                ui.label('Carryover: None (manager approval required)').classes('text-sm text-amber-700')

                    # Sick Time
                    with ui.card().classes('w-full mb-4 bg-green-50'):
                        ui.label('Sick Time').classes('font-semibold text-green-800')
                        sick_policy = accrual_service.get_policy_for_employee(current_user, 'SICK')

                        if sick_policy:
                            if sick_policy.accrual_hours_divisor:
                                ui.label(f'Accrual: 1 hr per {sick_policy.accrual_hours_divisor} hrs worked').classes('text-sm')
                            if sick_policy.max_annual_hours:
                                ui.label(f'Annual max: {sick_policy.max_annual_hours} hrs').classes('text-sm')
                            if sick_policy.max_carryover_hours:
                                ui.label(f'Carryover: Up to {sick_policy.max_carryover_hours} hrs').classes('text-sm')
                            if sick_policy.waiting_period_days and sick_policy.waiting_period_days > 0:
                                ui.label(f'Waiting period: {sick_policy.waiting_period_days} days').classes('text-sm text-gray-600')
                        else:
                            ui.label('No sick time policy found for your location').classes('text-sm text-gray-600')

                    # Personal Days
                    with ui.card().classes('w-full mb-4 bg-purple-50'):
                        ui.label('Personal Days').classes('font-semibold text-purple-800')
                        personal_policy = accrual_service.get_policy_for_employee(current_user, 'PERSONAL')

                        if personal_policy:
                            if personal_policy.max_annual_hours:
                                days = float(personal_policy.max_annual_hours) / 8
                                ui.label(f'Annual allowance: {int(days)} days ({personal_policy.max_annual_hours} hrs)').classes('text-sm')
                            if personal_policy.min_increment_hours:
                                ui.label(f'Minimum request: {personal_policy.min_increment_hours} hrs').classes('text-sm')
                        else:
                            ui.label('No personal day policy found').classes('text-sm text-gray-600')
            else:
                ui.label('Unable to load user information').classes('text-red-600')

        # Logout button
        def logout():
            """Clear user session and redirect to home."""
            app.storage.general.pop('user', None)
            ui.navigate.to('/')
        
        ui.button('Logout', on_click=logout).classes('w-full max-w-xs')
        
    finally:
        if db:
            db.close()
