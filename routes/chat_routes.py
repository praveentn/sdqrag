# routes/chat_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import ChatHistory, Project, User, db
from services.llm_service import LLMService
from services.search_service import SearchService
from datetime import datetime
import uuid
import time
import traceback

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/<int:project_id>/llm-status', methods=['GET'])
def check_llm_status(project_id):
    """Check if LLM service is available"""
    try:
        llm_service = LLMService()
        is_available = llm_service.is_available()
        
        return jsonify({
            'status': 'success',
            'available': is_available,
            'message': 'LLM service available' if is_available else 'LLM service not configured'
        })
        
    except Exception as e:
        current_app.logger.error(f"LLM status check error: {str(e)}")
        return jsonify({
            'status': 'success',
            'available': False,
            'message': f'LLM service error: {str(e)}'
        })

@chat_bp.route('/<int:project_id>/sessions', methods=['GET'])
def get_chat_sessions(project_id):
    """Get all chat sessions for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Get distinct session IDs with latest timestamp
        sessions_query = db.session.query(
            ChatHistory.session_id,
            db.func.max(ChatHistory.created_at).label('last_activity'),
            db.func.count(ChatHistory.id).label('query_count')
        ).filter_by(project_id=project_id).group_by(ChatHistory.session_id)
        
        sessions = sessions_query.all()
        
        session_list = []
        for session in sessions:
            # Get first query for session name
            first_chat = ChatHistory.query.filter_by(
                project_id=project_id,
                session_id=session.session_id
            ).order_by(ChatHistory.created_at).first()
            
            session_list.append({
                'session_id': session.session_id,
                'last_activity': session.last_activity.isoformat() if session.last_activity else None,
                'query_count': session.query_count,
                'first_query': first_chat.user_query[:100] + '...' if first_chat and len(first_chat.user_query) > 100 else first_chat.user_query if first_chat else ''
            })
        
        # Sort by last activity
        session_list.sort(key=lambda x: x['last_activity'] or '', reverse=True)
        
        return jsonify({
            'status': 'success',
            'sessions': session_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Get chat sessions error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/<int:project_id>/sessions/<session_id>', methods=['GET'])
def get_chat_history(project_id, session_id):
    """Get chat history for a specific session"""
    try:
        project = Project.query.get_or_404(project_id)
        
        chats = ChatHistory.query.filter_by(
            project_id=project_id,
            session_id=session_id
        ).order_by(ChatHistory.created_at).all()
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'chat_history': [chat.to_dict() for chat in chats]
        })
        
    except Exception as e:
        current_app.logger.error(f"Get chat history error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/<int:project_id>/query', methods=['POST'])
def process_natural_language_query(project_id):
    """Process a natural language query with step-by-step confirmation"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        session_id = data.get('session_id', str(uuid.uuid4()))
        step = data.get('step', 'extract_entities')
        confirmation_data = data.get('confirmation_data', {})
        
        # Get default user
        user = User.query.filter_by(username='admin').first()
        
        start_time = time.time()
        
        # Initialize or get existing chat record
        chat = ChatHistory.query.filter_by(
            project_id=project_id,
            session_id=session_id,
            user_query=query
        ).first()
        
        if not chat:
            chat = ChatHistory(
                project_id=project_id,
                session_id=session_id,
                user_query=query,
                created_by=user.id if user else None,
                status='pending'
            )
            db.session.add(chat)
            db.session.commit()
        
        # Step 1: Extract entities
        if step == 'extract_entities':
            result = _extract_entities_step(project_id, query, chat)
        
        # Step 2: Confirm entities and find mappings
        elif step == 'confirm_entities':
            result = _confirm_entities_step(project_id, query, chat, confirmation_data)
        
        # Step 3: Confirm mappings and select tables
        elif step == 'confirm_mappings':
            result = _confirm_mappings_step(project_id, query, chat, confirmation_data)
        
        # Step 4: Generate and confirm SQL
        elif step == 'generate_sql':
            result = _generate_sql_step(project_id, query, chat, confirmation_data)
        
        # Step 5: Execute SQL
        elif step == 'execute_sql':
            result = _execute_sql_step(project_id, query, chat, confirmation_data)
        
        # Step 6: Process feedback and regenerate
        elif step == 'process_feedback':
            result = _process_feedback_step(project_id, query, chat, confirmation_data)
        
        else:
            return jsonify({'error': f'Invalid step: {step}'}), 400
        
        # Update processing time
        processing_time = time.time() - start_time
        chat.processing_time = processing_time
        db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Process NL query error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def _extract_entities_step(project_id, query, chat):
    """Step 1: Extract entities from query"""
    try:
        # Get schema context
        search_service = SearchService()
        schema_context = search_service.get_table_schema_context(project_id)
        
        # Extract entities using LLM
        llm_service = LLMService()
        if not llm_service.is_available():
            return {
                'status': 'error',
                'message': 'LLM service not available. Please configure Azure OpenAI settings.'
            }
        
        entity_result = llm_service.extract_entities(query, schema_context)
        
        if 'error' in entity_result:
            chat.status = 'error'
            chat.error_message = entity_result['error']
            db.session.commit()
            return {
                'status': 'error',
                'message': entity_result['error']
            }
        
        entities = entity_result.get('entities', [])
        
        if not entities:
            return {
                'status': 'error',
                'message': 'No entities found in the query. Please try rephrasing your question.'
            }
        
        # Save entities
        chat.set_extracted_entities(entities)
        
        # Set confirmation step
        confirmation_steps = {
            'current_step': 'confirm_entities',
            'next_step': 'confirm_mappings',
            'extracted_entities': entities
        }
        chat.set_confirmation_steps(confirmation_steps)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'confirm_entities',
            'session_id': chat.session_id,
            'entities': entities,
            'message': 'Entities extracted. Please confirm the identified entities.',
            'next_action': 'User should review and confirm entities'
        }
        
    except Exception as e:
        current_app.logger.error(f"Extract entities step error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        chat.status = 'error'
        chat.error_message = str(e)
        db.session.commit()
        return {'status': 'error', 'message': str(e)}

def _confirm_entities_step(project_id, query, chat, confirmation_data):
    """Step 2: Confirm entities and find mappings"""
    try:
        confirmed_entities = confirmation_data.get('confirmed_entities', [])
        
        if not confirmed_entities:
            return {
                'status': 'error',
                'message': 'No entities confirmed'
            }
        
        # Search for entity mappings
        search_service = SearchService()
        mapping_results = search_service.search_entities(project_id, query, confirmed_entities)
        
        # Save entity mappings
        chat.set_entity_mappings(mapping_results)
        
        # Set confirmation step
        confirmation_steps = {
            'current_step': 'confirm_mappings',
            'next_step': 'generate_sql',
            'confirmed_entities': confirmed_entities,
            'mapping_results': mapping_results
        }
        chat.set_confirmation_steps(confirmation_steps)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'confirm_mappings',
            'session_id': chat.session_id,
            'confirmed_entities': confirmed_entities,
            'mapping_results': mapping_results,
            'message': 'Entity mappings found. Please confirm the table and column mappings.',
            'next_action': 'User should review and confirm mappings'
        }
        
    except Exception as e:
        current_app.logger.error(f"Confirm entities step error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def _confirm_mappings_step(project_id, query, chat, confirmation_data):
    """Step 3: Confirm mappings and prepare for SQL generation"""
    try:
        confirmed_mappings = confirmation_data.get('confirmed_mappings', [])
        
        if not confirmed_mappings:
            return {
                'status': 'error',
                'message': 'No mappings confirmed'
            }
        
        # Extract table IDs from mappings
        table_ids = set()
        for mapping in confirmed_mappings:
            if mapping.get('type') == 'table':
                table_ids.add(mapping.get('id'))
            elif mapping.get('type') == 'column':
                table_ids.add(mapping.get('table_id'))
        
        # Get detailed schema context
        search_service = SearchService()
        schema_context = search_service.get_table_schema_context(project_id, list(table_ids))
        
        # Update confirmation step
        confirmation_steps = {
            'current_step': 'generate_sql',
            'next_step': 'execute_sql',
            'confirmed_mappings': confirmed_mappings,
            'selected_mappings': confirmed_mappings,
            'schema_context': schema_context
        }
        chat.set_confirmation_steps(confirmation_steps)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'generate_sql',
            'session_id': chat.session_id,
            'confirmed_mappings': confirmed_mappings,
            'schema_context': schema_context,
            'message': 'Mappings confirmed. Ready to generate SQL query.',
            'next_action': 'User should confirm to generate SQL'
        }
        
    except Exception as e:
        current_app.logger.error(f"Confirm mappings step error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def _generate_sql_step(project_id, query, chat, confirmation_data):
    """Step 4: Generate and confirm SQL"""
    try:
        # Get confirmation data
        confirmation_steps = chat.get_confirmation_steps()
        schema_context = confirmation_steps.get('schema_context', {})
        selected_mappings = confirmation_steps.get('selected_mappings', [])
        entities = chat.get_extracted_entities()
        
        # Generate SQL using LLM
        llm_service = LLMService()
        if not llm_service.is_available():
            return {
                'status': 'error',
                'message': 'LLM service not available'
            }
        
        sql_result = llm_service.generate_sql(
            query, entities, selected_mappings, schema_context
        )
        
        if 'error' in sql_result:
            return {
                'status': 'error',
                'message': sql_result['error']
            }
        
        generated_sql = sql_result.get('sql', '')
        
        # Save generated SQL
        chat.generated_sql = generated_sql
        
        # Update confirmation step
        confirmation_steps['current_step'] = 'execute_sql'
        confirmation_steps['generated_sql'] = generated_sql
        confirmation_steps['sql_metadata'] = sql_result
        chat.set_confirmation_steps(confirmation_steps)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'execute_sql',
            'session_id': chat.session_id,
            'generated_sql': generated_sql,
            'sql_metadata': sql_result,
            'message': 'SQL query generated. Please review and confirm execution.',
            'next_action': 'User should confirm SQL execution'
        }
        
    except Exception as e:
        current_app.logger.error(f"Generate SQL step error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def _execute_sql_step(project_id, query, chat, confirmation_data):
    """Step 5: Execute SQL and generate final response"""
    try:
        # Get SQL from chat
        sql_query = chat.generated_sql
        
        if not sql_query:
            return {
                'status': 'error',
                'message': 'No SQL query to execute'
            }
        
        # Execute SQL
        search_service = SearchService()
        sql_result = search_service.execute_sql_query(project_id, sql_query)
        
        if 'error' in sql_result:
            chat.status = 'error'
            chat.error_message = sql_result['error']
            db.session.commit()
            return {
                'status': 'error',
                'message': sql_result['error']
            }
        
        # Save SQL results
        chat.set_sql_results(sql_result['data'])
        
        # Generate final response using LLM
        llm_service = LLMService()
        if llm_service.is_available():
            final_response_result = llm_service.generate_final_response(
                query, sql_query, sql_result['data']
            )
            final_response = final_response_result.get('response', 'Query completed successfully.')
        else:
            final_response = f"Found {len(sql_result['data'])} results for your query."
        
        # Update chat record
        chat.final_response = final_response
        chat.status = 'completed'
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'completed',
            'session_id': chat.session_id,
            'sql_query': sql_query,
            'results': sql_result['data'],
            'result_count': len(sql_result['data']),
            'final_response': final_response,
            'message': 'Query completed successfully.',
            'next_action': 'User can provide feedback or ask a new question'
        }
        
    except Exception as e:
        current_app.logger.error(f"Execute SQL step error: {str(e)}")
        chat.status = 'error'
        chat.error_message = str(e)
        db.session.commit()
        return {'status': 'error', 'message': str(e)}

