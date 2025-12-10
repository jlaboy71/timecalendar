"""
Export service for generating PDF and CSV reports.
"""
import csv
from io import BytesIO, StringIO
from datetime import date
from typing import List, Dict, Any

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class ExportService:
    """Service for generating export files."""

    @staticmethod
    def _get_logo_path() -> Path:
        """Get the path to the TJM logo."""
        return Path(__file__).parent.parent.parent / 'nicegui_app' / 'static' / 'TJMLogo.png'

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
    def generate_report_pdf(html_content: str, title: str = "Report") -> bytes:
        """
        Generate PDF from report HTML content.

        Args:
            html_content: HTML report content
            title: Report title

        Returns:
            PDF file as bytes
        """
        from bs4 import BeautifulSoup
        import re

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        elements = []

        # Parse HTML to extract content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Add TJM logo at the top (preserving aspect ratio 2.28:1)
        logo_path = ExportService._get_logo_path()
        if logo_path.exists():
            logo_width = 2 * inch
            logo_height = logo_width / 2.28
            logo = Image(str(logo_path), width=logo_width, height=logo_height)
            elements.append(logo)
            elements.append(Spacer(1, 10))

        # Title style
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Title'],
            fontSize=16,
            spaceAfter=6,
            textColor=colors.HexColor('#5A6A72')
        )
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=4
        )
        info_label_style = ParagraphStyle(
            'InfoLabel',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666')
        )
        info_value_style = ParagraphStyle(
            'InfoValue',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        )

        # Extract title from HTML if present
        title_elem = soup.find('h1') or soup.find('h2')
        report_title = title_elem.get_text() if title_elem else title
        elements.append(Paragraph(report_title, title_style))

        # Extract employee name and department from subtitle (in header)
        header_div = soup.find('div', style=lambda s: s and 'border-bottom' in s and 'C5A951' in s)
        if header_div:
            subtitle_div = header_div.find('div', style=lambda s: s and 'font-size: 14px' in s)
            if subtitle_div:
                elements.append(Paragraph(subtitle_div.get_text(strip=True), subtitle_style))

        elements.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Spacer(1, 15))

        # Extract employee info section (hire date, manager, location)
        info_section = soup.find('div', style=lambda s: s and 'background: #f8f9fa' in s)
        if info_section:
            info_items = info_section.find_all('div', recursive=False)
            if info_items:
                inner_flex = info_section.find('div', style=lambda s: s and 'display: flex' in s)
                if inner_flex:
                    info_data = []
                    for item in inner_flex.find_all('div', recursive=False):
                        label_span = item.find('span')
                        value_div = item.find('div')
                        if label_span and value_div:
                            info_data.append([label_span.get_text(strip=True), value_div.get_text(strip=True)])

                    if info_data:
                        info_table = Table(info_data, colWidths=[1.2*inch, 2*inch])
                        info_table.setStyle(TableStyle([
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ]))
                        elements.append(info_table)
                        elements.append(Spacer(1, 15))

        # Extract summary stats (the colored boxes with Approved Days, Pending Days, etc.)
        stat_boxes = soup.find_all('div', style=lambda s: s and 'border-left: 4px solid' in s and 'border-radius' in s)
        if stat_boxes:
            stat_data = []
            stat_values = []
            for box in stat_boxes:
                label_div = box.find('div', style=lambda s: s and 'font-size: 1' in s and 'color: #666' in s)
                value_div = box.find('div', style=lambda s: s and 'font-size: 24px' in s)
                if label_div and value_div:
                    stat_data.append(label_div.get_text(strip=True))
                    stat_values.append(value_div.get_text(strip=True))

            if stat_data:
                # Create a summary table
                summary_table = Table([stat_data, stat_values], colWidths=[1.8*inch] * len(stat_data))
                summary_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
                    ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, 1), 14),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#666666')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 20))

        # Find tables in HTML and convert to PDF tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if not rows:
                continue

            table_data = []
            for row in rows:
                cells = row.find_all(['th', 'td'])
                # Get text from each cell, preserving line breaks for approval info
                row_data = []
                for cell in cells:
                    # Get all text including nested divs (for approval info)
                    cell_text = ' '.join(cell.stripped_strings)
                    # Clean up multiple spaces
                    cell_text = re.sub(r'\s+', ' ', cell_text).strip()
                    row_data.append(cell_text)
                if row_data:
                    table_data.append(row_data)

            if table_data:
                # Calculate column widths based on number of columns
                num_cols = len(table_data[0]) if table_data else 1
                col_width = (7.5 * inch) / num_cols
                col_widths = [col_width] * num_cols

                pdf_table = Table(table_data, colWidths=col_widths)
                pdf_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5A6A72')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elements.append(pdf_table)
                elements.append(Spacer(1, 15))

        # If no tables found, try to extract text content
        if not tables:
            for p in soup.find_all(['p', 'div']):
                text = p.get_text(strip=True)
                if text:
                    elements.append(Paragraph(text, styles['Normal']))
                    elements.append(Spacer(1, 6))

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
