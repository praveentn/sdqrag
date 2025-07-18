# models.py
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    data_sources = db.relationship('DataSource', backref='project', lazy=True, cascade='all, delete-orphan')
    table_infos = db.relationship('TableInfo', backref='project', lazy=True, cascade='all, delete-orphan')
    dictionary_entries = db.relationship('DataDictionary', backref='project', lazy=True, cascade='all, delete-orphan')
    embedding_models = db.relationship('EmbeddingModel', backref='project', lazy=True, cascade='all, delete-orphan')
    search_indexes = db.relationship('SearchIndex', backref='project', lazy=True, cascade='all, delete-orphan')
    chat_sessions = db.relationship('ChatHistory', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'data_sources_count': len(self.data_sources),
            'tables_count': len(self.table_infos)
        }

class DataSource(db.Model):
    __tablename__ = 'data_sources'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(20), nullable=False)  # 'file', 'database'
    file_path = db.Column(db.String(500))
    file_name = db.Column(db.String(100))
    file_size = db.Column(db.Integer)
    connection_string = db.Column(db.Text)  # For database connections
    connection_config = db.Column(db.Text)  # JSON config for DB connections
    status = db.Column(db.String(20), default='active')  # active, error, processing
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tables = db.relationship('TableInfo', backref='data_source', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'source_type': self.source_type,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'tables_count': len(self.tables)
        }

