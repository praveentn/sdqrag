# routes/embedding_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import EmbeddingModel, SearchIndex, Project, TableInfo, DataDictionary, db
from services.embedding_service import EmbeddingService
import threading

embedding_bp = Blueprint('embeddings', __name__)

@embedding_bp.route('/models/available', methods=['GET'])
def get_available_models():
    """Get list of available embedding models"""
    try:
        embedding_service = EmbeddingService()
        models = embedding_service.get_available_models()
        
        return jsonify({
            'status': 'success',
            'models': models
        })
        
    except Exception as e:
        current_app.logger.error(f"Get available models error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/<int:project_id>/models', methods=['GET'])
def get_project_models(project_id):
    """Get all embedding models for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        models = EmbeddingModel.query.filter_by(project_id=project_id).all()
        
        return jsonify({
            'status': 'success',
            'models': [model.to_dict() for model in models]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get project models error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/models/<int:model_id>/status', methods=['GET'])
def get_model_status(model_id):
    """Get model download/status"""
    try:
        model = EmbeddingModel.query.get_or_404(model_id)
        
        return jsonify({
            'status': 'success',
            'model': model.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Get model status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/<int:project_id>/indexes', methods=['GET'])
def get_project_indexes(project_id):
    """Get all search indexes for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        indexes = SearchIndex.query.filter_by(project_id=project_id).all()
        
        # Include embedding model info
        result = []
        for index in indexes:
            index_data = index.to_dict()
            if index.embedding_model:
                index_data['embedding_model'] = index.embedding_model.to_dict()
            result.append(index_data)
        
        return jsonify({
            'status': 'success',
            'indexes': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Get project indexes error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/indexes/<int:index_id>/status', methods=['GET'])
def get_index_status(index_id):
    """Get index build status"""
    try:
        index = SearchIndex.query.get_or_404(index_id)
        
        index_data = index.to_dict()
        if index.embedding_model:
            index_data['embedding_model'] = index.embedding_model.to_dict()
        
        return jsonify({
            'status': 'success',
            'index': index_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Get index status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/indexes/<int:index_id>', methods=['DELETE'])
def delete_index(index_id):
    """Delete a search index"""
    try:
        index = SearchIndex.query.get_or_404(index_id)
        
        # Delete index files
        import os
        if index.index_path and os.path.exists(index.index_path):
            os.remove(index.index_path)
        
        # Delete metadata file for FAISS indexes
        if index.index_type == 'faiss':
            metadata_path = index.index_path.replace('.index', '_metadata.pkl')
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
        
        # Delete database record
        db.session.delete(index)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Index deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete index error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/<int:project_id>/targets', methods=['GET'])
def get_indexing_targets(project_id):
    """Get available targets for indexing"""
    try:
        project = Project.query.get_or_404(project_id)
        target_type = request.args.get('type', 'all')
        
        targets = {}
        
        if target_type in ['all', 'tables']:
            tables = TableInfo.query.filter_by(project_id=project_id).all()
            targets['tables'] = [
                {
                    'id': table.id,
                    'name': table.table_name,
                    'description': table.description,
                    'row_count': table.row_count,
                    'column_count': table.column_count
                }
                for table in tables
            ]
        
        if target_type in ['all', 'dictionary']:
            dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
            targets['dictionary'] = [
                {
                    'id': entry.id,
                    'term': entry.term,
                    'category': entry.category,
                    'definition': entry.definition[:100] + '...' if len(entry.definition) > 100 else entry.definition
                }
                for entry in dict_entries
            ]
        
        return jsonify({
            'status': 'success',
            'targets': targets
        })
        
    except Exception as e:
        current_app.logger.error(f"Get indexing targets error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """Delete an embedding model"""
    try:
        model = EmbeddingModel.query.get_or_404(model_id)
        
        # Check if model is used by any indexes
        indexes_count = SearchIndex.query.filter_by(embedding_model_id=model_id).count()
        if indexes_count > 0:
            return jsonify({
                'error': f'Cannot delete model. It is used by {indexes_count} search indexes.'
            }), 409
        
        # Delete model files
        import os
        import shutil
        if model.model_path and os.path.exists(model.model_path):
            # Delete the entire model directory
            model_dir = os.path.dirname(model.model_path)
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir)
        
        # Delete database record
        db.session.delete(model)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Embedding model deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete model error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/indexes/<int:index_id>/test', methods=['POST'])
def test_index_search(index_id):
    """Test search on a specific index"""
    try:
        index = SearchIndex.query.get_or_404(index_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        top_k = data.get('top_k', 10)
        
        if not index.is_built:
            return jsonify({'error': 'Index is not ready for search'}), 400
        
        # Perform search
        embedding_service = EmbeddingService()
        results = embedding_service.search_index(index_id, query, top_k)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'results': results,
            'index_name': index.index_name,
            'index_type': index.index_type
        })
        
    except Exception as e:
        current_app.logger.error(f"Test index search error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@embedding_bp.route('/<int:project_id>/models/download', methods=['POST'])
def download_model(project_id):
    """Download an embedding model"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('model_name'):
            return jsonify({'error': 'Model name is required'}), 400
        
        model_name = data['model_name']
        
        # Get Flask app instance BEFORE starting thread
        app = current_app._get_current_object()
        
        # Start download in background with proper Flask context
        embedding_service = EmbeddingService()
        
        def download_task():
            # CRITICAL: Use the app instance to create context
            with app.app_context():
                try:
                    result = embedding_service.download_model(project_id, model_name)
                    app.logger.info(f"Model download completed: {result}")
                except Exception as e:
                    app.logger.error(f"Model download failed: {str(e)}")
        
        # Start download thread
        thread = threading.Thread(target=download_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Model download started: {model_name}',
            'model_name': model_name
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Download model error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/<int:project_id>/indexes', methods=['POST'])
def create_index(project_id):
    """Create a new search index"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['index_name', 'index_type', 'target_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        index_name = data['index_name']
        index_type = data['index_type']
        target_type = data['target_type']
        target_ids = data.get('target_ids', [])
        embedding_model_id = data.get('embedding_model_id')
        config = data.get('config', {})
        
        # Validate embedding model for vector indexes
        if index_type in ['faiss'] and not embedding_model_id:
            return jsonify({'error': 'Embedding model is required for vector indexes'}), 400
        
        # CRITICAL: Check if model is locally downloaded and ready
        if embedding_model_id:
            model = EmbeddingModel.query.get(embedding_model_id)
            if not model:
                return jsonify({'error': 'Embedding model not found'}), 400
            if model.project_id != project_id:
                return jsonify({'error': 'Embedding model belongs to different project'}), 400
            if not model.is_downloaded or model.status != 'ready':
                return jsonify({
                    'error': f'Embedding model is not ready. Status: {model.status}. Please ensure the model is downloaded first.'
                }), 400
        
        # Validate targets
        if target_type == 'tables' and target_ids:
            tables = TableInfo.query.filter(
                TableInfo.id.in_(target_ids),
                TableInfo.project_id == project_id
            ).all()
            if len(tables) != len(target_ids):
                return jsonify({'error': 'Some target tables not found'}), 400
        
        # Create index record
        search_index = SearchIndex(
            project_id=project_id,
            index_name=index_name,
            index_type=index_type,
            target_type=target_type,
            embedding_model_id=embedding_model_id,
            status='building',
            build_progress=0.0,
            is_built=False
        )
        search_index.set_target_ids(target_ids)
        search_index.set_build_config(config)
        
        db.session.add(search_index)
        db.session.commit()
        
        # Get the index ID and Flask app instance BEFORE starting thread
        index_id = search_index.id
        app = current_app._get_current_object()
        
        # Start index creation in background with proper Flask context
        embedding_service = EmbeddingService()
        
        def create_index_task():
            # CRITICAL: Use the app instance to create context
            with app.app_context():
                try:
                    # Get fresh instance of index within this context
                    index = SearchIndex.query.get(index_id)
                    if not index:
                        app.logger.error(f"Index {index_id} not found in background task")
                        return
                    
                    app.logger.info(f"Starting {index_type} index creation: {index_name}")
                    
                    if index_type == 'faiss':
                        result = embedding_service.create_faiss_index(
                            project_id, embedding_model_id, index_name,
                            target_type, target_ids, config
                        )
                    elif index_type == 'tfidf':
                        result = embedding_service.create_tfidf_index(
                            project_id, index_name, target_type, target_ids, config
                        )
                    else:
                        result = {'status': 'error', 'message': f'Unsupported index type: {index_type}'}
                    
                    # Update index status based on result
                    if result['status'] == 'success':
                        index.status = 'ready'
                        index.is_built = True
                        index.build_progress = 100.0
                        app.logger.info(f"Index creation completed successfully: {index_name}")
                    else:
                        index.status = 'error'
                        index.error_message = result.get('message', 'Unknown error')
                        app.logger.error(f"Index creation failed: {index_name} - {result.get('message')}")
                    
                    db.session.commit()
                    
                except Exception as e:
                    # Update index status on error
                    try:
                        index = SearchIndex.query.get(index_id)
                        if index:
                            index.status = 'error'
                            index.error_message = str(e)
                            db.session.commit()
                    except:
                        pass  # If we can't update status, just log
                    app.logger.error(f"Index creation failed with exception: {str(e)}")
        
        # Start creation thread
        thread = threading.Thread(target=create_index_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Index creation started: {index_name}',
            'index': search_index.to_dict()
        }), 202
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Create index error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@embedding_bp.route('/<int:project_id>/indexes/rebuild', methods=['POST'])
def rebuild_indexes(project_id):
    """Rebuild all indexes for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        index_ids = data.get('index_ids', []) if data else []
        
        # Get indexes to rebuild
        if index_ids:
            indexes = SearchIndex.query.filter(
                SearchIndex.id.in_(index_ids),
                SearchIndex.project_id == project_id
            ).all()
        else:
            indexes = SearchIndex.query.filter_by(project_id=project_id).all()
        
        if not indexes:
            return jsonify({'error': 'No indexes found to rebuild'}), 404
        
        # Get index IDs and Flask app instance BEFORE starting thread
        rebuild_index_ids = [idx.id for idx in indexes]
        app = current_app._get_current_object()
        
        # Start rebuild in background with proper Flask context
        embedding_service = EmbeddingService()
        
        def rebuild_task():
            # CRITICAL: Use the app instance to create context
            with app.app_context():
                try:
                    for index_id in rebuild_index_ids:
                        # Get fresh instance of index within this context
                        index = SearchIndex.query.get(index_id)
                        if not index:
                            app.logger.warning(f"Index {index_id} not found during rebuild")
                            continue
                        
                        # Check if embedding model is still available for FAISS indexes
                        if index.index_type == 'faiss' and index.embedding_model_id:
                            model = EmbeddingModel.query.get(index.embedding_model_id)
                            if not model or not model.is_downloaded or model.status != 'ready':
                                index.status = 'error'
                                index.error_message = 'Embedding model not available for rebuild'
                                db.session.commit()
                                app.logger.error(f"Cannot rebuild {index.index_name}: embedding model not ready")
                                continue
                        
                        # Reset index status
                        index.status = 'building'
                        index.build_progress = 0.0
                        index.is_built = False
                        db.session.commit()
                        
                        app.logger.info(f"Rebuilding index: {index.index_name}")
                        
                        # Rebuild based on type
                        if index.index_type == 'faiss':
                            result = embedding_service.create_faiss_index(
                                index.project_id,
                                index.embedding_model_id,
                                index.index_name,
                                index.target_type,
                                index.get_target_ids(),
                                index.get_build_config()
                            )
                        elif index.index_type == 'tfidf':
                            result = embedding_service.create_tfidf_index(
                                index.project_id,
                                index.index_name,
                                index.target_type,
                                index.get_target_ids(),
                                index.get_build_config()
                            )
                        else:
                            result = {'status': 'error', 'message': f'Unsupported index type: {index.index_type}'}
                        
                        # Update index status
                        if result['status'] == 'success':
                            index.status = 'ready'
                            index.is_built = True
                            index.build_progress = 100.0
                        else:
                            index.status = 'error'
                            index.error_message = result.get('message', 'Rebuild failed')
                        
                        db.session.commit()
                        app.logger.info(f"Index rebuild completed: {index.index_name} - {result['status']}")
                        
                except Exception as e:
                    app.logger.error(f"Index rebuild failed: {str(e)}")
        
        # Start rebuild thread
        thread = threading.Thread(target=rebuild_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Rebuilding {len(indexes)} indexes',
            'rebuild_count': len(indexes)
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Rebuild indexes error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add endpoint to check local models status
@embedding_bp.route('/<int:project_id>/models/local', methods=['GET'])
def get_local_models(project_id):
    """Get locally downloaded models for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        models = EmbeddingModel.query.filter_by(
            project_id=project_id,
            is_downloaded=True,
            status='ready'
        ).all()
        
        return jsonify({
            'status': 'success',
            'local_models': [model.to_dict() for model in models],
            'count': len(models)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get local models error: {str(e)}")
        return jsonify({'error': str(e)}), 500

