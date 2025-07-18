# routes/search_routes.py
from flask import Blueprint, request, jsonify, current_app
from models import Project, SearchIndex, TableInfo, DataDictionary
from services.search_service import SearchService
from services.embedding_service import EmbeddingService

search_bp = Blueprint('search', __name__)

@search_bp.route('/<int:project_id>/methods', methods=['GET'])
def get_search_methods(project_id):
    """Get available search methods for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Check available indexes
        indexes = SearchIndex.query.filter_by(
            project_id=project_id,
            is_built=True,
            status='ready'
        ).all()
        
        methods = {
            'semantic': {
                'available': any(idx.index_type == 'faiss' for idx in indexes),
                'indexes': [idx.to_dict() for idx in indexes if idx.index_type == 'faiss'],
                'description': 'Vector-based semantic similarity search using embeddings'
            },
            'keyword': {
                'available': any(idx.index_type == 'tfidf' for idx in indexes),
                'indexes': [idx.to_dict() for idx in indexes if idx.index_type == 'tfidf'],
                'description': 'TF-IDF based keyword matching'
            },
            'fuzzy': {
                'available': True,  # Always available
                'indexes': [],
                'description': 'Fuzzy string matching using Levenshtein distance'
            },
            'exact': {
                'available': True,  # Always available
                'indexes': [],
                'description': 'Exact string matching'
            }
        }
        
        return jsonify({
            'status': 'success',
            'methods': methods,
            'total_indexes': len(indexes)
        })
        
    except Exception as e:
        current_app.logger.error(f"Get search methods error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/<int:project_id>/test', methods=['POST'])
def test_search(project_id):
    """Test search using specified method"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        method = data.get('method', 'semantic')
        config = data.get('config', {})
        
        # Validate method
        valid_methods = ['semantic', 'keyword', 'fuzzy', 'exact', 'combined']
        if method not in valid_methods:
            return jsonify({'error': f'Invalid method. Must be one of: {valid_methods}'}), 400
        
        search_service = SearchService()
        
        if method == 'combined':
            # Test all methods and combine results
            entities = [{'text': query, 'type': 'unknown'}]
            results = search_service.search_entities(project_id, query, entities, config)
        else:
            # Test specific method
            results = search_service.search_by_method(project_id, query, method, config)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'method': method,
            'results': results,
            'result_count': len(results) if isinstance(results, list) else sum(len(v) for v in results.values() if isinstance(v, list))
        })
        
    except Exception as e:
        current_app.logger.error(f"Test search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/<int:project_id>/compare', methods=['POST'])
def compare_search_methods(project_id):
    """Compare results across different search methods"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        methods = data.get('methods', ['semantic', 'keyword', 'fuzzy', 'exact'])
        config = data.get('config', {})
        
        search_service = SearchService()
        comparison_results = {}
        
        for method in methods:
            try:
                if method == 'combined':
                    entities = [{'text': query, 'type': 'unknown'}]
                    method_results = search_service.search_entities(project_id, query, entities, config)
                    comparison_results[method] = method_results
                else:
                    method_results = search_service.search_by_method(project_id, query, method, config)
                    comparison_results[method] = {
                        'results': method_results,
                        'count': len(method_results)
                    }
            except Exception as e:
                comparison_results[method] = {
                    'error': str(e),
                    'results': [],
                    'count': 0
                }
        
        # Calculate overlap statistics
        all_items = set()
        method_items = {}
        
        for method, data in comparison_results.items():
            if 'error' not in data:
                results = data.get('results', [])
                if isinstance(results, list):
                    items = set()
                    for result in results:
                        if result.get('type') == 'table':
                            items.add(f"table_{result.get('id')}")
                        elif result.get('type') == 'column':
                            items.add(f"column_{result.get('table_id')}_{result.get('column_name')}")
                        elif result.get('type') == 'dictionary':
                            items.add(f"dict_{result.get('id')}")
                    
                    method_items[method] = items
                    all_items.update(items)
        
        # Calculate overlap matrix
        overlap_matrix = {}
        for method1 in method_items:
            overlap_matrix[method1] = {}
            for method2 in method_items:
                if method1 == method2:
                    overlap_matrix[method1][method2] = 1.0
                else:
                    items1 = method_items[method1]
                    items2 = method_items[method2]
                    intersection = len(items1.intersection(items2))
                    union = len(items1.union(items2))
                    overlap_matrix[method1][method2] = intersection / union if union > 0 else 0.0
        
        return jsonify({
            'status': 'success',
            'query': query,
            'methods_tested': methods,
            'results': comparison_results,
            'overlap_matrix': overlap_matrix,
            'unique_items_found': len(all_items)
        })
        
    except Exception as e:
        current_app.logger.error(f"Compare search methods error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/<int:project_id>/index/<int:index_id>/search', methods=['POST'])
def search_specific_index(project_id, index_id):
    """Search in a specific index"""
    try:
        project = Project.query.get_or_404(project_id)
        index = SearchIndex.query.get_or_404(index_id)
        
        if index.project_id != project_id:
            return jsonify({'error': 'Index does not belong to this project'}), 403
        
        if not index.is_built:
            return jsonify({'error': 'Index is not ready for search'}), 400
        
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        top_k = data.get('top_k', 10)
        
        embedding_service = EmbeddingService()
        results = embedding_service.search_index(index_id, query, top_k)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'index': index.to_dict(),
            'results': results,
            'result_count': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Search specific index error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/<int:project_id>/analyze', methods=['POST'])
def analyze_search_query(project_id):
    """Analyze a search query and suggest improvements"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('query'):
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        
        # Basic query analysis
        analysis = {
            'query': query,
            'length': len(query),
            'word_count': len(query.split()),
            'has_operators': any(op in query.upper() for op in ['AND', 'OR', 'NOT']),
            'has_quotes': '"' in query,
            'has_wildcards': any(char in query for char in ['*', '?']),
            'suggestions': []
        }
        
        # Provide suggestions based on analysis
        if analysis['length'] < 3:
            analysis['suggestions'].append('Query is very short. Consider adding more descriptive terms.')
        
        if analysis['word_count'] == 1:
            analysis['suggestions'].append('Single word queries may return broad results. Consider adding context.')
        
        if analysis['word_count'] > 10:
            analysis['suggestions'].append('Long queries may be too specific. Consider shorter, focused terms.')
        
        # Check against project schema
        search_service = SearchService()
        schema_context = search_service.get_table_schema_context(project_id)
        
        # Find potential matches in schema
        table_matches = []
        column_matches = []
        dictionary_matches = []
        
        query_lower = query.lower()
        
        # Check table names
        for table_name in schema_context['tables'].keys():
            if query_lower in table_name.lower() or table_name.lower() in query_lower:
                table_matches.append(table_name)
        
        # Check column names
        for table_name, table_info in schema_context['tables'].items():
            for column in table_info.get('columns', []):
                col_name = column['name']
                if query_lower in col_name.lower() or col_name.lower() in query_lower:
                    column_matches.append(f"{table_name}.{col_name}")
        
        # Check dictionary terms
        for entry in schema_context['dictionary']:
            term = entry['term']
            if query_lower in term.lower() or term.lower() in query_lower:
                dictionary_matches.append(term)
        
        analysis['schema_matches'] = {
            'tables': table_matches,
            'columns': column_matches,
            'dictionary_terms': dictionary_matches
        }
        
        if not any([table_matches, column_matches, dictionary_matches]):
            analysis['suggestions'].append('No direct matches found in schema. Try synonyms or broader terms.')
        
        return jsonify({
            'status': 'success',
            'analysis': analysis
        })
        
    except Exception as e:
        current_app.logger.error(f"Analyze search query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@search_bp.route('/<int:project_id>/benchmark', methods=['POST'])
def benchmark_search_methods(project_id):
    """Benchmark search methods with multiple queries"""
    try:
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        if not data or not data.get('queries'):
            return jsonify({'error': 'Queries list is required'}), 400
        
        queries = data['queries']
        methods = data.get('methods', ['semantic', 'keyword', 'fuzzy', 'exact'])
        
        if len(queries) > 20:
            return jsonify({'error': 'Maximum 20 queries allowed for benchmarking'}), 400
        
        search_service = SearchService()
        benchmark_results = {
            'queries_tested': len(queries),
            'methods': methods,
            'results': {},
            'performance': {}
        }
        
        import time
        
        for method in methods:
            method_results = []
            total_time = 0
            error_count = 0
            
            for query in queries:
                start_time = time.time()
                try:
                    if method == 'combined':
                        entities = [{'text': query, 'type': 'unknown'}]
                        results = search_service.search_entities(project_id, query, entities)
                        result_count = sum(len(v) for v in results.values() if isinstance(v, list))
                    else:
                        results = search_service.search_by_method(project_id, query, method)
                        result_count = len(results)
                    
                    end_time = time.time()
                    query_time = end_time - start_time
                    total_time += query_time
                    
                    method_results.append({
                        'query': query,
                        'result_count': result_count,
                        'time': round(query_time, 3),
                        'status': 'success'
                    })
                
                except Exception as e:
                    end_time = time.time()
                    query_time = end_time - start_time
                    total_time += query_time
                    error_count += 1
                    
                    method_results.append({
                        'query': query,
                        'error': str(e),
                        'time': round(query_time, 3),
                        'status': 'error'
                    })
            
            benchmark_results['results'][method] = method_results
            benchmark_results['performance'][method] = {
                'total_time': round(total_time, 3),
                'average_time': round(total_time / len(queries), 3),
                'error_rate': round(error_count / len(queries), 3),
                'success_rate': round((len(queries) - error_count) / len(queries), 3)
            }
        
        return jsonify({
            'status': 'success',
            'benchmark': benchmark_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Benchmark search methods error: {str(e)}")
        return jsonify({'error': str(e)}), 500