def _process_feedback_step(project_id, query, chat, confirmation_data):
    """Step 6: Process user feedback and regenerate"""
    try:
        feedback = confirmation_data.get('feedback', '')
        
        if not feedback:
            return {
                'status': 'error',
                'message': 'No feedback provided'
            }
        
        # Save feedback
        chat.user_feedback = feedback
        
        # Reset status for regeneration
        chat.status = 'pending'
        
        # Get previous entities and mappings
        entities = chat.get_extracted_entities()
        mappings = chat.get_entity_mappings()
        
        # Incorporate feedback into entity extraction
        enhanced_query = f"{query} (User feedback: {feedback})"
        
        # Re-extract entities with feedback
        search_service = SearchService()
        schema_context = search_service.get_table_schema_context(project_id)
        
        llm_service = LLMService()
        if llm_service.is_available():
            entity_result = llm_service.extract_entities(enhanced_query, schema_context)
            
            if 'error' not in entity_result:
                entities = entity_result.get('entities', [])
                chat.set_extracted_entities(entities)
        
        # Update confirmation step to restart from entity confirmation
        confirmation_steps = {
            'current_step': 'confirm_entities',
            'next_step': 'confirm_mappings',
            'extracted_entities': entities,
            'user_feedback': feedback,
            'regeneration': True
        }
        chat.set_confirmation_steps(confirmation_steps)
        
        db.session.commit()
        
        return {
            'status': 'success',
            'step': 'confirm_entities',
            'session_id': chat.session_id,
            'entities': entities,
            'feedback_processed': feedback,
            'message': 'Feedback processed. Please confirm the updated entities.',
            'next_action': 'User should review and confirm updated entities'
        }
        
    except Exception as e:
        current_app.logger.error(f"Process feedback step error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

@chat_bp.route('/<int:project_id>/sessions/<session_id>', methods=['DELETE'])
def delete_chat_session(project_id, session_id):
    """Delete a chat session"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Delete all chats in the session
        chats = ChatHistory.query.filter_by(
            project_id=project_id,
            session_id=session_id
        ).all()
        
        for chat in chats:
            db.session.delete(chat)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Chat session deleted: {len(chats)} queries removed'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete chat session error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/<int:project_id>/quick-query', methods=['POST'])
def quick_query(project_id):
    """Quick query without step-by-step confirmation (for testing)"""
    try:
        from sqlalchemy import text

        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        session_id = str(uuid.uuid4())
        
        # Get default user
        user = User.query.filter_by(username='admin').first()
        
        start_time = time.time()
        
        # Create chat record
        chat = ChatHistory(
            project_id=project_id,
            session_id=session_id,
            user_query=query,
            created_by=user.id if user else None,
            status='pending'
        )
        db.session.add(chat)
        db.session.commit()
        
        try:
            # Get services
            search_service = SearchService()
            llm_service = LLMService()
            
            # Check LLM availability
            if not llm_service.is_available():
                raise Exception("LLM service not available. Please configure Azure OpenAI settings.")
            
            # Get schema context
            schema_context = search_service.get_table_schema_context(project_id)
            current_app.logger.info(f"Schema context tables: {list(schema_context.get('tables', {}).keys())}")
            
            # Extract entities
            entity_result = llm_service.extract_entities(query, schema_context)
            if 'error' in entity_result:
                raise Exception(f"Entity extraction failed: {entity_result['error']}")
                
            entities = entity_result.get('entities', [])
            if not entities:
                raise Exception("No entities found in the query. Please try rephrasing your question.")
            
            current_app.logger.info(f"Extracted entities: {entities}")
            chat.set_extracted_entities(entities)
            
            # Search for mappings
            mapping_results = search_service.search_entities(project_id, query, entities)
            chat.set_entity_mappings(mapping_results)
            
            # Use top mappings automatically
            combined_results = mapping_results.get('combined_results', [])
            if not combined_results:
                # If no combined results, try using any available mappings
                all_mappings = []
                for method_results in mapping_results.values():
                    if isinstance(method_results, list):
                        all_mappings.extend(method_results)
                
                if not all_mappings:
                    raise Exception("No entity mappings found. Please ensure your data is properly indexed.")
                
                combined_results = all_mappings[:5]
            
            top_mappings = combined_results[:5]  # Use top 5 mappings
            current_app.logger.info(f"Top mappings: {[m.get('name') or m.get('table_name') for m in top_mappings]}")
            
            # Extract table IDs
            table_ids = set()
            for mapping in top_mappings:
                if mapping.get('type') == 'table':
                    table_ids.add(mapping.get('id'))
                elif mapping.get('type') == 'column':
                    table_ids.add(mapping.get('table_id'))
            
            # Get detailed schema
            detailed_schema = search_service.get_table_schema_context(project_id, list(table_ids))
            current_app.logger.info(f"Detailed schema tables: {list(detailed_schema.get('tables', {}).keys())}")
            
            # Generate SQL
            sql_result = llm_service.generate_sql(query, entities, top_mappings, detailed_schema)
            if 'error' in sql_result:
                raise Exception(f"SQL generation failed: {sql_result['error']}")
            
            generated_sql = sql_result.get('sql', '')
            current_app.logger.info(f"Generated SQL for query '{query}': {generated_sql}")
            
            chat.generated_sql = generated_sql
            
            # Execute SQL with enhanced error handling
            execution_result = search_service.execute_sql_query(project_id, generated_sql)
            if 'error' in execution_result:
                current_app.logger.error(f"SQL execution failed. SQL: {generated_sql}")
                current_app.logger.error(f"Error: {execution_result['error']}")
                
                # Try to suggest corrections if it's a table name issue
                if 'no such table' in execution_result['error'].lower():
                    try:
                        # Get actual table names from database
                        actual_tables_result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                        actual_table_names = [row[0] for row in actual_tables_result]
                        current_app.logger.error(f"Available tables in database: {actual_table_names}")
                        
                        # Try to find a similar table name
                        import difflib
                        table_mentioned = execution_result['error'].split('no such table: ')[-1].strip()
                        similar_tables = difflib.get_close_matches(table_mentioned, actual_table_names, n=3, cutoff=0.4)
                        if similar_tables:
                            current_app.logger.info(f"Similar table names found: {similar_tables}")
                            
                            # Try correcting the SQL with the most similar table name
                            corrected_sql = generated_sql.replace(table_mentioned, similar_tables[0])
                            current_app.logger.info(f"Trying corrected SQL: {corrected_sql}")
                            
                            corrected_result = search_service.execute_sql_query(project_id, corrected_sql)
                            if corrected_result.get('status') == 'success':
                                current_app.logger.info("Corrected SQL worked!")
                                execution_result = corrected_result
                                generated_sql = corrected_sql
                                chat.generated_sql = corrected_sql
                        else:
                            # If no similar tables, try using the first available table
                            if actual_table_names:
                                fallback_sql = f"SELECT * FROM {actual_table_names[0]} LIMIT 10"
                                current_app.logger.info(f"Trying fallback SQL: {fallback_sql}")
                                fallback_result = search_service.execute_sql_query(project_id, fallback_sql)
                                if fallback_result.get('status') == 'success':
                                    execution_result = fallback_result
                                    generated_sql = fallback_sql
                                    chat.generated_sql = fallback_sql
                    except Exception as table_correction_error:
                        current_app.logger.error(f"Table correction attempt failed: {table_correction_error}")
                
                if 'error' in execution_result:
                    raise Exception(f"SQL execution failed: {execution_result['error']}")
            
            results_data = execution_result['data']
            chat.set_sql_results(results_data)
            
            # Generate final response
            final_response_result = llm_service.generate_final_response(
                query, generated_sql, results_data
            )
            final_response = final_response_result.get('response', 'Query completed successfully.')
            
            # Update chat record
            chat.final_response = final_response
            chat.status = 'completed'
            chat.processing_time = time.time() - start_time
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'sql_query': generated_sql,
                'results': results_data,
                'result_count': len(results_data),
                'final_response': final_response,
                'processing_time': round(chat.processing_time, 3),
                'entities_extracted': len(entities),
                'mappings_found': len(combined_results),
                'debug_info': {
                    'available_tables': list(detailed_schema.get('tables', {}).keys()),
                    'sql_confidence': sql_result.get('confidence', 0)
                }
            })
            
        except Exception as e:
            # Update chat with error
            chat.status = 'error'
            chat.error_message = str(e)
            chat.processing_time = time.time() - start_time
            db.session.commit()
            
            current_app.logger.error(f"Quick query error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"Quick query setup error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/<int:project_id>/debug-db', methods=['GET'])
def debug_database_info(project_id):
    """Debug endpoint to check database configuration"""
    try:
        import os
        from services.search_service import SearchService
        from sqlalchemy import text

        search_service = SearchService()
        
        # Get database URI and current directory info
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        current_dir = os.getcwd()
        
        # List all .db files in current directory and subdirectories
        db_files = []
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                if file.endswith('.db'):
                    full_path = os.path.join(root, file)
                    size = os.path.getsize(full_path)
                    db_files.append({
                        'path': full_path,
                        'size_mb': round(size / (1024*1024), 2),
                        'relative_path': os.path.relpath(full_path, current_dir)
                    })
        
        # Test SQLAlchemy connection
        sqlalchemy_test = False
        table_count = 0
        try:
            with current_app.app_context():
                result = db.session.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"')
                table_count = result.scalar()
                sqlalchemy_test = True
        except Exception as e:
            sqlalchemy_error = str(e)
        
        # Test direct file access to the resolved database path
        resolved_path = None
        if db_uri.startswith('sqlite:///'):
            resolved_path = db_uri.replace('sqlite:///', '')
        elif db_uri.startswith('sqlite://'):
            resolved_path = db_uri.replace('sqlite://', '')
        
        if resolved_path and not os.path.isabs(resolved_path):
            resolved_path = os.path.abspath(resolved_path)
        
        # Check project tables
        project_tables = []
        try:
            from models import TableInfo
            tables = TableInfo.query.filter_by(project_id=project_id).all()
            project_tables = [{'id': t.id, 'name': t.table_name, 'row_count': t.row_count} for t in tables]
        except Exception as e:
            project_tables_error = str(e)
        
        return jsonify({
            'status': 'success',
            'debug_info': {
                'database_uri': db_uri,
                'current_directory': current_dir,
                'resolved_db_path': resolved_path,
                'resolved_path_exists': os.path.exists(resolved_path) if resolved_path else False,
                'db_files_found': db_files,
                'sqlalchemy_connection_works': sqlalchemy_test,
                'table_count_in_db': table_count,
                'project_tables': project_tables,
                'project_id': project_id
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Debug database info error: {str(e)}")
        return jsonify({'error': str(e)}), 500

