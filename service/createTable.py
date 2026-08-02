"""
PDF Table Generation Service using ReportLab
Generates formatted PDF tables from CSV data with merged cells for repeated first column values
"""

import csv
import os
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def read_csv_data(csv_file_path):
    """Read CSV file and return headers and rows"""
    try:
        data = []
        headers = []
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)
            for row in reader:
                data.append(row)
        
        logger.info(f"✓ Read CSV file: {csv_file_path} ({len(data)} rows, {len(headers)} columns)")
        return headers, data
    except Exception as e:
        logger.error(f"❌ Error reading CSV: {str(e)}")
        return [], []


def merge_cells_for_column(headers, data, merge_column_index=0):
    """
    Merge cells in the specified column (can be any column, not just first)
    Returns data with merge information and merged row indices
    """
    merged_rows = []
    merge_info = {}  # {row_index: merge_span}
    
    if not data:
        return data, merge_info
    
    i = 0
    while i < len(data):
        current_value = data[i][merge_column_index] if merge_column_index < len(data[i]) else ""
        merge_start = i
        
        # Find how many consecutive rows have the same value in the specified column
        j = i + 1
        while j < len(data):
            next_value = data[j][merge_column_index] if merge_column_index < len(data[j]) else ""
            if next_value == current_value:
                j += 1
            else:
                break
        
        # Record merge span for the column
        merge_span = j - i
        if merge_span > 1:
            merge_info[merge_start] = merge_span
        
        i = j
    
    return data, merge_info


def create_table_pdf(csv_file_path, pdf_output_path, grouping_column_name=None):
    """
    Generate a PDF table from CSV file with merged cells for specified grouping column
    
    Args:
        csv_file_path: Path to input CSV file
        pdf_output_path: Path where PDF will be saved
        grouping_column_name: Column name to use for cell merging (e.g., 'Teacher', 'Staff', 'Room')
                             If None, uses first column
    
    Returns:
        Path to generated PDF file or None if failed
    """
    try:
        logger.info(f"📄 Starting PDF generation from: {csv_file_path}")
        
        # Read CSV data
        headers, data = read_csv_data(csv_file_path)
        
        if not headers or not data:
            logger.error("❌ No data to generate PDF")
            return None
        
        # --- Date formatting (YYYY-MM-DD -> DD/MM/YYYY) and ascending sort ---
        # Find date column (case-insensitive)
        date_col_idx = -1
        shift_col_idx = -1
        group_col_idx = -1
        for idx, h in enumerate(headers):
            if h.strip().lower() == 'date':
                date_col_idx = idx
            if h.strip().lower() == 'shift':
                shift_col_idx = idx
            if grouping_column_name and h.strip().lower() == grouping_column_name.lower():
                group_col_idx = idx

        if date_col_idx != -1:
            # Sort: if grouping column exists, sort by group first, then date; otherwise just by date
            def _sort_key(row):
                raw = row[date_col_idx]
                try:
                    dt = datetime.strptime(raw, '%Y-%m-%d')
                except Exception:
                    try:
                        dt = datetime.strptime(raw, '%d/%m/%Y')
                    except Exception:
                        dt = datetime.max
                shift_order = 0
                if shift_col_idx != -1:
                    shift_order = 0 if row[shift_col_idx].strip().lower() == 'morning' else 1
                
                if group_col_idx != -1:
                    return (row[group_col_idx], dt, shift_order)
                return (dt, shift_order)

            data.sort(key=_sort_key)

            # Convert date strings to DD/MM/YYYY
            for row in data:
                raw = row[date_col_idx]
                try:
                    dt = datetime.strptime(raw, '%Y-%m-%d')
                    row[date_col_idx] = dt.strftime('%d/%m/%Y')
                except Exception:
                    pass  # already formatted or unknown format, leave as-is

            logger.info("✓ Dates formatted to DD/MM/YYYY and sorted ascending")
        
        # Determine which column to merge on
        merge_column_index = 0
        if grouping_column_name:
            try:
                merge_column_index = headers.index(grouping_column_name)
                logger.info(f"✓ Using column '{grouping_column_name}' (index {merge_column_index}) for merging")
            except ValueError:
                logger.warning(f"⚠️ Column '{grouping_column_name}' not found, using first column")
                merge_column_index = 0
        
        # Merge cells for specified column
        data, merge_info = merge_cells_for_column(headers, data, merge_column_index=merge_column_index)
        
        # Create table data with headers
        table_data = [headers] + data
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_output_path,
            pagesize=landscape(letter),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f497d'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Create story (elements to add to PDF)
        story = []
        
        # Add title
        title = "Schedule Report"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Calculate proportional column widths
        max_lengths = [len(str(h)) for h in headers]
        for row in data:
            for i, cell in enumerate(row):
                if i < len(max_lengths):
                    max_lengths[i] = max(max_lengths[i], len(str(cell)))
                    
        total_len = sum(max_lengths)
        available_width = 10.0 * inch  # 11 inches landscape - 2 * 0.5 inch margins
        
        col_widths = []
        for ml in max_lengths:
            # allocate proportionally, but ensure a minimum width
            cw = max(0.8 * inch, (ml / total_len) * available_width)
            col_widths.append(cw)
            
        # normalize to exactly available_width
        sum_cw = sum(col_widths)
        if sum_cw > 0:
            col_widths = [cw * (available_width / sum_cw) for cw in col_widths]
        
        # Define Paragraph styles for text wrapping
        header_pstyle = ParagraphStyle(
            'HeaderP',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.whitesmoke,
            alignment=TA_CENTER
        )
        
        data_pstyle = ParagraphStyle(
            'DataP',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            alignment=TA_LEFT
        )
        
        data_center_pstyle = ParagraphStyle(
            'DataCenterP',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            alignment=TA_CENTER
        )

        # Apply table styling
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f497d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 1), (-1, -1), 6),
            ('RIGHTPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#1f497d')),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.HexColor('#1f497d')),
        ]

        # Apply vertical merges for specified column (merge cells with same values)
        current_row = 1  # Start after header
        while current_row < len(table_data):
            if current_row - 1 in merge_info:
                merge_span = merge_info[current_row - 1]
                if merge_span > 1:
                    # Add merge command for specified column
                    table_style.append(
                        ('VALIGN', (merge_column_index, current_row), (merge_column_index, current_row + merge_span - 1), 'MIDDLE')
                    )
                    table_style.append(
                        ('ALIGN', (merge_column_index, current_row), (merge_column_index, current_row + merge_span - 1), 'CENTER')
                    )
                    
                    # Merge cells by clearing duplicate values
                    for i in range(1, merge_span):
                        table_data[current_row + i][merge_column_index] = ""
                
                current_row += merge_span
            else:
                current_row += 1
        
        # Convert text to Paragraphs for auto-wrapping
        formatted_table_data = []
        for r_idx, row in enumerate(table_data):
            formatted_row = []
            for c_idx, cell in enumerate(row):
                if cell == "":
                    formatted_row.append("")
                elif r_idx == 0:
                    formatted_row.append(Paragraph(str(cell), header_pstyle))
                else:
                    style = data_center_pstyle if c_idx == merge_column_index else data_pstyle
                    formatted_row.append(Paragraph(str(cell), style))
            formatted_table_data.append(formatted_row)
        
        # Rebuild table with merged and wrapped data
        table = Table(formatted_table_data, colWidths=col_widths)
        table.setStyle(TableStyle(table_style))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"✓ PDF generated successfully: {pdf_output_path}")
        return pdf_output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating PDF: {str(e)}")
        return None


