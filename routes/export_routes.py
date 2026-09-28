import os
import logging
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
try:
    from config import Config
except ImportError:
    from CONFIG import Config
from utils.export_utils import build_grouped_dataframe, generate_schedules_zip
from service.createTable import create_table_pdf, create_room_tables_pdf, create_personnel_report_pdf

logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__)

@export_bp.route('/api/download-csv', methods=['POST'])
def download_csv():
    """Generate and download grouped CSV files (main, teachers, staffs, rooms) with constant filenames."""
    try:
        data = request.json or {}
        results = data.get('results', [])
        csv_type = data.get('type', 'main')
        
        logger.info(f'CSV generation started with {len(results)} schedule entries - Type: {csv_type}')
        
        output_df, filename = build_grouped_dataframe(results, csv_type)
        csv_string = output_df.to_csv(index=False)
        
        filepath = os.path.join(Config.SCHEDULE_STORAGE_DIR, filename)
        output_df.to_csv(filepath, index=False)
        logger.info(f'CSV saved to disk: {filepath} ({len(output_df)} rows)')

        output = BytesIO()
        output.write(csv_string.encode('utf-8'))
        output.seek(0)

        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f'CSV generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@export_bp.route('/api/download-all-csv', methods=['POST'])
def download_all_csv():
    """Download all grouped CSVs as a single ZIP file."""
    try:
        data = request.json or {}
        results = data.get('results', [])
        
        logger.info('Creating ZIP archive with all grouped schedules')
        zip_buffer = generate_schedules_zip(results)
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='exam_schedules.zip'
        )
    except Exception as e:
        logger.error(f'ZIP generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@export_bp.route('/api/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF from saved CSV file with formatting and grouping."""
    try:
        data = request.json or {}
        pdf_type = data.get('type', 'main')
        
        csv_config_map = {
            'main': {'csv': Config.MAIN_SCHEDULE_CSV, 'grouping': None},
            'teacher': {'csv': Config.TEACHER_SCHEDULE_CSV, 'grouping': 'Teacher'},
            'staff': {'csv': Config.STAFF_SCHEDULE_CSV, 'grouping': 'Staff'},
            'room': {'csv': Config.ROOM_SCHEDULE_CSV, 'grouping': 'Room'}
        }
        
        config_entry = csv_config_map.get(pdf_type, csv_config_map['main'])
        csv_filename = config_entry['csv']
        grouping_column = config_entry['grouping']
        csv_path = os.path.join(Config.SCHEDULE_STORAGE_DIR, csv_filename)
        
        if not os.path.exists(csv_path):
            return jsonify({
                'success': False,
                'error': f'CSV file not found: {csv_filename}. Please generate or view schedule first.'
            }), 404
        
        logger.info(f'Generating PDF from: {csv_filename} (grouping: {grouping_column})')
        pdf_filename = csv_filename.replace('.csv', '.pdf')
        pdf_path = os.path.join(Config.SCHEDULE_STORAGE_DIR, pdf_filename)
        
        if pdf_type == 'room':
            result = create_room_tables_pdf(csv_path, pdf_path)
        elif pdf_type in ['teacher', 'staff']:
            is_staff = (pdf_type == 'staff')
            result = create_personnel_report_pdf(csv_path, pdf_path, is_staff=is_staff)
        else:
            result = create_table_pdf(csv_path, pdf_path, grouping_column_name=grouping_column)
        
        if result and os.path.exists(pdf_path):
            logger.info(f'PDF generated successfully: {pdf_filename}')
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=pdf_filename
            )
        else:
            return jsonify({'success': False, 'error': 'Failed to generate PDF'}), 500
    
    except Exception as e:
        logger.error(f'PDF generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400
