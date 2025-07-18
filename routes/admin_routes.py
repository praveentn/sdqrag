# routes/admin_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import db, Project, DataSource, TableInfo, DataDictionary, EmbeddingModel, SearchIndex, ChatHistory, User
from services.search_service import SearchService
import sqlite3
import os
import psutil
from datetime import datetime, timedelta
import json

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/tables', methods=['GET'])
def get_all_tables():
    """Get all database tables with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        
        # Get all table names from SQLAlchemy metadata
        tables_info = []
        
        # System tables
        system_tables = [
            ('projects', Project),
            ('data_sources', DataSource),
            ('table_info', TableInfo),
            ('data_dictionary', DataDictionary),
            ('embedding_models', EmbeddingModel),
            ('search_indexes', SearchIndex),
            ('chat_history', ChatHistory),
            ('users', User)
        ]
        
        for table_name, model_class in system_tables:
            try:
                count = model_class.query.count()
                tables_info.append({
                    'name': table_name,
                    'type': 'system',
                    'row_count': count,
                    'model': model_class.__name__
                })
            except Exception as e:
                tables_info.append({
                    'name': table_name,
                    'type': 'system',
                    'row_count': 0,
                    'error': str(e)
                })
        
        # Get user data tables from project databases
        projects = Project.query.all()
        for project in projects:
            try:
                search_service = SearchService()
                db_path = search_service._get_project_db_path(project.id)
                
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    user_tables = cursor.fetchall()
                    
                    for table in user_tables:
                        table_name = table[0]
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        
                        tables_info.append({
                            'name': f"{project.name}.{table_name}",
                            'type': 'user_data',
                            'row_count': row_count,
                            'project_id': project.id,
                            'project_name': project.name,
                            'table_name': table_name
                        })
                    
                    conn.close()
            except Exception as e:
                current_app.logger.error(f"Error reading project {project.id} database: {str(e)}")
        
        # Sort and paginate
        tables_info.sort(key=lambda x: x['name'])
        
        total_tables = len(tables_info)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_tables = tables_info[start_idx:end_idx]
        
        return jsonify({
            'status': 'success',
            'tables': paginated_tables,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_tables,
                'pages': (total_tables + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Get all tables error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tables/<table_name>/data', methods=['GET'])
def get_table_data(table_name):
    """Get data from a specific table"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 1000)
        
        # Check if it's a system table or user data table
        if '.' in table_name:
            # User data table (project.table_name)
            project_name, actual_table_name = table_name.split('.', 1)
            
            project = Project.query.filter_by(name=project_name).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            
            search_service = SearchService()
            db_path = search_service._get_project_db_path(project.id)
            
            if not os.path.exists(db_path):
                return jsonify({'error': 'Project database not found'}), 404
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM {actual_table_name}")
            total_count = cursor.fetchone()['count']
            
            # Get paginated data
            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * FROM {actual_table_name} LIMIT ? OFFSET ?", (per_page, offset))
            rows = cursor.fetchall()
            
            data = [dict(row) for row in rows]
            columns = list(data[0].keys()) if data else []
            
            conn.close()
            
        else:
            # System table
            model_map = {
                'projects': Project,
                'data_sources': DataSource,
                'table_info': TableInfo,
                'data_dictionary': DataDictionary,
                'embedding_models': EmbeddingModel,
                'search_indexes': SearchIndex,
                'chat_history': ChatHistory,
                'users': User
            }
            
            if table_name not in model_map:
                return jsonify({'error': 'Table not found'}), 404
            
            model_class = model_map[table_name]
            
            # Get total count
            total_count = model_class.query.count()
            
            # Get paginated data
            offset = (page - 1) * per_page
            records = model_class.query.offset(offset).limit(per_page).all()
            
            data = [record.to_dict() for record in records]
            columns = list(data[0].keys()) if data else []
        
        return jsonify({
            'status': 'success',
            'table_name': table_name,
            'data': data,
            'columns': columns,
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

@admin_bp.route('/sql/execute', methods=['POST'])
def execute_sql():
    """Execute SQL query with syntax highlighting support"""
    try:
        data = request.get_json()
        
        if not data or not data.get('sql'):
            return jsonify({'error': 'SQL query is required'}), 400
        
        sql_query = data['sql'].strip()
        target_db = data.get('target_db', 'system')  # 'system' or project_id
        
        if not sql_query:
            return jsonify({'error': 'Empty SQL query'}), 400
        
        # Security validation
        sql_upper = sql_query.upper()
        
        # Check for dangerous operations
        dangerous_keywords = ['DROP', 'TRUNCATE', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'EXEC']
        is_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
        
        if is_dangerous:
            confirm_dangerous = data.get('confirm_dangerous', False)
            if not confirm_dangerous:
                return jsonify({
                    'status': 'warning',
                    'message': 'This query contains potentially dangerous operations. Confirm to execute.',
                    'dangerous_operations': [kw for kw in dangerous_keywords if kw in sql_upper],
                    'requires_confirmation': True
                }), 200
        
        # Execute query
        if target_db == 'system':
            # Execute on system database
            result = db.session.execute(sql_query)
            
            if sql_upper.startswith('SELECT'):
                rows = result.fetchall()
                data_list = [dict(row) for row in rows]
                columns = list(data_list[0].keys()) if data_list else []
                
                return jsonify({
                    'status': 'success',
                    'message': f'Query executed successfully. {len(data_list)} rows returned.',
                    'data': data_list,
                    'columns': columns,
                    'row_count': len(data_list),
                    'execution_type': 'SELECT'
                })
            else:
                db.session.commit()
                return jsonify({
                    'status': 'success',
                    'message': f'Query executed successfully. {result.rowcount} rows affected.',
                    'rows_affected': result.rowcount,
                    'execution_type': 'DML'
                })
        
        else:
            # Execute on project database
            try:
                project_id = int(target_db)
                project = Project.query.get_or_404(project_id)
                
                search_service = SearchService()
                db_path = search_service._get_project_db_path(project_id)
                
                if not os.path.exists(db_path):
                    return jsonify({'error': 'Project database not found'}), 404
                
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(sql_query)
                
                if sql_upper.startswith('SELECT'):
                    rows = cursor.fetchall()
                    data_list = [dict(row) for row in rows]
                    columns = list(data_list[0].keys()) if data_list else []
                    
                    conn.close()
                    
                    return jsonify({
                        'status': 'success',
                        'message': f'Query executed successfully. {len(data_list)} rows returned.',
                        'data': data_list,
                        'columns': columns,
                        'row_count': len(data_list),
                        'execution_type': 'SELECT',
                        'target_project': project.name
                    })
                else:
                    conn.commit()
                    affected_rows = cursor.rowcount
                    conn.close()
                    
                    return jsonify({
                        'status': 'success',
                        'message': f'Query executed successfully. {affected_rows} rows affected.',
                        'rows_affected': affected_rows,
                        'execution_type': 'DML',
                        'target_project': project.name
                    })
                    
            except ValueError:
                return jsonify({'error': 'Invalid project ID'}), 400
        
    except Exception as e:
        if 'db.session' in locals():
            db.session.rollback()
        current_app.logger.error(f"Execute SQL error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/system/health', methods=['GET'])
def get_system_health():
    """Get system health and performance metrics"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database metrics
        db_stats = {}
        
        # System database stats
        system_tables = [
            ('projects', Project),
            ('data_sources', DataSource),
            ('table_info', TableInfo),
            ('data_dictionary', DataDictionary),
            ('embedding_models', EmbeddingModel),
            ('search_indexes', SearchIndex),
            ('chat_history', ChatHistory),
            ('users', User)
        ]
        
        for table_name, model_class in system_tables:
            try:
                count = model_class.query.count()
                db_stats[table_name] = count
            except:
                db_stats[table_name] = 0
        
        # Project databases stats
        projects = Project.query.all()
        project_db_stats = {}
        
        for project in projects:
            try:
                search_service = SearchService()
                db_path = search_service._get_project_db_path(project.id)
                
                if os.path.exists(db_path):
                    file_size = os.path.getsize(db_path)
                    project_db_stats[project.name] = {
                        'size_bytes': file_size,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    }
            except:
                project_db_stats[project.name] = {'size_bytes': 0, 'size_mb': 0}
        
        # Application metrics
        uptime = datetime.utcnow() - datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Recent activity
        recent_activity = {
            'recent_projects': Project.query.order_by(Project.created_at.desc()).limit(5).count(),
            'recent_queries': ChatHistory.query.filter(
                ChatHistory.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count(),
            'active_sessions': len(set(
                chat.session_id for chat in ChatHistory.query.filter(
                    ChatHistory.created_at >= datetime.utcnow() - timedelta(hours=1)
                ).all()
            ))
        }
        
        # Storage usage
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        models_folder = 'models'
        indexes_folder = 'indexes'
        
        storage_usage = {}
        for folder_name, folder_path in [('uploads', upload_folder), ('models', models_folder), ('indexes', indexes_folder)]:
            try:
                if os.path.exists(folder_path):
                    total_size = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(folder_path)
                        for filename in filenames
                    )
                    storage_usage[folder_name] = {
                        'size_bytes': total_size,
                        'size_mb': round(total_size / (1024 * 1024), 2)
                    }
                else:
                    storage_usage[folder_name] = {'size_bytes': 0, 'size_mb': 0}
            except:
                storage_usage[folder_name] = {'size_bytes': 0, 'size_mb': 0}
        
        health_status = {
            'system': {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'used_gb': round(disk.used / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'percent': (disk.used / disk.total) * 100
                }
            },
            'database': {
                'system_tables': db_stats,
                'project_databases': project_db_stats
            },
            'application': {
                'uptime_hours': uptime.total_seconds() / 3600,
                'recent_activity': recent_activity,
                'storage_usage': storage_usage
            },
            'services': {
                'llm_available': False,  # Will be updated below
                'embedding_models_ready': 0,
                'search_indexes_ready': 0
            }
        }
        
        # Check LLM service
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            health_status['services']['llm_available'] = llm_service.is_available()
        except:
            pass
        
        # Check embedding models and indexes
        try:
            ready_models = EmbeddingModel.query.filter_by(status='ready').count()
            ready_indexes = SearchIndex.query.filter_by(status='ready').count()
            
            health_status['services']['embedding_models_ready'] = ready_models
            health_status['services']['search_indexes_ready'] = ready_indexes
        except:
            pass
        
        return jsonify({
            'status': 'success',
            'health': health_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Get system health error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        users = User.query.all()
        
        return jsonify({
            'status': 'success',
            'users': [user.to_dict() for user in users]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get users error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('email'):
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Check for existing user
        existing = User.query.filter(
            db.or_(User.username == data['username'], User.email == data['email'])
        ).first()
        
        if existing:
            return jsonify({'error': 'Username or email already exists'}), 409
        
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            role=data.get('role', 'user'),
            is_active=data.get('is_active', True)
        )
        
        if data.get('password'):
            user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create user error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/backup', methods=['POST'])
def create_backup():
    """Create system backup"""
    try:
        # Create backup directory
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"queryforge_backup_{timestamp}"
        backup_path = os.path.join(backup_dir, f"{backup_name}.json")
        
        # Collect all data
        backup_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'data': {}
        }
        
        # System tables
        system_tables = [
            ('projects', Project),
            ('data_sources', DataSource),
            ('table_info', TableInfo),
            ('data_dictionary', DataDictionary),
            ('embedding_models', EmbeddingModel),
            ('search_indexes', SearchIndex),
            ('chat_history', ChatHistory),
            ('users', User)
        ]
        
        for table_name, model_class in system_tables:
            try:
                records = model_class.query.all()
                backup_data['data'][table_name] = [record.to_dict() for record in records]
            except Exception as e:
                backup_data['data'][table_name] = {'error': str(e)}
        
        # Save backup
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Get backup file size
        backup_size = os.path.getsize(backup_path)
        
        return jsonify({
            'status': 'success',
            'message': 'Backup created successfully',
            'backup_name': backup_name,
            'backup_path': backup_path,
            'backup_size_mb': round(backup_size / (1024 * 1024), 2),
            'tables_backed_up': len([k for k, v in backup_data['data'].items() if 'error' not in v])
        })
        
    except Exception as e:
        current_app.logger.error(f"Create backup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/backups', methods=['GET'])
def list_backups():
    """List available backups"""
    try:
        backup_dir = 'backups'
        
        if not os.path.exists(backup_dir):
            return jsonify({
                'status': 'success',
                'backups': []
            })
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(backup_dir, filename)
                file_size = os.path.getsize(file_path)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                backups.append({
                    'filename': filename,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'created_at': file_mtime.isoformat(),
                    'age_hours': (datetime.utcnow() - file_mtime).total_seconds() / 3600
                })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'backups': backups
        })
        
    except Exception as e:
        current_app.logger.error(f"List backups error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/optimize', methods=['POST'])
def optimize_database():
    """Optimize database performance"""
    try:
        optimization_results = {}
        
        # System database optimization
        try:
            db.session.execute('VACUUM')
            db.session.execute('ANALYZE')
            db.session.commit()
            optimization_results['system_db'] = 'optimized'
        except Exception as e:
            optimization_results['system_db'] = f'error: {str(e)}'
        
        # Project databases optimization
        projects = Project.query.all()
        for project in projects:
            try:
                search_service = SearchService()
                db_path = search_service._get_project_db_path(project.id)
                
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('VACUUM')
                    cursor.execute('ANALYZE')
                    conn.commit()
                    conn.close()
                    
                    optimization_results[f'project_{project.id}'] = 'optimized'
            except Exception as e:
                optimization_results[f'project_{project.id}'] = f'error: {str(e)}'
        
        # Clean up temporary files
        temp_cleaned = 0
        for folder in ['uploads', 'models', 'indexes']:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        if file.endswith('.tmp') or file.startswith('temp_'):
                            try:
                                os.remove(os.path.join(root, file))
                                temp_cleaned += 1
                            except:
                                pass
        
        optimization_results['temp_files_cleaned'] = temp_cleaned
        
        return jsonify({
            'status': 'success',
            'message': 'Database optimization completed',
            'results': optimization_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Optimize database error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/logs', methods=['GET'])
def get_system_logs():
    """Get system logs"""
    try:
        log_file = 'logs/app.log'
        lines = request.args.get('lines', 100, type=int)
        level = request.args.get('level', 'all')
        
        if not os.path.exists(log_file):
            return jsonify({
                'status': 'success',
                'logs': [],
                'message': 'No log file found'
            })
        
        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
        
        # Get last N lines
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Filter by level if specified
        if level != 'all':
            recent_lines = [line for line in recent_lines if level.upper() in line.upper()]
        
        # Parse log lines
        logs = []
        for line in recent_lines:
            line = line.strip()
            if line:
                logs.append({
                    'timestamp': line.split(']')[0].replace('[', '') if ']' in line else '',
                    'level': 'INFO' if 'INFO' in line else 'ERROR' if 'ERROR' in line else 'WARNING' if 'WARNING' in line else 'DEBUG',
                    'message': line
                })
        
        return jsonify({
            'status': 'success',
            'logs': logs,
            'total_lines': len(recent_lines)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get system logs error: {str(e)}")
        return jsonify({'error': str(e)}), 500