def create_room_tables_pdf(csv_file_path, pdf_output_path):
    """
    Generate a PDF with separate tables for each room from the room schedule CSV
    
    Args:
        csv_file_path: Path to room schedule CSV file
        pdf_output_path: Path where PDF will be saved
        
    Returns:
        Path to generated PDF file or None if failed
    """
    try:
        logger.info(f"📄 Creating room-specific PDF from: {csv_file_path}")
        
        # Read CSV data
        headers, data = read_csv_data(csv_file_path)
        
        if not headers or not data:
            logger.error("❌ No data to generate PDF")
            return None
        
        # Group data by room
        rooms_data = {}
        for row in data:
            # Find room column (usually index 1, but let's be safe)
            room_idx = -1
            for idx, h in enumerate(headers):
                if h.strip().lower() == 'room':
                    room_idx = idx
                    break
            
            if room_idx >= 0 and room_idx < len(row):
                room_name = row[room_idx]
                if room_name not in rooms_data:
                    rooms_data[room_name] = []
                rooms_data[room_name].append(row)
        
        # Sort data by date within each room
        date_col_idx = -1
        shift_col_idx = -1
        for idx, h in enumerate(headers):
            if h.strip().lower() == 'date':
                date_col_idx = idx
            if h.strip().lower() == 'shift':
                shift_col_idx = idx
        
        for room in rooms_data:
            if date_col_idx != -1:
                def _sort_key(row):
                    raw = row[date_col_idx] if date_col_idx < len(row) else ""
                    try:
                        dt = datetime.strptime(raw, '%Y-%m-%d')
                    except Exception:
                        try:
                            dt = datetime.strptime(raw, '%d/%m/%Y')
                        except Exception:
                            dt = datetime.max
                    shift_order = 0
                    if shift_col_idx != -1 and shift_col_idx < len(row):
                        shift_order = 0 if row[shift_col_idx].strip().lower() == 'morning' else 1
                    return (dt, shift_order)
                
                rooms_data[room].sort(key=_sort_key)
                
                # Convert date format
                for row in rooms_data[room]:
                    if date_col_idx < len(row):
                        raw = row[date_col_idx]
                        try:
                            dt = datetime.strptime(raw, '%Y-%m-%d')
                            row[date_col_idx] = dt.strftime('%d/%m/%Y')
                        except Exception:
                            pass
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_output_path,
            pagesize=landscape(letter),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f497d'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        room_style = ParagraphStyle(
            'RoomTitle',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#2e5090'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        # Create story (elements to add to PDF)
        story = []
        
        # Add main title
        title = "Room Schedule Report"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Calculate proportional column widths
        num_cols = len(headers)
        max_lengths = [len(str(h)) for h in headers]
        for room_name in rooms_data:
            for row in rooms_data[room_name]:
                for i, cell in enumerate(row):
                    if i < len(max_lengths):
                        max_lengths[i] = max(max_lengths[i], len(str(cell)))
                        
        total_len = sum(max_lengths)
        available_width = 10.0 * inch  # 11 inches landscape - 2 * 0.5 inch margins
        
        col_widths = []
        for ml in max_lengths:
            cw = max(0.8 * inch, (ml / total_len) * available_width)
            col_widths.append(cw)
            
        sum_cw = sum(col_widths)
        if sum_cw > 0:
            col_widths = [cw * (available_width / sum_cw) for cw in col_widths]
            
        # Define Paragraph styles
        header_pstyle = ParagraphStyle(
            'HeaderP',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.whitesmoke,
            alignment=TA_CENTER
        )
        
        data_pstyle = ParagraphStyle(
            'DataP',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            alignment=TA_LEFT
        )
        
        # Create table for each room
        for room_name in sorted(rooms_data.keys()):
            room_table_data = [headers] + rooms_data[room_name]
            
            # Convert text to Paragraphs for auto-wrapping
            formatted_table_data = []
            for r_idx, row in enumerate(room_table_data):
                formatted_row = []
                for cell in row:
                    if cell == "":
                        formatted_row.append("")
                    elif r_idx == 0:
                        formatted_row.append(Paragraph(str(cell), header_pstyle))
                    else:
                        formatted_row.append(Paragraph(str(cell), data_pstyle))
                formatted_table_data.append(formatted_row)
            
            # Create table
            table = Table(formatted_table_data, colWidths=col_widths)
            
            # Apply table styling
            table_style = [
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f497d')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Data row styling
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('LEFTPADDING', (0, 1), (-1, -1), 4),
                ('RIGHTPADDING', (0, 1), (-1, -1), 4),
                
                # Alternate row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                
                # Grid lines
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#1f497d')),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.HexColor('#1f497d')),
            ]
            
            table.setStyle(TableStyle(table_style))
            
            # Add room title
            story.append(Paragraph(f"Room: {room_name}", room_style))
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"✓ PDF generated successfully with {len(rooms_data)} room(s): {pdf_output_path}")
        return pdf_output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating room PDF: {str(e)}")
        return None


