"""Email template preview page for admins."""
from nicegui import ui, app
from nicegui_app.components.header import page_header, go_back
from src.services.email_service import _get_email_template, _get_pto_type_icon, _format_date_range_with_days
from datetime import date, timedelta


def email_preview_page():
    """Preview all email templates with sample data."""
    user = app.storage.user.get('user')
    if not user:
        ui.navigate.to('/')
        return

    user_role = user.get('role', 'employee')
    if user_role not in ['admin', 'superadmin']:
        ui.navigate.to('/dashboard')
        return

    page_header(title='Email Template Preview', show_back=False)

    # Sample data for previews
    sample_employee = "John Smith"
    sample_manager = "Jane Doe"
    sample_pto_type = "Vacation"
    sample_start = date.today() + timedelta(days=7)
    sample_end = date.today() + timedelta(days=10)
    sample_days = 4.0

    # Email type selector - clear labels showing recipient
    email_types = {
        'submitted': 'EMP: REQUEST SUBMITTED',
        'approved': 'EMP: REQUEST APPROVED',
        'denied': 'EMP: REQUEST DENIED',
        'pending': 'MAN: REQUEST ARRIVED',
        'cancelled': 'MAN: PTO CANCELLED',
        'report': 'ADMIN: REPORT EMAIL'
    }

    selected_type = {'value': 'approved'}
    preview_container = ui.element('div').classes('w-full')

    def generate_preview(email_type: str) -> str:
        """Generate HTML preview for the selected email type."""
        days_display = str(int(sample_days)) if sample_days == int(sample_days) else f"{sample_days:.1f}"
        date_range = _format_date_range_with_days(sample_start, sample_end)
        pto_icon = _get_pto_type_icon('vacation')

        if email_type == 'submitted':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
            <p style="margin-bottom: 25px;">Your time off request has been submitted and is <span style="color: #f59e0b; font-weight: 600;">pending approval</span>.</p>

            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <table style="width: 100%; color: #e5e7eb;">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td>
                    </tr>
                </table>
            </div>
            """
            return _get_email_template(
                title="Request Submitted",
                title_color="#f59e0b",
                content=content,
                footer_text="You will receive another email once your request has been reviewed."
            )

        elif email_type == 'approved':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
            <p style="margin-bottom: 25px;">Great news! Your time off request has been <span style="color: #22c55e; font-weight: 600;">approved</span>.</p>

            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #22c55e;">
                <table style="width: 100%; color: #e5e7eb;">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #22c55e;">{days_display}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Approved by:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{sample_manager}</td>
                    </tr>
                </table>
            </div>
            """
            return _get_email_template(
                title="Request Approved",
                title_color="#22c55e",
                content=content,
                footer_text="Enjoy your time off!"
            )

        elif email_type == 'denied':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_employee},</p>
            <p style="margin-bottom: 25px;">Unfortunately, your time off request has been <span style="color: #ef4444; font-weight: 600;">denied</span>.</p>

            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
                <table style="width: 100%; color: #e5e7eb;">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{days_display}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Reviewed by:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{sample_manager}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af; vertical-align: top;">Reason:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #fca5a5;">Team coverage needed during this period.</td>
                    </tr>
                </table>
            </div>
            """
            return _get_email_template(
                title="Request Denied",
                title_color="#ef4444",
                content=content,
                footer_text="If you have questions, please speak with your manager."
            )

        elif email_type == 'pending':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_manager},</p>
            <p style="margin-bottom: 25px;">A new time off request requires your review.</p>

            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <table style="width: 100%; color: #e5e7eb;">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Employee:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{sample_employee}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #f59e0b;">{days_display}</td>
                    </tr>
                </table>
            </div>
            """
            return _get_email_template(
                title="New Request Pending",
                title_color="#f59e0b",
                content=content,
                footer_text="Please log in to PTO Central to approve or deny this request."
            )

        elif email_type == 'cancelled':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Hi {sample_manager},</p>
            <p style="margin-bottom: 25px;">An employee has <span style="color: #ef4444; font-weight: 600;">cancelled</span> their previously approved time off.</p>

            <div style="background-color: #374151; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
                <table style="width: 100%; color: #e5e7eb;">
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Employee:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #C9A227;">{sample_employee}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Type:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{pto_icon} {sample_pto_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Dates:</td>
                        <td style="padding: 8px 0; font-weight: 600;">{date_range}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #9ca3af;">Total Days:</td>
                        <td style="padding: 8px 0; font-weight: 600; color: #ef4444;">{days_display}</td>
                    </tr>
                </table>
            </div>
            """
            return _get_email_template(
                title="Approved PTO Cancelled",
                title_color="#ef4444",
                content=content,
                footer_text="The employee's PTO balance has been restored automatically."
            )

        elif email_type == 'report':
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px; color: #e5e7eb;">Please find the report below:</p>
            <div style="background-color: #374151; padding: 15px; border-radius: 8px; border-left: 4px solid #C9A227; margin-bottom: 20px;">
                <p style="margin: 0; color: #e5e7eb; font-style: italic;">Here is the monthly PTO summary you requested.</p>
            </div>
            <div style="background-color: #374151; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <p style="color: #e5e7eb; margin: 0;">Sample report content would appear here...</p>
            </div>
            """
            return _get_email_template(
                title="Report",
                title_color="#C9A227",
                content=content
            )

        return ""

    def render_preview():
        """Render the preview based on selected type."""
        preview_container.clear()
        with preview_container:
            html_content = generate_preview(selected_type['value'])

            # Edge-to-edge iframe preview
            ui.html(f'''
                <iframe
                    srcdoc="{html_content.replace('"', '&quot;')}"
                    style="width: 100%; height: 650px; border: none; background: #111827;"
                ></iframe>
            ''', sanitize=False)

    # Email type buttons - edge to edge, larger
    with ui.row().classes('w-full gap-3 mb-4'):
        for key, label in email_types.items():
            def make_handler(k=key):
                def handler():
                    selected_type['value'] = k
                    render_preview()
                return handler

            # Color code the buttons
            colors = {
                'submitted': '#f59e0b',
                'approved': '#22c55e',
                'denied': '#ef4444',
                'pending': '#f59e0b',
                'cancelled': '#ef4444',
                'report': '#C9A227'
            }
            color = colors.get(key, '#6b7280')
            ui.button(
                label,
                on_click=make_handler()
            ).props('outline').classes('flex-1').style(f'border-color: {color}; color: {color}; font-size: 12px; padding: 10px 6px; font-weight: 600;')

    # Initial preview
    render_preview()

    # Back button - gold theme color
    ui.button('Back', on_click=go_back).props('outline').classes('mt-4').style('border-color: #C9A227 !important; color: #C9A227 !important;')