class TableInfo(db.Model):
    __tablename__ = 'table_info'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    data_source_id = db.Column(db.Integer, db.ForeignKey('data_sources.id'), nullable=False)
    table_name = db.Column(db.String(100), nullable=False)
    original_name = db.Column(db.String(100))  # Original sheet/table name
    schema_info = db.Column(db.Text)  # JSON schema information
    row_count = db.Column(db.Integer, default=0)
    column_count = db.Column(db.Integer, default=0)
    sample_data = db.Column(db.Text)  # JSON sample rows
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_schema(self):
        return json.loads(self.schema_info) if self.schema_info else {}
    
    def set_schema(self, schema_dict):
        self.schema_info = json.dumps(schema_dict)
    
    def get_sample_data(self):
        return json.loads(self.sample_data) if self.sample_data else []
    
    def set_sample_data(self, data_list):
        self.sample_data = json.dumps(data_list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'data_source_id': self.data_source_id,
            'table_name': self.table_name,
            'original_name': self.original_name,
            'schema_info': self.get_schema(),
            'row_count': self.row_count,
            'column_count': self.column_count,
            'sample_data': self.get_sample_data(),
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DataDictionary(db.Model):
    __tablename__ = 'data_dictionary'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    term = db.Column(db.String(100), nullable=False)
    definition = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # encyclopedia, abbreviation, keyword, domain_term
    source_table = db.Column(db.String(100))
    source_column = db.Column(db.String(100))
    aliases = db.Column(db.Text)  # JSON array of alternative terms
    examples = db.Column(db.Text)  # JSON array of examples
    tags = db.Column(db.Text)  # JSON array of tags
    confidence_score = db.Column(db.Float, default=1.0)
    is_verified = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_aliases(self):
        return json.loads(self.aliases) if self.aliases else []
    
    def set_aliases(self, aliases_list):
        self.aliases = json.dumps(aliases_list)
    
    def get_examples(self):
        return json.loads(self.examples) if self.examples else []
    
    def set_examples(self, examples_list):
        self.examples = json.dumps(examples_list)
    
    def get_tags(self):
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags_list):
        self.tags = json.dumps(tags_list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'term': self.term,
            'definition': self.definition,
            'category': self.category,
            'source_table': self.source_table,
            'source_column': self.source_column,
            'aliases': self.get_aliases(),
            'examples': self.get_examples(),
            'tags': self.get_tags(),
            'confidence_score': round(self.confidence_score, 3) if self.confidence_score else 0.0,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class EmbeddingModel(db.Model):
    __tablename__ = 'embedding_models'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    model_name = db.Column(db.String(200), nullable=False)
    model_path = db.Column(db.String(500))  # Local path to downloaded model
    model_type = db.Column(db.String(50), nullable=False)  # sentence-transformers, openai, etc.
    embedding_dimension = db.Column(db.Integer)
    is_downloaded = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    download_progress = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, downloading, ready, error
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    search_indexes = db.relationship('SearchIndex', backref='embedding_model', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'embedding_dimension': self.embedding_dimension,
            'is_downloaded': self.is_downloaded,
            'is_active': self.is_active,
            'download_progress': round(self.download_progress, 2) if self.download_progress else 0.0,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SearchIndex(db.Model):
    __tablename__ = 'search_indexes'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    embedding_model_id = db.Column(db.Integer, db.ForeignKey('embedding_models.id'), nullable=False)
    index_name = db.Column(db.String(100), nullable=False)
    index_type = db.Column(db.String(50), nullable=False)  # faiss, tfidf, bm25, pgvector
    target_type = db.Column(db.String(50), nullable=False)  # tables, columns, dictionary, encyclopedia
    target_ids = db.Column(db.Text)  # JSON array of target IDs
    index_path = db.Column(db.String(500))  # Path to saved index file
    vector_count = db.Column(db.Integer, default=0)
    is_built = db.Column(db.Boolean, default=False)
    build_progress = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, building, ready, error
    error_message = db.Column(db.Text)
    build_config = db.Column(db.Text)  # JSON config used for building
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_target_ids(self):
        return json.loads(self.target_ids) if self.target_ids else []
    
    def set_target_ids(self, ids_list):
        self.target_ids = json.dumps(ids_list)
    
    def get_build_config(self):
        return json.loads(self.build_config) if self.build_config else {}
    
    def set_build_config(self, config_dict):
        self.build_config = json.dumps(config_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'embedding_model_id': self.embedding_model_id,
            'index_name': self.index_name,
            'index_type': self.index_type,
            'target_type': self.target_type,
            'target_ids': self.get_target_ids(),
            'vector_count': self.vector_count,
            'is_built': self.is_built,
            'build_progress': round(self.build_progress, 2) if self.build_progress else 0.0,
            'status': self.status,
            'error_message': self.error_message,
            'build_config': self.get_build_config(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    user_query = db.Column(db.Text, nullable=False)
    extracted_entities = db.Column(db.Text)  # JSON entities from LLM
    entity_mappings = db.Column(db.Text)  # JSON mapped entities to schema
    selected_tables = db.Column(db.Text)  # JSON selected tables and schemas
    generated_sql = db.Column(db.Text)
    sql_results = db.Column(db.Text)  # JSON query results
    final_response = db.Column(db.Text)
    user_feedback = db.Column(db.Text)
    confirmation_steps = db.Column(db.Text)  # JSON confirmation flow
    processing_time = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')  # pending, completed, error
    error_message = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_extracted_entities(self):
        return json.loads(self.extracted_entities) if self.extracted_entities else []
    
    def set_extracted_entities(self, entities_list):
        self.extracted_entities = json.dumps(entities_list)
    
    def get_entity_mappings(self):
        return json.loads(self.entity_mappings) if self.entity_mappings else {}
    
    def set_entity_mappings(self, mappings_dict):
        self.entity_mappings = json.dumps(mappings_dict)
    
    def get_selected_tables(self):
        return json.loads(self.selected_tables) if self.selected_tables else []
    
    def set_selected_tables(self, tables_list):
        self.selected_tables = json.dumps(tables_list)
    
    def get_sql_results(self):
        return json.loads(self.sql_results) if self.sql_results else []
    
    def set_sql_results(self, results_list):
        self.sql_results = json.dumps(results_list)
    
    def get_confirmation_steps(self):
        return json.loads(self.confirmation_steps) if self.confirmation_steps else {}
    
    def set_confirmation_steps(self, steps_dict):
        self.confirmation_steps = json.dumps(steps_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'session_id': self.session_id,
            'user_query': self.user_query,
            'extracted_entities': self.get_extracted_entities(),
            'entity_mappings': self.get_entity_mappings(),
            'selected_tables': self.get_selected_tables(),
            'generated_sql': self.generated_sql,
            'sql_results': self.get_sql_results(),
            'final_response': self.final_response,
            'user_feedback': self.user_feedback,
            'confirmation_steps': self.get_confirmation_steps(),
            'processing_time': round(self.processing_time, 3) if self.processing_time else 0.0,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')  # admin, user, viewer
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='creator', lazy=True)
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True)
    dictionary_entries = db.relationship('DataDictionary', backref='creator', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }