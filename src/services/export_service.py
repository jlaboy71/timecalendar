"""
Export service for generating PDF and CSV reports.
"""
import csv
from io import BytesIO, StringIO
from datetime import date
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class ExportService:
    """Service for generating export files."""

    @staticmethod
    def generate_analytics_pdf(
        overview: Dict,
        recommendations: List[Dict],
        carryover_risk: List[Dict],
        optimal_dates: List[Dict],
        title: str = "Workforce Analytics Report"
    ) -> bytes:
        """
        Generate PDF analytics report.

        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=12
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6
        )

        # Title
        elements.append(Paragraph("TJM Holdings - Workforce Analytics Report", title_style))
        elements.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Key Metrics
        elements.append(Paragraph("Key Metrics", heading_style))
        metrics_data = [
            ['Metric', 'Value'],
            ['Total Requests', str(overview.get('total_requests', 0))],
            ['Approved', str(overview.get('approved', 0))],
            ['Pending', str(overview.get('pending', 0))],
            ['Days Taken', str(overview.get('total_days_taken', 0))],
            ['Avg Days/Employee', str(overview.get('avg_days_per_employee', 0))],
            ['Active Employees', str(overview.get('active_employees', 0))],
            ['Approval Rate', f"{overview.get('approval_rate', 0)}%"],
        ]

        metrics_table = Table(metrics_data, colWidths=[200, 150])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        # Optimal Meeting Dates
        if optimal_dates:
            elements.append(Paragraph("Recommended All-Hands Meeting Dates", heading_style))
            for meeting in optimal_dates[:5]:
                elements.append(Paragraph(
                    f"  {meeting.get('date_str', '')} ({meeting.get('day_of_week', '')}) - "
                    f"{meeting.get('expected_attendance', 0):.0f}% expected attendance",
                    styles['Normal']
                ))
            elements.append(Spacer(1, 15))

        # Recommendations
        if recommendations:
            elements.append(Paragraph("Recommendations", heading_style))
            for rec in recommendations:
                priority_color = {
                    'HIGH': colors.red,
                    'MEDIUM': colors.orange,
                    'LOW': colors.blue,
                    'INFO': colors.green
                }.get(rec.get('priority', ''), colors.grey)

                elements.append(Paragraph(
                    f"[{rec.get('priority', '')}] {rec.get('title', '')}",
                    ParagraphStyle('RecTitle', parent=styles['Normal'], textColor=priority_color, fontName='Helvetica-Bold')
                ))
                elements.append(Paragraph(f"  Action: {rec.get('action', '')}", styles['Normal']))
                if rec.get('affected'):
                    elements.append(Paragraph(
                        f"  Affected: {', '.join(rec['affected'][:3])}",
                        ParagraphStyle('RecAffected', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
                    ))
                elements.append(Spacer(1, 8))
            elements.append(Spacer(1, 15))

        # Carryover Risk
        if carryover_risk:
            elements.append(Paragraph("Employees at Carryover Risk", heading_style))
            risk_data = [['Employee', 'Department', 'Remaining', 'Total', 'Risk']]
            for emp in carryover_risk[:15]:
                risk_data.append([
                    emp.get('name', ''),
                    emp.get('department', ''),
                    f"{emp.get('vacation_remaining', 0)} days",
                    f"{emp.get('vacation_total', 0)} days",
                    emp.get('risk_level', '')
                ])

            risk_table = Table(risk_data, colWidths=[120, 100, 70, 70, 60])
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A5F')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')])
            ]))
            elements.append(risk_table)

        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "TJM Time Calendar - Confidential",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
        ))

        doc.build(elements)
        return buffer.getvalue()

    @staticmethod
    def generate_csv(data: List[Dict], columns: List[str]) -> str:
        """
        Generate CSV string from data.

        Args:
            data: List of dictionaries
            columns: List of column keys to include

        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(columns)

        # Data rows
        for row in data:
            writer.writerow([row.get(col, '') for col in columns])

        return output.getvalue()

    @staticmethod
    def generate_carryover_csv(carryover_risk: List[Dict]) -> str:
        """Generate CSV for carryover risk employees."""
        columns = ['name', 'department', 'vacation_remaining', 'vacation_total', 'pct_remaining', 'risk_level']
        return ExportService.generate_csv(carryover_risk, columns)

    @staticmethod
    def generate_department_csv(dept_data: List[Dict]) -> str:
        """Generate CSV for department comparison."""
        columns = ['department_name', 'employee_count', 'total_requests', 'total_days', 'avg_days_per_employee']
        return ExportService.generate_csv(dept_data, columns)
