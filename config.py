# config.py
import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///queryforge.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json'}
    
    # Azure OpenAI Configuration
    LLM_CONFIG = {
        'azure': {
            'api_key': os.environ.get('AZURE_OPENAI_API_KEY') or 'your-azure-openai-api-key',
            'endpoint': os.environ.get('AZURE_OPENAI_ENDPOINT') or 'https://your-resource.openai.azure.com/',
            'api_version': os.environ.get('AZURE_OPENAI_API_VERSION') or '2024-02-01',
            'deployment_name': os.environ.get('AZURE_OPENAI_DEPLOYMENT') or 'gpt-4',
            'model_name': os.environ.get('AZURE_OPENAI_MODEL') or 'gpt-4',
            'max_tokens': 2000,
            'temperature': 0.1
        }
    }
    
    # Embedding Configuration
    EMBEDDING_CONFIG = {
        'default_model': 'sentence-transformers/all-MiniLM-L6-v2',
        'batch_size': 32,
        'max_sequence_length': 512,
        'available_models': [
            'sentence-transformers/all-MiniLM-L6-v2',
            'sentence-transformers/all-mpnet-base-v2',
            'sentence-transformers/distilbert-base-nli-mean-tokens',
            'sentence-transformers/paraphrase-MiniLM-L6-v2'
        ]
    }
    
    # Entity Extraction Configuration
    ENTITY_CONFIG = {
        'similarity_threshold': 0.5,
        'max_entities': 20,
        'confidence_threshold': 0.3,
        'max_mappings_per_entity': 3
    }
    
    # Search Configuration
    SEARCH_CONFIG = {
        'default_top_k': 10,
        'max_top_k': 100,
        'min_similarity_score': 0.1,
        'result_timeout_seconds': 30
    }
    
    # AI Prompts
    PROMPTS = {
        'entity_extraction': """
Extract entities from the following natural language query that could map to database elements.

Query: "{query}"

Available database schema:
Tables: {tables}
Columns: {columns}
Dictionary Terms: {dictionary_terms}

Please identify:
1. Table names or concepts
2. Column names or attributes  
3. Business terms or metrics
4. Filter conditions or constraints
5. Aggregation requirements

Return a JSON object with an "entities" array. Each entity should have:
- "text": the exact text from the query
- "type": one of ["table", "column", "metric", "filter", "aggregation", "business_term"]
- "confidence": a float between 0.0 and 1.0

Example:
{{
  "entities": [
    {{"text": "customers", "type": "table", "confidence": 0.9}},
    {{"text": "revenue", "type": "metric", "confidence": 0.8}},
    {{"text": "last month", "type": "filter", "confidence": 0.7}}
  ]
}}
""",
        
        'sql_generation': """
Generate a SQL query based on the following information:

User Query: "{query}"

Extracted Entities:
{entities}

Entity Mappings:
{mappings}

Database Schema:
{schema}

Table Relationships:
{relationships}

Instructions:
1. Generate a SELECT query only
2. Use proper table and column names from the schema
3. Include appropriate WHERE clauses for filters
4. Add GROUP BY and aggregation functions as needed
5. Use LIMIT for result size control
6. Ensure the query is syntactically correct
7. Round numeric results to 2-3 decimal places

Return a JSON object with:
- "sql": the complete SQL query string
- "confidence": confidence score (0.0-1.0)
- "explanation": brief explanation of the query logic

Example:
{{
  "sql": "SELECT customer_name, ROUND(SUM(order_total), 2) as total_revenue FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.order_date >= DATE('now', '-30 days') GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 10",
  "confidence": 0.9,
  "explanation": "Calculates total revenue per customer for the last 30 days, ordered by highest revenue first"
}}
""",
        
        'response_generation': """
Generate a natural language response based on the query results.

Original Query: "{query}"
SQL Query: "{sql_query}"
Results: {results}
Total Results: {total_results}

Instructions:
1. Provide a clear, conversational summary of the results
2. Highlight key insights or patterns
3. Use natural language, not technical jargon
4. If no results, suggest why and potential next steps
5. If many results, summarize the top findings
6. Include relevant numbers and statistics
7. Be concise but informative

Focus on answering the user's original question directly.
""",
        
        'query_improvement': """
Analyze this natural language query and suggest improvements:

Query: "{query}"
Available Tables: {tables}

Provide suggestions to make the query:
1. More specific and precise
2. Clearer in intent
3. Better aligned with available data
4. More likely to return useful results

Return JSON with:
- "suggestions": array of improvement suggestions
- "clarity_score": score from 0.0-1.0 for current clarity
- "specificity_score": score from 0.0-1.0 for current specificity
- "improved_query": an improved version of the query

Example:
{{
  "suggestions": [
    "Specify a time period for more focused results",
    "Consider adding constraints to narrow the scope"
  ],
  "clarity_score": 0.7,
  "specificity_score": 0.6,
  "improved_query": "Show me the top 10 customers by revenue in the last quarter"
}}
""",
        
        'intent_analysis': """
Analyze the intent and characteristics of this query:

Query: "{query}"

Determine:
1. Primary intent (lookup, aggregation, comparison, filtering, etc.)
2. Complexity level (simple, moderate, complex)
3. Expected result type (single value, list, table, summary)
4. Key concepts and entities mentioned
5. Required operations (joins, grouping, calculations)

Return JSON with:
- "intent": primary intent category
- "complexity": complexity level
- "result_type": expected result format
- "concepts": array of key concepts
- "operations": array of required database operations
- "confidence": confidence in analysis (0.0-1.0)

Example:
{{
  "intent": "aggregation",
  "complexity": "moderate", 
  "result_type": "summary_table",
  "concepts": ["sales", "revenue", "time_period"],
  "operations": ["join", "group_by", "sum"],
  "confidence": 0.8
}}
"""
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_timeout': 20,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 30
    }

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

def get_config():
    """Get configuration class based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig

def init_app_config(app):
    """Initialize additional app configuration"""
    
    # Create required directories
    directories = [
        app.config['UPLOAD_FOLDER'],
        'models',
        'indexes', 
        'data',
        'logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Configure logging
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/queryforge.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('QueryForge startup')
    
    # Validate Azure OpenAI configuration
    azure_config = app.config['LLM_CONFIG']['azure']
    api_key = os.environ.get('AZURE_OPENAI_API_KEY') or azure_config.get('api_key')
    endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT') or azure_config.get('endpoint')
    
    if (api_key == 'your-azure-openai-api-key' or 
        endpoint == 'https://your-resource.openai.azure.com/'):
        app.logger.warning(
            "Azure OpenAI not configured. Chat functionality will be limited. "
            "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables."
        )
    else:
        app.logger.info("Azure OpenAI configuration detected")
    
    return app

# Database connection validation
def validate_database_config(config):
    """Validate database configuration"""
    try:
        from sqlalchemy import create_engine
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
        connection = engine.connect()
        connection.close()
        return True
    except Exception as e:
        print(f"Database validation failed: {str(e)}")
        return False

# Default configuration for immediate use
Config.SQLALCHEMY_DATABASE_URI = 'sqlite:///queryforge.db'
Config.DEBUG = True