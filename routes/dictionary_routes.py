# routes/dictionary_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import DataDictionary, Project, User, db
from services.llm_service import LLMService
from datetime import datetime

dictionary_bp = Blueprint('dictionary', __name__)

@dictionary_bp.route('/<int:project_id>', methods=['GET'])
def get_dictionary_entries(project_id):
    """Get all dictionary entries for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get filter parameters
        category = request.args.get('category')
        search_term = request.args.get('search')
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'
        
        # Build query
        query = DataDictionary.query.filter_by(project_id=project_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                db.or_(
                    DataDictionary.term.ilike(search_pattern),
                    DataDictionary.definition.ilike(search_pattern),
                    DataDictionary.aliases.ilike(search_pattern)
                )
            )
        
        if verified_only:
            query = query.filter_by(is_verified=True)
        
        # Get results with ordering
        entries = query.order_by(DataDictionary.term).all()
        
        # Group by category for better organization
        grouped_entries = {}
        for entry in entries:
            category_key = entry.category
            if category_key not in grouped_entries:
                grouped_entries[category_key] = []
            grouped_entries[category_key].append(entry.to_dict())
        
        return jsonify({
            'status': 'success',
            'entries': [entry.to_dict() for entry in entries],
            'grouped_entries': grouped_entries,
            'total_count': len(entries),
            'categories': list(grouped_entries.keys())
        })
        
    except Exception as e:
        current_app.logger.error(f"Get dictionary entries error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/<int:project_id>', methods=['POST'])
def create_dictionary_entry(project_id):
    """Create a new dictionary entry"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('term') or not data.get('definition'):
            return jsonify({'error': 'Term and definition are required'}), 400
        
        # Check if term already exists in this project
        existing = DataDictionary.query.filter_by(
            project_id=project_id,
            term=data['term'],
            category=data.get('category', 'encyclopedia')
        ).first()
        
        if existing:
            return jsonify({'error': 'Term already exists in this category'}), 409
        
        # Get default user
        user = User.query.filter_by(username='admin').first()
        
        # Create entry
        entry = DataDictionary(
            project_id=project_id,
            term=data['term'],
            definition=data['definition'],
            category=data.get('category', 'encyclopedia'),
            source_table=data.get('source_table'),
            source_column=data.get('source_column'),
            confidence_score=data.get('confidence_score', 1.0),
            is_verified=data.get('is_verified', False),
            created_by=user.id if user else None
        )
        
        # Set optional fields
        if data.get('aliases'):
            entry.set_aliases(data['aliases'])
        if data.get('examples'):
            entry.set_examples(data['examples'])
        if data.get('tags'):
            entry.set_tags(data['tags'])
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Dictionary entry created successfully',
            'entry': entry.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create dictionary entry error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/entries/<int:entry_id>', methods=['GET'])