def create_all_schedules_pdf(csv_dir, pdf_output_dir):
    """
    Generate PDFs for all schedule CSV files in a directory
    
    Args:
        csv_dir: Directory containing CSV files
        pdf_output_dir: Directory where PDFs will be saved
    
    Returns:
        Dictionary of {csv_filename: pdf_path}
    """
    try:
        if not os.path.exists(pdf_output_dir):
            os.makedirs(pdf_output_dir)
        
        pdf_paths = {}
        
        # Expected CSV files
        csv_files = [
            'exam_schedule.csv',
            'teacher_schedule.csv',
            'staff_schedule.csv',
            'room_schedule.csv'
        ]
        
        for csv_file in csv_files:
            csv_path = os.path.join(csv_dir, csv_file)
            if os.path.exists(csv_path):
                pdf_name = csv_file.replace('.csv', '.pdf')
                pdf_path = os.path.join(pdf_output_dir, pdf_name)
                
                result = create_table_pdf(csv_path, pdf_path)
                if result:
                    pdf_paths[csv_file] = result
                    logger.info(f"✓ Generated PDF: {pdf_name}")
        
        return pdf_paths
        
    except Exception as e:
        logger.error(f"❌ Error creating all PDFs: {str(e)}")
        return {}


def create_personnel_report_pdf(csv_file_path, pdf_output_path, is_staff=False):
    """
    Generate a custom PDF report for personnel (teachers or staff) from the schedule CSV.
    Shows each person, total duties, and a table of their assignments (Date, Shift, Room).
    """
    try:
        report_title = "Staff Invigilation Report" if is_staff else "Faculty Invigilation Report"
        label = "Staff" if is_staff else "Faculty"
        logger.info(f"📄 Starting {label} PDF generation from: {csv_file_path}")
        
        headers, data = read_csv_data(csv_file_path)
        if not headers or not data:
            logger.error("❌ No data to generate PDF")
            return None
            
        # Extract indices
        try:
            d_idx = headers.index('Date')
            s_idx = headers.index('Shift')
            r_idx = headers.index('Room')
            
            # Faculty CSV now has 'Teacher' column; Staff CSV has 'Staff' column
            p_col = 'Staff' if is_staff else 'Teacher'
            if p_col not in headers:
                # Fallback: try the old Faculty1 column for legacy CSVs
                if not is_staff and 'Faculty1' in headers:
                    p_col = 'Faculty1'
                elif is_staff and 'Staff1' in headers:
                    p_col = 'Staff1'
                else:
                    logger.error(f"❌ Column '{p_col}' not found in CSV headers: {headers}")
                    return None
            p_idx = headers.index(p_col)
        except ValueError as e:
            logger.error(f"❌ Missing expected column in CSV: {str(e)}")
            return None
            
        personnel_map = {}
        for row in data:
            person = row[p_idx] if p_idx < len(row) else None
                
            if not person or person == 'N/A' or person == '---':
                continue
                
            # Date Formatting (YYYY-MM-DD -> DD/MM/YYYY) and sorting preservation
            raw_date = row[d_idx]
            sort_key = raw_date
            try:
                dt_obj = datetime.strptime(raw_date, '%Y-%m-%d')
                fmt_date = dt_obj.strftime('%d/%m/%Y')
                sort_key = dt_obj # Sort by actual precise datetime
            except Exception:
                fmt_date = raw_date
                
            if person not in personnel_map:
                personnel_map[person] = []
            personnel_map[person].append({
                'date': fmt_date,
                'shift': row[s_idx],
                'room': row[r_idx],
                'sort_key': sort_key
            })
            
        doc = SimpleDocTemplate(
            pdf_output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f497d'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        teacher_name_style = ParagraphStyle(
            'PersonName',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceBefore=15,
            spaceAfter=5,
            fontName='Helvetica-Bold'
        )
        
        duties_style = ParagraphStyle(
            'DutiesStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#e74c3c'),
            spaceAfter=10,
            fontName='Helvetica-Oblique'
        )
        
        story = []
        
        story.append(Paragraph(report_title, title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Sort personnel alphabetically
        for person in sorted(personnel_map.keys()):
            assignments = personnel_map[person]
            
            # Sort appointments ascending by date object, then shift
            assignments.sort(key=lambda x: (x['sort_key'], x['shift']))
            
            person_block = []
            
            # Print Person Name and Duty Count
            person_block.append(Paragraph(f"{label}: {person}", teacher_name_style))
            person_block.append(Paragraph(f"Total Assigned Duties: {len(assignments)}", duties_style))
            
            # Calculate column widths based on max content length
            # We have 7 inches of available width (8.5 - 1.5 margins)
            available_width = 7.0 * inch
            max_lengths = [4, 5, 4] # "Date", "Shift", "Room"
            for asn in assignments:
                max_lengths[0] = max(max_lengths[0], len(str(asn['date'])))
                max_lengths[1] = max(max_lengths[1], len(str(asn['shift'])))
                max_lengths[2] = max(max_lengths[2], len(str(asn['room'])))
                
            total_len = sum(max_lengths)
            col_widths = []
            for ml in max_lengths:
                cw = max(1.0 * inch, (ml / total_len) * available_width)
                col_widths.append(cw)
                
            sum_cw = sum(col_widths)
            if sum_cw > 0:
                col_widths = [cw * (available_width / sum_cw) for cw in col_widths]
                
            header_pstyle = ParagraphStyle(
                'HeaderP',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=colors.whitesmoke,
                alignment=TA_CENTER
            )
            
            data_pstyle = ParagraphStyle(
                'DataP',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                alignment=TA_CENTER
            )

            # Build mini-table (Removed Role Column)
            formatted_table_data = [[
                Paragraph("Date", header_pstyle), 
                Paragraph("Shift", header_pstyle), 
                Paragraph("Room", header_pstyle)
            ]]
            for asn in assignments:
                formatted_table_data.append([
                    Paragraph(str(asn['date']), data_pstyle),
                    Paragraph(str(asn['shift']), data_pstyle),
                    Paragraph(str(asn['room']), data_pstyle)
                ])
                
            t = Table(formatted_table_data, colWidths=col_widths)
            
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ]))
            
            person_block.append(t)
            person_block.append(Spacer(1, 0.3*inch))
            
            story.append(KeepTogether(person_block))
            
        doc.build(story)
        logger.info(f"✓ {label} PDF generated successfully: {pdf_output_path}")
        return pdf_output_path
        
    except Exception as e:
        logger.error(f"❌ Error creating {label} PDF: {str(e)}")
        return None
