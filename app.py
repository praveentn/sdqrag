import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import json
from datetime import datetime

# Your config loader
from config import get_config, init_app_config

# Single shared db instance
from extensions import db

# Initialize Flask
app = Flask(__name__, static_folder='build', static_url_path='')
config_class = get_config()
app.config.from_object(config_class)

# Init extensions
db.init_app(app)
CORS(app)

# Models (now import *after* db.init_app)
from models import (
    Project, DataSource, TableInfo, DataDictionary,
    EmbeddingModel, SearchIndex, ChatHistory, User
)

# Services & routes
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from services.search_service import SearchService
from services.data_service import DataService

from routes.project_routes import project_bp
from routes.datasource_routes import datasource_bp
from routes.dictionary_routes import dictionary_bp
from routes.embedding_routes import embedding_bp
from routes.search_routes import search_bp
from routes.chat_routes import chat_bp
from routes.admin_routes import admin_bp

# Register blueprints
app.register_blueprint(project_bp, url_prefix='/api/projects')
app.register_blueprint(datasource_bp, url_prefix='/api/datasources')
app.register_blueprint(dictionary_bp, url_prefix='/api/dictionary')
app.register_blueprint(embedding_bp, url_prefix='/api/embeddings')
app.register_blueprint(search_bp, url_prefix='/api/search')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Any other app init
init_app_config(app)

# Error handlers and endpoints unchanged…
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large'}), 413

@app.route('/api/health')
def health_check():
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and delegate to datasource service"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get project_id from form data
        project_id = request.form.get('project_id')
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        try:
            project_id = int(project_id)
        except ValueError:
            return jsonify({'error': 'Invalid project ID'}), 400
        
        # Verify project exists - FIX: Use newer SQLAlchemy syntax
        project = db.session.get(Project, project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Validate file extension
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in app.config['ALLOWED_EXTENSIONS']:
            return jsonify({
                'error': f'File type .{file_ext} not allowed. Supported types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
            }), 400
        
        # Create upload directory for project
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], str(project_id))
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # Process file using DataService
        data_service = DataService()
        result = data_service.process_uploaded_file(file_path, project_id, filename)
        
        if result['status'] == 'success':
            return jsonify({
                'status': 'success',
                'message': f'File {filename} uploaded and processed successfully',
                'data_source': result.get('data_source'),
                'tables': result.get('tables_created', [])
            })
        else:
            # Clean up file on processing failure
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({
                'status': 'error',
                'message': result.get('message', 'File processing failed')
            }), 500
        
    except Exception as e:
        app.logger.error(f"Upload file error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Upload failed: {str(e)}'
        }), 500


def init_db():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@queryforge.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created (username: admin, password: admin123)")

if __name__ == '__main__':
    if not os.path.exists('queryforge.db'):
        print("Database not found. Initializing...")
        init_db()
    else:
        print("Database already exists. Skipping initialization.")

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
