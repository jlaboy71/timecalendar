from nicegui import ui, app
from src.services.pto_service import PTOService
from src.database import get_db
from datetime import date


def request_form_page():
    """PTO request form page with form fields and submission handling."""

    # Check if user is logged in
    user = app.storage.general.get('user')
    if not user:
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full max-w-md mx-auto mt-8 p-6'):
        ui.label('Submit PTO Request').classes('text-2xl font-bold mb-6')

        # Form fields
        pto_type = ui.select(
            ['vacation', 'sick', 'personal', 'other'],
            label='PTO Type',
            value='vacation'
        ).classes('w-full mb-4')

        ui.label('Start Date').classes('text-sm font-medium mb-1')
        start_date = ui.date(value=date.today()).classes('w-full mb-4')

        ui.label('End Date').classes('text-sm font-medium mb-1')
        end_date = ui.date(value=date.today()).classes('w-full mb-4')

        half_day = ui.switch(
            'Half Day',
            value=False
        ).classes('mb-4')

        description = ui.textarea(
            label='Description (required for "other" type)',
            placeholder='Enter description...'
        ).classes('w-full mb-6')

        # Show/hide description based on PTO type
        def toggle_description():
            if pto_type.value == 'other':
                description.visible = True
            else:
                description.visible = False
                description.value = ''

        pto_type.on('update:model-value', toggle_description)
        toggle_description()  # Initial state

        # Buttons
        with ui.row().classes('w-full gap-4'):
            ui.button(
                'Submit Request',
                on_click=lambda: submit_request(
                    user['id'],
                    pto_type.value,
                    start_date.value,
                    end_date.value,
                    half_day.value,
                    description.value
                )
            ).classes('flex-1')

            ui.button(
                'Cancel',
                on_click=lambda: ui.navigate.to('/dashboard')
            ).classes('flex-1')


def submit_request(user_id, pto_type, start_date, end_date, half_day, description):
    """Submit PTO request with validation and database operations."""

    # Validate required fields
    if not start_date or not end_date:
        ui.notify('Start date and end date are required', type='negative')
        return

    if pto_type == 'other' and not description.strip():
        ui.notify('Description is required for "other" PTO type', type='negative')
        return

    if start_date > end_date:
        ui.notify('Start date cannot be after end date', type='negative')
        return

    db = None
    try:
        # Get database session
        db = next(get_db())

        # Create PTO service and submit request
        pto_service = PTOService(db)

        # Create request data
        from src.schemas.pto_schemas import PTORequestCreate
        request_data = PTORequestCreate(
            user_id=user_id,
            pto_type=pto_type,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            description=description if pto_type == 'other' else None
        )

        # Submit the request
        pto_service.create_request(request_data)

        # Success feedback
        ui.notify('PTO request submitted successfully!', type='positive')
        ui.navigate.to('/dashboard')

    except Exception as e:
        ui.notify(f'Error submitting request: {str(e)}', type='negative')

    finally:
        if db:
            db.close()
