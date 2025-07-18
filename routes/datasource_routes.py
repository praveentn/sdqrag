# routes/datasource_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import DataSource, TableInfo, Project, db
from services.data_service import DataService
import os
import sqlite3
import json

datasource_bp = Blueprint('datasources', __name__)

@datasource_bp.route('/<int:project_id>', methods=['GET'])
def get_data_sources(project_id):
    """Get all data sources for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        data_sources = DataSource.query.filter_by(project_id=project_id).all()
        
        return jsonify({
            'status': 'success',
            'data_sources': [ds.to_dict() for ds in data_sources]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get data sources error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/<int:project_id>/upload', methods=['POST'])
def upload_data_source(project_id):
    """Upload and process a data file"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in current_app.config['ALLOWED_EXTENSIONS']:
            return jsonify({'error': f'File type .{file_ext} not allowed'}), 400
        
        # Save file
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], str(project_id))
        os.makedirs(upload_path, exist_ok=True)
        
        from werkzeug.utils import secure_filename
        filename = secure_filename(filename)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # Process file
        data_service = DataService()
        result = data_service.process_uploaded_file(file_path, project_id, filename)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Upload data source error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/<int:data_source_id>', methods=['GET'])
def get_data_source(data_source_id):
    """Get a specific data source with its tables"""
    try:
        data_source = DataSource.query.get_or_404(data_source_id)
        
        # Get associated tables
        tables = TableInfo.query.filter_by(data_source_id=data_source_id).all()
        
        result = data_source.to_dict()
        result['tables'] = [table.to_dict() for table in tables]
        
        return jsonify({
            'status': 'success',
            'data_source': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Get data source error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/<int:data_source_id>', methods=['DELETE'])
def delete_data_source(data_source_id):
    """Delete a data source and its associated tables"""
    try:
        data_source = DataSource.query.get_or_404(data_source_id)
        
        # Delete associated tables and files
        tables = TableInfo.query.filter_by(data_source_id=data_source_id).all()
        
        # Delete from database
        for table in tables:
            db.session.delete(table)
        
        # Delete file if it exists
        if data_source.file_path and os.path.exists(data_source.file_path):
            os.remove(data_source.file_path)
        
        db.session.delete(data_source)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Data source deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete data source error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/tables/<int:table_id>', methods=['GET'])
def get_table_info(table_id):
    """Get detailed table information"""
    try:
        table = TableInfo.query.get_or_404(table_id)
        
        return jsonify({
            'status': 'success',
            'table': table.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Get table info error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/tables/<int:table_id>', methods=['PUT'])
def update_table_info(table_id):
    """Update table information (description, schema descriptions)"""
    try:
        table = TableInfo.query.get_or_404(table_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update description
        if 'description' in data:
            table.description = data['description']
        
        # Update column descriptions in schema
        if 'schema_updates' in data:
            schema = table.get_schema()
            updates = data['schema_updates']
            
            for column in schema.get('columns', []):
                col_name = column['name']
                if col_name in updates:
                    column['description'] = updates[col_name]
            
            table.set_schema(schema)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Table updated successfully',
            'table': table.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update table info error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/tables/<int:table_id>/data', methods=['GET'])
def get_table_data(table_id):
    """Get table data with pagination"""
    try:
        table = TableInfo.query.get_or_404(table_id)
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 1000)  # Max 1000 rows
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Get project database path
        data_service = DataService()
        db_path = data_service._get_project_db_path(table.project_id)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database file not found'}), 404
        
        # Query data
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) as count FROM {table.table_name}")
        total_count = cursor.fetchone()['count']
        
        # Get paginated data
        cursor.execute(f"SELECT * FROM {table.table_name} LIMIT ? OFFSET ?", (per_page, offset))
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        data = [dict(row) for row in rows]
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get table data error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/database/connect', methods=['POST'])
def connect_database():
    """Test database connection"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No connection data provided'}), 400
        
        data_service = DataService()
        result = data_service.test_database_connection(data)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Database connection error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/<int:project_id>/database', methods=['POST'])
def add_database_source(project_id):
    """Add a database as a data source"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No connection data provided'}), 400
        
        # Test connection first
        data_service = DataService()
        test_result = data_service.test_database_connection(data)
        
        if test_result['status'] != 'success':
            return jsonify(test_result), 400
        
        # Create data source record
        data_source = DataSource(
            project_id=project_id,
            name=data.get('name', f"Database Connection"),
            source_type='database',
            connection_config=json.dumps(data),
            status='active'
        )
        
        db.session.add(data_source)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Database connection added successfully',
            'data_source': data_source.to_dict(),
            'connection_test': test_result
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add database source error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/<int:project_id>/generate-dictionary', methods=['POST'])
def generate_project_dictionary(project_id):
    """Auto-generate data dictionary for project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        data_service = DataService()
        result = data_service.generate_data_dictionary(project_id)
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Generate dictionary error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@datasource_bp.route('/tables/<int:table_id>/schema/validate', methods=['POST'])
def validate_table_schema(table_id):
    """Validate and analyze table schema"""
    try:
        table = TableInfo.query.get_or_404(table_id)
        
        # Get actual data from database to validate schema
        data_service = DataService()
        db_path = data_service._get_project_db_path(table.project_id)
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database file not found'}), 404
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info from SQLite
        cursor.execute(f"PRAGMA table_info({table.table_name})")
        db_columns = cursor.fetchall()
        
        # Get sample data for analysis
        cursor.execute(f"SELECT * FROM {table.table_name} LIMIT 100")
        sample_rows = cursor.fetchall()
        
        conn.close()
        
        # Analyze schema consistency
        validation_results = {
            'status': 'success',
            'schema_matches': True,
            'issues': [],
            'recommendations': [],
            'column_analysis': []
        }
        
        # Compare stored schema with actual database schema
        stored_schema = table.get_schema()
        stored_columns = {col['name']: col for col in stored_schema.get('columns', [])}
        
        for db_col in db_columns:
            col_name = db_col[1]  # Column name
            col_type = db_col[2]  # Column type
            
            if col_name not in stored_columns:
                validation_results['issues'].append(f"Column '{col_name}' exists in database but not in stored schema")
                validation_results['schema_matches'] = False
            else:
                stored_col = stored_columns[col_name]
                validation_results['column_analysis'].append({
                    'name': col_name,
                    'db_type': col_type,
                    'stored_type': stored_col.get('type'),
                    'consistent': True  # You could add more sophisticated type checking here
                })
        
        return jsonify(validation_results)
        
    except Exception as e:
        current_app.logger.error(f"Validate schema error: {str(e)}")
        return jsonify({'error': str(e)}), 500