def get_dictionary_entry(entry_id):
    """Get a specific dictionary entry"""
    try:
        entry = DataDictionary.query.get_or_404(entry_id)
        
        return jsonify({
            'status': 'success',
            'entry': entry.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Get dictionary entry error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/entries/<int:entry_id>', methods=['PUT'])
def update_dictionary_entry(entry_id):
    """Update a dictionary entry"""
    try:
        entry = DataDictionary.query.get_or_404(entry_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update fields
        if 'term' in data:
            # Check for duplicates
            existing = DataDictionary.query.filter(
                DataDictionary.id != entry_id,
                DataDictionary.project_id == entry.project_id,
                DataDictionary.term == data['term'],
                DataDictionary.category == data.get('category', entry.category)
            ).first()
            
            if existing:
                return jsonify({'error': 'Term already exists in this category'}), 409
            
            entry.term = data['term']
        
        if 'definition' in data:
            entry.definition = data['definition']
        if 'category' in data:
            entry.category = data['category']
        if 'source_table' in data:
            entry.source_table = data['source_table']
        if 'source_column' in data:
            entry.source_column = data['source_column']
        if 'confidence_score' in data:
            entry.confidence_score = data['confidence_score']
        if 'is_verified' in data:
            entry.is_verified = data['is_verified']
        
        # Update arrays
        if 'aliases' in data:
            entry.set_aliases(data['aliases'])
        if 'examples' in data:
            entry.set_examples(data['examples'])
        if 'tags' in data:
            entry.set_tags(data['tags'])
        
        entry.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Dictionary entry updated successfully',
            'entry': entry.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update dictionary entry error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
def delete_dictionary_entry(entry_id):
    """Delete a dictionary entry"""
    try:
        entry = DataDictionary.query.get_or_404(entry_id)
        
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Dictionary entry deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete dictionary entry error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/<int:project_id>/categories', methods=['GET'])
def get_dictionary_categories(project_id):
    """Get all categories used in the project dictionary"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get distinct categories
        categories = db.session.query(DataDictionary.category).filter_by(
            project_id=project_id
        ).distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        # Get counts for each category
        category_stats = {}
        for category in category_list:
            count = DataDictionary.query.filter_by(
                project_id=project_id,
                category=category
            ).count()
            
            verified_count = DataDictionary.query.filter_by(
                project_id=project_id,
                category=category,
                is_verified=True
            ).count()
            
            category_stats[category] = {
                'total': count,
                'verified': verified_count,
                'unverified': count - verified_count
            }
        
        return jsonify({
            'status': 'success',
            'categories': category_list,
            'category_stats': category_stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Get dictionary categories error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/entries/<int:entry_id>/enhance', methods=['POST'])
def enhance_dictionary_entry(entry_id):
    """Enhance a dictionary entry using AI"""
    try:
        entry = DataDictionary.query.get_or_404(entry_id)
        
        # Get project context
        from models import TableInfo
        tables = TableInfo.query.filter_by(project_id=entry.project_id).all()
        table_names = [table.table_name for table in tables]
        
        # Use LLM to enhance definition
        llm_service = LLMService()
        if llm_service.is_available():
            enhanced_definition = llm_service.enhance_dictionary_definition(
                entry.term,
                entry.definition,
                entry.category,
                table_names
            )
            
            # Save original as backup and update
            original_definition = entry.definition
            entry.definition = enhanced_definition
            entry.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Dictionary entry enhanced successfully',
                'entry': entry.to_dict(),
                'original_definition': original_definition
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'AI enhancement service not available'
            }), 503
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Enhance dictionary entry error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/<int:project_id>/bulk-verify', methods=['POST'])
def bulk_verify_entries(project_id):
    """Bulk verify dictionary entries"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or 'entry_ids' not in data:
            return jsonify({'error': 'Entry IDs are required'}), 400
        
        entry_ids = data['entry_ids']
        verify_status = data.get('verified', True)
        
        # Update entries
        entries = DataDictionary.query.filter(
            DataDictionary.id.in_(entry_ids),
            DataDictionary.project_id == project_id
        ).all()
        
        updated_count = 0
        for entry in entries:
            entry.is_verified = verify_status
            entry.updated_at = datetime.utcnow()
            updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'{updated_count} entries updated successfully',
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk verify entries error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/<int:project_id>/import', methods=['POST'])
def import_dictionary_entries(project_id):
    """Import dictionary entries from file or data"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or 'entries' not in data:
            return jsonify({'error': 'Entries data is required'}), 400
        
        entries_data = data['entries']
        overwrite_existing = data.get('overwrite_existing', False)
        
        # Get default user
        user = User.query.filter_by(username='admin').first()
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for entry_data in entries_data:
            if not entry_data.get('term') or not entry_data.get('definition'):
                skipped_count += 1
                continue
            
            # Check if entry exists
            existing = DataDictionary.query.filter_by(
                project_id=project_id,
                term=entry_data['term'],
                category=entry_data.get('category', 'encyclopedia')
            ).first()
            
            if existing:
                if overwrite_existing:
                    # Update existing entry
                    existing.definition = entry_data['definition']
                    if 'aliases' in entry_data:
                        existing.set_aliases(entry_data['aliases'])
                    if 'examples' in entry_data:
                        existing.set_examples(entry_data['examples'])
                    if 'tags' in entry_data:
                        existing.set_tags(entry_data['tags'])
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    skipped_count += 1
                    continue
            else:
                # Create new entry
                entry = DataDictionary(
                    project_id=project_id,
                    term=entry_data['term'],
                    definition=entry_data['definition'],
                    category=entry_data.get('category', 'encyclopedia'),
                    source_table=entry_data.get('source_table'),
                    source_column=entry_data.get('source_column'),
                    confidence_score=entry_data.get('confidence_score', 1.0),
                    is_verified=entry_data.get('is_verified', False),
                    created_by=user.id if user else None
                )
                
                if 'aliases' in entry_data:
                    entry.set_aliases(entry_data['aliases'])
                if 'examples' in entry_data:
                    entry.set_examples(entry_data['examples'])
                if 'tags' in entry_data:
                    entry.set_tags(entry_data['tags'])
                
                db.session.add(entry)
                created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped',
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Import dictionary entries error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@dictionary_bp.route('/<int:project_id>/export', methods=['GET'])
def export_dictionary_entries(project_id):
    """Export dictionary entries"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get filter parameters
        category = request.args.get('category')
        verified_only = request.args.get('verified_only', 'false').lower() == 'true'
        
        # Build query
        query = DataDictionary.query.filter_by(project_id=project_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if verified_only:
            query = query.filter_by(is_verified=True)
        
        entries = query.order_by(DataDictionary.category, DataDictionary.term).all()
        
        # Convert to export format
        export_data = {
            'project_name': project.name,
            'export_date': datetime.utcnow().isoformat(),
            'total_entries': len(entries),
            'entries': [entry.to_dict() for entry in entries]
        }
        
        return jsonify({
            'status': 'success',
            'export_data': export_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Export dictionary entries error: {str(e)}")
        return jsonify({'error': str(e)}), 500