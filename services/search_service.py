# services/search_service.py
import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz, process
import sqlite3
from flask import current_app
from models import SearchIndex, TableInfo, DataDictionary, db
from services.embedding_service import EmbeddingService

class SearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    def search_entities(self, project_id: int, query: str, entities: List[Dict[str, Any]],
                       search_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Search for entity mappings across all available indexes and methods"""
        config = search_config or {}
        results = {
            'semantic_results': [],
            'keyword_results': [],
            'fuzzy_results': [],
            'exact_results': [],
            'combined_results': []
        }
        
        try:
            # Get all available indexes for the project
            indexes = SearchIndex.query.filter_by(
                project_id=project_id,
                is_built=True,
                status='ready'
            ).all()
            
            # Search each entity
            for entity in entities:
                entity_text = entity.get('text', '')
                entity_type = entity.get('type', 'unknown')
                
                # Semantic search using embeddings
                semantic_matches = self._semantic_search(entity_text, indexes, config)
                results['semantic_results'].extend(semantic_matches)
                
                # Keyword search
                keyword_matches = self._keyword_search(project_id, entity_text, entity_type, config)
                results['keyword_results'].extend(keyword_matches)
                
                # Fuzzy string matching
                fuzzy_matches = self._fuzzy_search(project_id, entity_text, entity_type, config)
                results['fuzzy_results'].extend(fuzzy_matches)
                
                # Exact string matching
                exact_matches = self._exact_search(project_id, entity_text, entity_type, config)
                results['exact_results'].extend(exact_matches)
            
            # Combine and rank results
            results['combined_results'] = self._combine_and_rank_results(
                results, entities, config
            )
            
            return results
          
        except Exception as e:
            current_app.logger.error(f"Entity search error: {str(e)}")
            return results

    def search_by_method(self, project_id: int, query: str, method: str,
                        config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search using a specific method"""
        config = config or {}
        
        try:
            if method == 'semantic':
                indexes = SearchIndex.query.filter_by(
                    project_id=project_id,
                    index_type='faiss',
                    is_built=True,
                    status='ready'
                ).all()
                return self._semantic_search(query, indexes, config)
            
            elif method == 'keyword':
                return self._keyword_search(project_id, query, 'unknown', config)
            
            elif method == 'fuzzy':
                return self._fuzzy_search(project_id, query, 'unknown', config)
            
            elif method == 'exact':
                return self._exact_search(project_id, query, 'unknown', config)
            
            else:
                return []
                
        except Exception as e:
            current_app.logger.error(f"Method-specific search error: {str(e)}")
            return []
    
    def _semantic_search(self, query: str, indexes: List[SearchIndex], 
                        config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform semantic search using embedding indexes"""
        results = []
        top_k = config.get('semantic_top_k', 5)
        
        try:
            for index in indexes:
                if index.index_type in ['faiss']:
                    search_results = self.embedding_service.search_index(
                        index.id, query, top_k
                    )
                    
                    for result in search_results:
                        result['search_method'] = 'semantic'
                        result['index_id'] = index.id
                        result['index_name'] = index.index_name
                        result['query'] = query
                        results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Semantic search error: {str(e)}")
            return []
    
    def _keyword_search(self, project_id: int, query: str, entity_type: str,
                       config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform keyword search using TF-IDF or simple text matching"""
        results = []
        
        try:
            # Search in TF-IDF indexes
            tfidf_indexes = SearchIndex.query.filter_by(
                project_id=project_id,
                index_type='tfidf',
                is_built=True,
                status='ready'
            ).all()
            
            top_k = config.get('keyword_top_k', 5)
            
            for index in tfidf_indexes:
                search_results = self.embedding_service.search_index(
                    index.id, query, top_k
                )
                
                for result in search_results:
                    result['search_method'] = 'keyword'
                    result['index_id'] = index.id
                    result['index_name'] = index.index_name
                    result['query'] = query
                    results.append(result)
            
            # If no TF-IDF indexes, fall back to simple text matching
            if not tfidf_indexes:
                fallback_results = self._simple_keyword_search(project_id, query, entity_type, config)
                results.extend(fallback_results)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Keyword search error: {str(e)}")
            return []

    def _simple_keyword_search(self, project_id: int, query: str, entity_type: str,
                              config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple keyword search fallback"""
        results = []
        query_lower = query.lower()
        
        try:
            # Search table names
            if entity_type in ['table', 'unknown']:
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                
                for table in tables:
                    if query_lower in table.table_name.lower():
                        score = 1.0 if query_lower == table.table_name.lower() else 0.8
                        results.append({
                            'type': 'table',
                            'id': table.id,
                            'name': table.table_name,
                            'table_name': table.table_name,
                            'description': table.description,
                            'score': score,
                            'search_method': 'keyword',
                            'query': query,
                            'source': 'table_names'
                        })
            
            # Search column names
            if entity_type in ['column', 'unknown']:
                # Get columns from tables
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                
                for table in tables:
                    schema = table.get_schema()
                    columns = schema.get('columns', [])
                    
                    for column in columns:
                        column_name = column.get('name', '')
                        if query_lower in column_name.lower():
                            score = 1.0 if query_lower == column_name.lower() else 0.8
                            results.append({
                                'type': 'column',
                                'table_id': table.id,
                                'table_name': table.table_name,
                                'column_name': column_name,
                                'data_type': column.get('type'),
                                'score': score,
                                'search_method': 'keyword',
                                'query': query,
                                'source': 'column_names'
                            })
            
            # Search data dictionary
            if entity_type in ['business_term', 'unknown']:
                dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
                
                for entry in dict_entries:
                    if (query_lower in entry.term.lower() or 
                        (entry.definition and query_lower in entry.definition.lower())):
                        score = 1.0 if query_lower == entry.term.lower() else 0.8
                        results.append({
                            'type': 'dictionary',
                            'id': entry.id,
                            'term': entry.term,
                            'definition': entry.definition,
                            'score': score,
                            'search_method': 'keyword',
                            'query': query,
                            'source': 'data_dictionary'
                        })
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Simple keyword search error: {str(e)}")
            return []
    
    def _fuzzy_search(self, project_id: int, query: str, entity_type: str,
                     config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform fuzzy string matching"""
        results = []
        threshold = config.get('fuzzy_threshold', 70)
        
        try:
            # Search table names
            if entity_type in ['table', 'unknown']:
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                table_names = [(table.table_name, table.id, 'table') for table in tables]
                
                if table_names:
                    matches = process.extract(query, [name[0] for name in table_names],
                                            scorer=fuzz.ratio, limit=5)
                    
                    for match, score in matches:
                        if score >= threshold:
                            table_data = next((t for t in table_names if t[0] == match), None)
                            if table_data:
                                table_obj = next((t for t in tables if t.id == table_data[1]), None)
                                results.append({
                                    'type': 'table',
                                    'id': table_data[1],
                                    'name': table_data[0],
                                    'table_name': table_data[0],
                                    'description': table_obj.description if table_obj else None,
                                    'score': score / 100.0,
                                    'search_method': 'fuzzy',
                                    'query': query,
                                    'source': 'table_names'
                                })
            
            # Search column names
            if entity_type in ['column', 'unknown']:
                # Get all columns from all tables
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                column_data = []
                
                for table in tables:
                    schema = table.get_schema()
                    columns = schema.get('columns', [])
                    for column in columns:
                        column_data.append((column.get('name', ''), table.id, table.table_name, column.get('name', '')))
                
                if column_data:
                    matches = process.extract(query, [col[0] for col in column_data],
                                            scorer=fuzz.ratio, limit=5)
                    
                    for match, score in matches:
                        if score >= threshold:
                            col_data = next((c for c in column_data if c[0] == match), None)
                            if col_data:
                                results.append({
                                    'type': 'column',
                                    'table_id': col_data[1],
                                    'table_name': col_data[2],
                                    'column_name': col_data[3],
                                    'score': score / 100.0,
                                    'search_method': 'fuzzy',
                                    'query': query,
                                    'source': 'column_names'
                                })
            
            # Search data dictionary
            if entity_type in ['business_term', 'unknown']:
                dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
                dict_terms = [(entry.term, entry.id, 'dictionary') for entry in dict_entries]
                
                if dict_terms:
                    matches = process.extract(query, [term[0] for term in dict_terms],
                                            scorer=fuzz.ratio, limit=5)
                    
                    for match, score in matches:
                        if score >= threshold:
                            term_data = next((t for t in dict_terms if t[0] == match), None)
                            if term_data:
                                entry = next((e for e in dict_entries if e.id == term_data[1]), None)
                                results.append({
                                    'type': 'dictionary',
                                    'id': term_data[1],
                                    'term': term_data[0],
                                    'definition': entry.definition if entry else None,
                                    'score': score / 100.0,
                                    'search_method': 'fuzzy',
                                    'query': query,
                                    'source': 'data_dictionary'
                                })
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Fuzzy search error: {str(e)}")
            return []
    
    def _exact_search(self, project_id: int, query: str, entity_type: str,
                     config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform exact string matching"""
        results = []
        query_lower = query.lower()
        
        try:
            # Search table names
            if entity_type in ['table', 'unknown']:
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                
                for table in tables:
                    if query_lower in table.table_name.lower():
                        score = 1.0 if query_lower == table.table_name.lower() else 0.8
                        results.append({
                            'type': 'table',
                            'id': table.id,
                            'name': table.table_name,
                            'table_name': table.table_name,
                            'description': table.description,
                            'score': score,
                            'search_method': 'exact',
                            'query': query,
                            'source': 'table_names'
                        })
            
            # Search column names
            if entity_type in ['column', 'unknown']:
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                
                for table in tables:
                    schema = table.get_schema()
                    columns = schema.get('columns', [])
                    
                    for column in columns:
                        column_name = column.get('name', '')
                        if query_lower in column_name.lower():
                            score = 1.0 if query_lower == column_name.lower() else 0.8
                            results.append({
                                'type': 'column',
                                'table_id': table.id,
                                'table_name': table.table_name,
                                'column_name': column_name,
                                'data_type': column.get('type'),
                                'score': score,
                                'search_method': 'exact',
                                'query': query,
                                'source': 'column_names'
                            })
            
            # Search data dictionary
            if entity_type in ['business_term', 'unknown']:
                dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
                
                for entry in dict_entries:
                    # Search in term
                    if query_lower in entry.term.lower():
                        score = 1.0 if query_lower == entry.term.lower() else 0.9
                        results.append({
                            'type': 'dictionary',
                            'id': entry.id,
                            'term': entry.term,
                            'definition': entry.definition,
                            'score': score,
                            'search_method': 'exact',
                            'query': query,
                            'source': 'dictionary_terms'
                        })
                    
                    # Search in definition
                    elif entry.definition and query_lower in entry.definition.lower():
                        results.append({
                            'type': 'dictionary',
                            'id': entry.id,
                            'term': entry.term,
                            'definition': entry.definition,
                            'score': 0.7,
                            'search_method': 'exact',
                            'query': query,
                            'source': 'dictionary_definitions'
                        })
                    
                    # Search in aliases if available
                    try:
                        aliases = entry.get_aliases() if hasattr(entry, 'get_aliases') else []
                        for alias in aliases:
                            if query_lower in alias.lower():
                                score = 0.9 if query_lower == alias.lower() else 0.7
                                results.append({
                                    'type': 'dictionary',
                                    'id': entry.id,
                                    'term': entry.term,
                                    'definition': entry.definition,
                                    'matched_alias': alias,
                                    'score': score,
                                    'search_method': 'exact',
                                    'query': query,
                                    'source': 'dictionary_aliases'
                                })
                    except:
                        pass  # Skip if aliases not available
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Exact search error: {str(e)}")
            return []
    
    def _combine_and_rank_results(self, all_results: Dict[str, List], entities: List[Dict],
                                 config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine and rank results from different search methods"""
        try:
            # Weight configuration
            weights = config.get('method_weights', {
                'exact': 1.0,
                'semantic': 0.8,
                'fuzzy': 0.6,
                'keyword': 0.7
            })
            
            # Collect all results with weighted scores
            combined = []
            seen_items = set()
            
            for method, results in all_results.items():
                if method == 'combined_results':
                    continue
                    
                method_name = method.replace('_results', '')
                weight = weights.get(method_name, 0.5)
                
                for result in results:
                    # Create unique identifier for deduplication
                    if result.get('type') == 'table':
                        item_id = f"table_{result.get('id')}"
                    elif result.get('type') == 'column':
                        item_id = f"column_{result.get('table_id')}_{result.get('column_name')}"
                    elif result.get('type') == 'dictionary':
                        item_id = f"dict_{result.get('id')}"
                    else:
                        item_id = f"{result.get('type')}_{result.get('id', '')}"
                    
                    # Calculate weighted score
                    original_score = result.get('score', 0.0)
                    weighted_score = original_score * weight
                    
                    # Check if we've seen this item before
                    if item_id in seen_items:
                        # Find existing item and update score if higher
                        for existing in combined:
                            if existing.get('item_id') == item_id:
                                if weighted_score > existing.get('weighted_score', 0):
                                    existing.update(result)
                                    existing['weighted_score'] = weighted_score
                                    existing['search_methods'] = existing.get('search_methods', [])
                                    if method_name not in existing['search_methods']:
                                        existing['search_methods'].append(method_name)
                                break
                    else:
                        # Add new item
                        result['item_id'] = item_id
                        result['weighted_score'] = weighted_score
                        result['search_methods'] = [method_name]
                        combined.append(result)
                        seen_items.add(item_id)
            
            # Sort by weighted score
            combined.sort(key=lambda x: x.get('weighted_score', 0), reverse=True)
            
            # Add confidence and ranking
            for i, result in enumerate(combined):
                result['rank'] = i + 1
                result['confidence'] = round(result.get('weighted_score', 0), 3)
                
                # Remove internal fields
                result.pop('item_id', None)
                result.pop('weighted_score', None)
            
            # Limit results
            max_results = config.get('max_combined_results', 20)
            return combined[:max_results]
            
        except Exception as e:
            current_app.logger.error(f"Result combination error: {str(e)}")
            return []

    def get_table_schema_context(self, project_id: int, table_ids: List[int] = None) -> Dict[str, Any]:
        """Get schema context for tables in a project"""
        try:
            query = TableInfo.query.filter_by(project_id=project_id)
            if table_ids:
                query = query.filter(TableInfo.id.in_(table_ids))
            
            tables = query.all()
            
            context = {
                'tables': {},
                'relationships': [],
                'dictionary': []
            }
            
            # Build table schemas
            for table in tables:
                schema = table.get_schema()
                context['tables'][table.table_name] = {
                    'id': table.id,
                    'columns': schema.get('columns', []),
                    'description': table.description,
                    'row_count': table.row_count,
                    'sample_data': table.get_sample_data()[:3]  # Limit sample data
                }
            
            # Get dictionary terms
            dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
            context['dictionary'] = [entry.to_dict() for entry in dict_entries]
            
            return context
            
        except Exception as e:
            current_app.logger.error(f"Schema context error: {str(e)}")
            return {'tables': {}, 'relationships': [], 'dictionary': []}

    def execute_sql_query(self, project_id: int, sql_query: str, 
                        limit: int = 100) -> Dict[str, Any]:
        """Execute SQL query on project data"""
        try:
            import os
            # Security validation
            sql_lower = sql_query.lower().strip()
            
            # Only allow SELECT statements
            if not sql_lower.startswith('select'):
                return {'error': 'Only SELECT statements are allowed'}
            
            # Prevent dangerous operations
            dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create', 'truncate']
            if any(keyword in sql_lower for keyword in dangerous_keywords):
                return {'error': 'Dangerous SQL operations are not allowed'}
            
            # Get the main application database path with better error handling
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            current_app.logger.info(f"Database URI: {db_uri}")
            
            db_path = None
            
            # Handle different SQLite URI formats
            # if db_uri.startswith('sqlite:///'):
            #     db_path = db_uri.replace('sqlite:///', '')
            # elif db_uri.startswith('sqlite://'):
            #     db_path = db_uri.replace('sqlite://', '')
            # elif db_uri.startswith('sqlite:'):
            #     db_path = db_uri.replace('sqlite:', '')
            # else:
            # Fallback: try common database names
            possible_paths = [
                # 'instance/queryforge.db',
                # os.path.join(os.getcwd(), 'instance/queryforge.db'), 
                # os.path.join(os.getcwd(), 'instance', 'queryforge.db'),
                os.path.join(os.getcwd(), 'uploads', f'project_{project_id}.db'),
                # os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'queryforge.db')
            ]

            for path in possible_paths:
                abs_path = os.path.abspath(path)
                current_app.logger.info(f"Checking database path: {abs_path}")
                if os.path.exists(abs_path):
                    db_path = abs_path
                    break
            
            if not db_path:
                return {'error': f'Could not locate database. URI: {db_uri}, Checked paths: {possible_paths}'}
        
            # Make path absolute if it's relative
            if db_path and not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
            
            current_app.logger.info(f"Final database path: {db_path}")
            
            # Check if database file exists
            if not db_path or not os.path.exists(db_path):
                # Additional debugging - list files in current directory
                current_dir = os.getcwd()
                files_in_dir = [f for f in os.listdir(current_dir) if f.endswith('.db')]
                
                return {
                    'error': f'Database file not found at: {db_path}. Current directory: {current_dir}. DB files found: {files_in_dir}. URI was: {db_uri}'
                }
            
            # Try to access the database using SQLAlchemy's connection first
            try:
                # Use the Flask app's database connection
                with current_app.app_context():
                    # Use db.session to execute raw SQL
                    from sqlalchemy import text
                    
                    # Add LIMIT if not present
                    # if 'limit' not in sql_lower:
                    #     sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
                    # sql_query += ";"
                    # sql_query = """SELECT 
                    #                     description, 
                    #                     ROUND(estimated_monthly_cost, 3) as monthly_cost 
                    #                 FROM azure_components_sheet1 
                    #                 WHERE service_category = 'DevOps' 
                    #                 LIMIT 10"""
                    print(f"Executing SQLAlchemy query: {sql_query}")
                    # Execute query using SQLAlchemy
                    result = db.session.execute(text(sql_query))
                    rows = result.fetchall()
                    
                    # Get column names
                    columns = list(result.keys()) if rows else []
                    
                    # Convert to list of dicts
                    results = []
                    for row in rows:
                        # Convert Row object to dict
                        row_dict = {}
                        for i, col in enumerate(columns):
                            row_dict[col] = row[i] if i < len(row) else None
                        results.append(row_dict)
                    
                    return {
                        'status': 'success',
                        'data': results,
                        'row_count': len(results),
                        'columns': columns,
                        'query': sql_query,
                        'method': 'sqlalchemy'
                    }
                    
            except Exception as sqlalchemy_error:
                current_app.logger.warning(f"SQLAlchemy execution failed: {sqlalchemy_error}")
                # Fall back to direct SQLite connection
                pass
            
            # Fallback: Direct SQLite connection
            current_app.logger.info(f"Using direct SQLite connection to: {db_path}")
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            # Add LIMIT if not present
            if 'limit' not in sql_lower:
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
            
            # Execute the query
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert to list of dicts
            results = []
            columns = []
            if rows:
                columns = [description[0] for description in cursor.description]
                for row in rows:
                    results.append(dict(zip(columns, row)))
            
            conn.close()
            
            return {
                'status': 'success',
                'data': results,
                'row_count': len(results),
                'columns': columns,
                'query': sql_query,
                'method': 'sqlite'
            }
            
        except sqlite3.Error as e:
            current_app.logger.error(f"SQL execution error: {str(e)}")
            return {'error': f'SQL error: {str(e)}'}
        except Exception as e:
            current_app.logger.error(f"SQL execution error: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return {'error': str(e)}


    def debug_database_info(self) -> Dict[str, Any]:
        """Debug method to check database information"""
        try:
            db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
            current_dir = os.getcwd()
            
            # List all .db files in current directory and subdirectories
            db_files = []
            for root, dirs, files in os.walk(current_dir):
                for file in files:
                    if file.endswith('.db'):
                        db_files.append(os.path.join(root, file))
            
            # Check if we can connect to the main database
            connection_test = False
            try:
                with current_app.app_context():
                    db.session.execute('SELECT 1')
                    connection_test = True
            except:
                pass
            
            return {
                'database_uri': db_uri,
                'current_directory': current_dir,
                'db_files_found': db_files,
                'sqlalchemy_connection': connection_test,
                'config_loaded': bool(current_app.config)
            }
        except Exception as e:
            return {'error': str(e)}

    def _get_project_db_path(self, project_id: int) -> str:
        """Get the database path for a project"""
        return f"data/project_{project_id}.db"