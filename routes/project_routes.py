# routes/project_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import Project, User, db
from datetime import datetime

project_bp = Blueprint('projects', __name__)

@project_bp.route('/', methods=['GET'])
def get_projects():
    """Get all projects for the current user"""
    try:
        # For now, return all projects. In a real app, filter by user
        projects = Project.query.filter_by(is_active=True).all()
        
        return jsonify({
            'status': 'success',
            'projects': [project.to_dict() for project in projects]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get projects error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        
        # Get or create default user
        user = User.query.filter_by(username='admin').first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        project = Project(
            name=data['name'],
            description=data.get('description', ''),
            created_by=user.id
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project created successfully',
            'project': project.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create project error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Include additional statistics
        project_data = project.to_dict()
        project_data['stats'] = {
            'data_sources': len(project.data_sources),
            'tables': len(project.table_infos),
            'dictionary_entries': len(project.dictionary_entries),
            'embedding_models': len(project.embedding_models),
            'search_indexes': len(project.search_indexes),
            'chat_sessions': len(set(chat.session_id for chat in project.chat_sessions))
        }
        
        return jsonify({
            'status': 'success',
            'project': project_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get project error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update fields
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        
        project.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project updated successfully',
            'project': project.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update project error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project (soft delete)"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Soft delete - set is_active to False
        project.is_active = False
        project.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Project deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete project error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/<int:project_id>/summary', methods=['GET'])
def get_project_summary(project_id):
    """Get project summary with detailed statistics"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Calculate detailed statistics
        summary = {
            'project': project.to_dict(),
            'data_sources': {
                'total': len(project.data_sources),
                'by_type': {},
                'recent': []
            },
            'tables': {
                'total': len(project.table_infos),
                'total_rows': sum(table.row_count for table in project.table_infos),
                'total_columns': sum(table.column_count for table in project.table_infos),
                'largest_table': None
            },
            'dictionary': {
                'total': len(project.dictionary_entries),
                'by_category': {},
                'verified_count': sum(1 for entry in project.dictionary_entries if entry.is_verified)
            },
            'embeddings': {
                'total': len(project.embedding_models),
                'ready_count': sum(1 for model in project.embedding_models if model.status == 'ready'),
                'indexes_count': len(project.search_indexes)
            },
            'chat': {
                'total_sessions': len(set(chat.session_id for chat in project.chat_sessions)),
                'total_queries': len(project.chat_sessions),
                'successful_queries': sum(1 for chat in project.chat_sessions if chat.status == 'completed')
            }
        }
        
        # Data sources by type
        for ds in project.data_sources:
            ds_type = ds.source_type
            summary['data_sources']['by_type'][ds_type] = summary['data_sources']['by_type'].get(ds_type, 0) + 1
        
        # Recent data sources
        recent_ds = sorted(project.data_sources, key=lambda x: x.created_at, reverse=True)[:5]
        summary['data_sources']['recent'] = [ds.to_dict() for ds in recent_ds]
        
        # Largest table
        if project.table_infos:
            largest = max(project.table_infos, key=lambda x: x.row_count)
            summary['tables']['largest_table'] = {
                'name': largest.table_name,
                'rows': largest.row_count,
                'columns': largest.column_count
            }
        
        # Dictionary by category
        for entry in project.dictionary_entries:
            category = entry.category
            summary['dictionary']['by_category'][category] = summary['dictionary']['by_category'].get(category, 0) + 1
        
        return jsonify({
            'status': 'success',
            'summary': summary
        })
        
    except Exception as e:
        current_app.logger.error(f"Get project summary error: {str(e)}")
        return jsonify({'error': str(e)}), 500