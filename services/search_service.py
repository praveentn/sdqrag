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
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Keyword search error: {str(e)}")
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
                
                matches = process.extract(query, [name[0] for name in table_names], 
                                        scorer=fuzz.ratio, limit=5)
                
                for match, score in matches:
                    if score >= threshold:
                        table_data = next((t for t in table_names if t[0] == match), None)
                        if table_data:
                            results.append({
                                'type': 'table',
                                'id': table_data[1],
                                'name': table_data[0],
                                'score': score / 100.0,  # Normalize to 0-1
                                'search_method': 'fuzzy',
                                'query': query,
                                'source': 'table_names'
                            })
            
            # Search column names
            if entity_type in ['column', 'unknown']:
                tables = TableInfo.query.filter_by(project_id=project_id).all()
                column_data = []
                
                for table in tables:
                    schema = table.get_schema()
                    for column in schema.get('columns', []):
                        column_data.append((
                            column['name'], 
                            table.id, 
                            table.table_name,
                            column['name']
                        ))
                
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
                                results.append({
                                    'type': 'dictionary',
                                    'id': term_data[1],
                                    'term': term_data[0],
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
                    for column in schema.get('columns', []):
                        column_name = column['name'].lower()
                        if query_lower in column_name:
                            score = 1.0 if query_lower == column_name else 0.8
                            results.append({
                                'type': 'column',
                                'table_id': table.id,
                                'table_name': table.table_name,
                                'column_name': column['name'],
                                'score': score,
                                'search_method': 'exact',
                                'query': query,
                                'source': 'column_names'
                            })
            
            # Search data dictionary
            if entity_type in ['business_term', 'unknown']:
                dict_entries = DataDictionary.query.filter_by(project_id=project_id).all()
                
                for entry in dict_entries:
                    term_lower = entry.term.lower()
                    if query_lower in term_lower:
                        score = 1.0 if query_lower == term_lower else 0.8
                        results.append({
                            'type': 'dictionary',
                            'id': entry.id,
                            'term': entry.term,
                            'definition': entry.definition,
                            'score': score,
                            'search_method': 'exact',
                            'query': query,
                            'source': 'data_dictionary'
                        })
                    
                    # Also search in aliases
                    aliases = entry.get_aliases()
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
            # Security validation
            if not self._validate_sql_query(sql_query):
                return {
                    "status": "error",
                    "message": "SQL query failed security validation",
                    "results": []
                }
            
            # Get database path for project
            db_path = self._get_project_db_path(project_id)
            if not os.path.exists(db_path):
                return {
                    "status": "error",
                    "message": "Project database not found",
                    "results": []
                }
            
            # Execute query
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Add LIMIT if not present
            if 'LIMIT' not in sql_query.upper():
                sql_query += f" LIMIT {limit}"
            
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            results = [dict(row) for row in rows]
            
            conn.close()
            
            return {
                "status": "success",
                "message": "Query executed successfully",
                "results": results,
                "row_count": len(results),
                "columns": list(results[0].keys()) if results else []
            }
            
        except Exception as e:
            current_app.logger.error(f"SQL execution error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "results": []
            }
    
    def _validate_sql_query(self, sql_query: str) -> bool:
        """Validate SQL query for security"""
        if not sql_query:
            return False
        
        sql_upper = sql_query.upper().strip()
        
        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return False
        
        # Check for forbidden keywords
        forbidden = current_app.config['SECURITY_CONFIG']['forbidden_sql_keywords']
        for keyword in forbidden:
            if keyword in sql_upper:
                return False
        
        return True
    
    def _get_project_db_path(self, project_id: int) -> str:
        """Get database path for project data"""
        return os.path.join(current_app.config['UPLOAD_FOLDER'], f"project_{project_id}.db")