# services/embedding_service.py
import os
import json
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import current_app
from models import EmbeddingModel, SearchIndex, TableInfo, DataDictionary, db

class EmbeddingService:
    def __init__(self):
        self.models_cache = {}
        self.models_dir = os.path.join(os.getcwd(), 'models')
        self.indexes_dir = os.path.join(os.getcwd(), 'indexes')
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.indexes_dir, exist_ok=True)
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available embedding models"""
        return [
            {
                'name': 'sentence-transformers/all-MiniLM-L6-v2',
                'type': 'sentence-transformers',
                'dimension': 384,
                'description': 'Fast and efficient, good for general purpose',
                'size': '90MB'
            },
            {
                'name': 'sentence-transformers/all-mpnet-base-v2',
                'type': 'sentence-transformers', 
                'dimension': 768,
                'description': 'Higher quality embeddings, slower',
                'size': '420MB'
            },
            {
                'name': 'sentence-transformers/paraphrase-MiniLM-L6-v2',
                'type': 'sentence-transformers',
                'dimension': 384,
                'description': 'Good for paraphrase detection',
                'size': '90MB'
            },
            {
                'name': 'sentence-transformers/distilbert-base-nli-mean-tokens',
                'type': 'sentence-transformers',
                'dimension': 768,
                'description': 'Good for semantic similarity',
                'size': '250MB'
            }
        ]
    
    def download_model(self, project_id: int, model_name: str) -> Dict[str, Any]:
        """Download and setup embedding model"""
        try:
            # Check if model record exists
            existing_model = EmbeddingModel.query.filter_by(
                project_id=project_id, 
                model_name=model_name
            ).first()
            
            if existing_model and existing_model.is_downloaded:
                return {
                    "status": "success",
                    "message": "Model already downloaded",
                    "model_id": existing_model.id
                }
            
            # Create or update model record
            if not existing_model:
                model_info = next((m for m in self.get_available_models() if m['name'] == model_name), None)
                if not model_info:
                    return {"status": "error", "message": "Model not found in available models"}
                
                embedding_model = EmbeddingModel(
                    project_id=project_id,
                    model_name=model_name,
                    model_type=model_info['type'],
                    embedding_dimension=model_info['dimension'],
                    status='downloading'
                )
                db.session.add(embedding_model)
                db.session.commit()
            else:
                embedding_model = existing_model
                embedding_model.status = 'downloading'
                embedding_model.download_progress = 0.0
                db.session.commit()
            
            # Download model
            model_path = os.path.join(self.models_dir, model_name.replace('/', '_'))
            
            if model_name.startswith('sentence-transformers/'):
                # Download sentence transformer model
                try:
                    current_app.logger.info(f"Downloading model: {model_name}")
                    model = SentenceTransformer(model_name, cache_folder=self.models_dir)
                    
                    # Save model locally
                    local_model_path = os.path.join(model_path, 'model')
                    os.makedirs(local_model_path, exist_ok=True)
                    model.save(local_model_path)
                    
                    # Update model record
                    embedding_model.model_path = local_model_path
                    embedding_model.is_downloaded = True
                    embedding_model.download_progress = 100.0
                    embedding_model.status = 'ready'
                    db.session.commit()
                    
                    current_app.logger.info(f"Model downloaded successfully: {model_name}")
                    return {
                        "status": "success",
                        "message": "Model downloaded successfully",
                        "model_id": embedding_model.id,
                        "path": local_model_path
                    }
                    
                except Exception as e:
                    embedding_model.status = 'error'
                    embedding_model.error_message = str(e)
                    db.session.commit()
                    raise e
            else:
                return {"status": "error", "message": "Unsupported model type"}
                
        except Exception as e:
            current_app.logger.error(f"Model download error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def load_model(self, model_id: int) -> Optional[SentenceTransformer]:
        """Load embedding model from local storage"""
        try:
            if model_id in self.models_cache:
                return self.models_cache[model_id]
            
            embedding_model = EmbeddingModel.query.get(model_id)
            if not embedding_model or not embedding_model.is_downloaded:
                return None
            
            if embedding_model.model_type == 'sentence-transformers':
                model = SentenceTransformer(embedding_model.model_path)
                self.models_cache[model_id] = model
                return model
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Model loading error: {str(e)}")
            return None
    
    def generate_embeddings(self, texts: List[str], model_id: int) -> Optional[np.ndarray]:
        """Generate embeddings for texts using specified model"""
        try:
            model = self.load_model(model_id)
            if not model:
                return None
            
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings
            
        except Exception as e:
            current_app.logger.error(f"Embedding generation error: {str(e)}")
            return None
    
    def search_index(self, index_id: int, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search in a specific index"""
        try:
            search_index = SearchIndex.query.get(index_id)
            if not search_index or not search_index.is_built:
                return []
            
            if search_index.index_type == 'faiss':
                return self._search_faiss_index(search_index, query, top_k)
            elif search_index.index_type == 'tfidf':
                return self._search_tfidf_index(search_index, query, top_k)
            
            return []
            
        except Exception as e:
            current_app.logger.error(f"Index search error: {str(e)}")
            return []
    
    def _search_faiss_index(self, search_index: SearchIndex, query: str, 
                           top_k: int) -> List[Dict[str, Any]]:
        """Search FAISS index"""
        try:
            # Load FAISS index
            faiss_index = faiss.read_index(search_index.index_path)
            
            # Load metadata
            metadata_path = search_index.index_path.replace('.index', '_metadata.pkl')
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            # Generate query embedding
            query_embedding = self.generate_embeddings([query], search_index.embedding_model_id)
            if query_embedding is None:
                return []
            
            # Normalize query embedding
            faiss.normalize_L2(query_embedding)
            
            # Search
            scores, indices = faiss_index.search(query_embedding.astype('float32'), top_k)
            
            # Format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(metadata):
                    result = metadata[idx].copy()
                    result['score'] = float(score)
                    result['rank'] = i + 1
                    results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"FAISS search error: {str(e)}")
            return []
    
    def _search_tfidf_index(self, search_index: SearchIndex, query: str, 
                           top_k: int) -> List[Dict[str, Any]]:
        """Search TF-IDF index"""
        try:
            # Load TF-IDF index
            with open(search_index.index_path, 'rb') as f:
                index_data = pickle.load(f)
            
            vectorizer = index_data['vectorizer']
            tfidf_matrix = index_data['matrix']
            metadata = index_data['metadata']
            
            # Transform query
            query_vector = vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
            
            # Get top results
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            # Format results
            results = []
            for i, idx in enumerate(top_indices):
                if similarities[idx] > 0:  # Only return non-zero similarities
                    result = metadata[idx].copy()
                    result['score'] = float(similarities[idx])
                    result['rank'] = i + 1
                    results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"TF-IDF search error: {str(e)}")
            return []
        

    def create_faiss_index(self, project_id: int, embedding_model_id: int, index_name: str,
                        target_type: str, target_ids: List[int], 
                        config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create FAISS index for embeddings with better local model handling"""
        try:
            current_app.logger.info(f"Starting FAISS index creation: {index_name}")
            
            # Validate embedding model is locally available
            embedding_model = EmbeddingModel.query.get(embedding_model_id)
            if not embedding_model:
                return {"status": "error", "message": "Embedding model not found"}
            
            if not embedding_model.is_downloaded or embedding_model.status != 'ready':
                return {
                    "status": "error", 
                    "message": f"Embedding model '{embedding_model.model_name}' is not downloaded or ready. Status: {embedding_model.status}"
                }
            
            # Check if model files exist
            if not embedding_model.model_path or not os.path.exists(embedding_model.model_path):
                return {
                    "status": "error",
                    "message": f"Embedding model files not found at: {embedding_model.model_path}"
                }
            
            # Get or create index record - avoid duplicate creation
            search_index = SearchIndex.query.filter_by(
                project_id=project_id,
                index_name=index_name
            ).first()
            
            if not search_index:
                search_index = SearchIndex(
                    project_id=project_id,
                    embedding_model_id=embedding_model_id,
                    index_name=index_name,
                    index_type='faiss',
                    target_type=target_type,
                    status='building'
                )
                search_index.set_target_ids(target_ids)
                search_index.set_build_config(config or {})
                db.session.add(search_index)
                db.session.commit()
            
            current_app.logger.info(f"Collecting texts for indexing from {target_type}")
            
            # Collect texts to embed
            texts, metadata = self._collect_texts_for_indexing(target_type, target_ids, project_id)
            
            if not texts:
                search_index.status = 'error'
                search_index.error_message = 'No texts found for indexing'
                db.session.commit()
                return {"status": "error", "message": "No texts found for indexing"}
            
            current_app.logger.info(f"Found {len(texts)} texts to index")
            
            # Check if FAISS is available
            try:
                import faiss
            except ImportError:
                search_index.status = 'error'
                search_index.error_message = 'FAISS library not available'
                db.session.commit()
                return {
                    "status": "error", 
                    "message": "FAISS library not available. Please install with: pip install faiss-cpu"
                }
            
            # Load the local model
            current_app.logger.info(f"Loading embedding model: {embedding_model.model_name}")
            model = self.load_model(embedding_model_id)
            if not model:
                search_index.status = 'error'
                search_index.error_message = 'Failed to load embedding model'
                db.session.commit()
                return {"status": "error", "message": "Failed to load embedding model"}
            
            # Generate embeddings
            current_app.logger.info(f"Generating embeddings for {len(texts)} texts")
            try:
                embeddings = model.encode(texts, convert_to_numpy=True)
                current_app.logger.info(f"Generated embeddings with shape: {embeddings.shape}")
            except Exception as e:
                search_index.status = 'error'
                search_index.error_message = f'Failed to generate embeddings: {str(e)}'
                db.session.commit()
                return {"status": "error", "message": f"Failed to generate embeddings: {str(e)}"}
            
            # Create FAISS index
            current_app.logger.info(f"Creating FAISS index with dimension {embeddings.shape[1]}")
            dimension = embeddings.shape[1]
            faiss_index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            faiss_index.add(embeddings.astype('float32'))
            
            # Save index
            index_path = os.path.join(self.indexes_dir, f"faiss_{search_index.id}.index")
            faiss.write_index(faiss_index, index_path)
            
            # Save metadata
            metadata_path = os.path.join(self.indexes_dir, f"faiss_{search_index.id}_metadata.pkl")
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            # Update index record
            search_index.index_path = index_path
            search_index.vector_count = len(embeddings)
            search_index.is_built = True
            search_index.build_progress = 100.0
            search_index.status = 'ready'
            db.session.commit()
            
            current_app.logger.info(f"FAISS index created successfully: {index_name} with {len(embeddings)} vectors")
            return {
                "status": "success",
                "message": "FAISS index created successfully",
                "index_id": search_index.id,
                "vector_count": len(embeddings)
            }
            
        except Exception as e:
            current_app.logger.error(f"FAISS index creation error: {str(e)}")
            try:
                if 'search_index' in locals():
                    search_index.status = 'error'
                    search_index.error_message = str(e)
                    db.session.commit()
            except:
                pass
            return {"status": "error", "message": str(e)}

    def create_tfidf_index(self, project_id: int, index_name: str, target_type: str, 
                        target_ids: List[int], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create TF-IDF index with better error handling"""
        try:
            current_app.logger.info(f"Starting TF-IDF index creation: {index_name}")
            
            # Get or create index record - avoid duplicate creation
            search_index = SearchIndex.query.filter_by(
                project_id=project_id,
                index_name=index_name
            ).first()
            
            if not search_index:
                search_index = SearchIndex(
                    project_id=project_id,
                    index_name=index_name,
                    index_type='tfidf',
                    target_type=target_type,
                    status='building'
                )
                search_index.set_target_ids(target_ids)
                search_index.set_build_config(config or {})
                db.session.add(search_index)
                db.session.commit()
            
            # Collect texts for indexing
            current_app.logger.info(f"Collecting texts for TF-IDF indexing from {target_type}")
            texts, metadata = self._collect_texts_for_indexing(target_type, target_ids, project_id)
            
            if not texts:
                search_index.status = 'error'
                search_index.error_message = 'No texts found for indexing'
                db.session.commit()
                return {"status": "error", "message": "No texts found for indexing"}
            
            current_app.logger.info(f"Found {len(texts)} texts for TF-IDF indexing")
            
            # Check if sklearn is available
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
            except ImportError:
                search_index.status = 'error'
                search_index.error_message = 'scikit-learn library not available'
                db.session.commit()
                return {
                    "status": "error",
                    "message": "scikit-learn library not available. Please install with: pip install scikit-learn"
                }
            
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=config.get('max_features', 10000),
                ngram_range=config.get('ngram_range', (1, 2)),
                stop_words='english'
            )
            
            # Fit and transform texts
            current_app.logger.info("Creating TF-IDF vectors")
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # Save TF-IDF index
            index_data = {
                'vectorizer': vectorizer,
                'matrix': tfidf_matrix,
                'metadata': metadata
            }
            
            index_path = os.path.join(self.indexes_dir, f"tfidf_{search_index.id}.pkl")
            with open(index_path, 'wb') as f:
                pickle.dump(index_data, f)
            
            # Update index record
            search_index.index_path = index_path
            search_index.vector_count = len(texts)
            search_index.is_built = True
            search_index.build_progress = 100.0
            search_index.status = 'ready'
            db.session.commit()
            
            current_app.logger.info(f"TF-IDF index created successfully: {index_name} with {len(texts)} documents")
            return {
                "status": "success",
                "message": "TF-IDF index created successfully",
                "index_id": search_index.id,
                "vector_count": len(texts)
            }
            
        except Exception as e:
            current_app.logger.error(f"TF-IDF index creation error: {str(e)}")
            try:
                if 'search_index' in locals():
                    search_index.status = 'error'
                    search_index.error_message = str(e)
                    db.session.commit()
            except:
                pass
            return {"status": "error", "message": str(e)}

    def load_model(self, model_id: int) -> Optional[SentenceTransformer]:
        """Load embedding model from local storage with better error handling"""
        try:
            if model_id in self.models_cache:
                return self.models_cache[model_id]
            
            embedding_model = EmbeddingModel.query.get(model_id)
            if not embedding_model:
                current_app.logger.error(f"Embedding model {model_id} not found in database")
                return None
            
            if not embedding_model.is_downloaded or embedding_model.status != 'ready':
                current_app.logger.error(f"Embedding model {model_id} not ready: {embedding_model.status}")
                return None
            
            if not embedding_model.model_path or not os.path.exists(embedding_model.model_path):
                current_app.logger.error(f"Model files not found at: {embedding_model.model_path}")
                return None
            
            if embedding_model.model_type == 'sentence-transformers':
                current_app.logger.info(f"Loading SentenceTransformer model from: {embedding_model.model_path}")
                model = SentenceTransformer(embedding_model.model_path)
                self.models_cache[model_id] = model
                return model
            
            current_app.logger.error(f"Unsupported model type: {embedding_model.model_type}")
            return None
            
        except Exception as e:
            current_app.logger.error(f"Model loading error for model {model_id}: {str(e)}")
            return None

    def _collect_texts_for_indexing(self, target_type: str, target_ids: List[int], 
                                project_id: int) -> Tuple[List[str], List[Dict]]:
        """Collect texts and metadata for indexing with better logging"""
        texts = []
        metadata = []
        
        try:
            current_app.logger.info(f"Collecting {target_type} texts for project {project_id}")
            
            if target_type == 'tables':
                # Get table information
                tables = TableInfo.query.filter(
                    TableInfo.id.in_(target_ids),
                    TableInfo.project_id == project_id
                ).all()
                
                current_app.logger.info(f"Found {len(tables)} tables to index")
                
                for table in tables:
                    # Table name and description
                    text = f"Table: {table.table_name}"
                    if table.description:
                        text += f" - {table.description}"
                    
                    # Add column information
                    schema = table.get_schema()
                    if schema and 'columns' in schema:
                        column_names = [col.get('name', '') for col in schema['columns']]
                        if column_names:
                            text += f" Columns: {', '.join(column_names)}"
                    
                    texts.append(text)
                    metadata.append({
                        'type': 'table',
                        'id': table.id,
                        'name': table.table_name,
                        'source': 'table_info'
                    })
                    
                    current_app.logger.debug(f"Added table text: {text[:100]}...")
            
            elif target_type == 'dictionary':
                # Get dictionary entries
                entries = DataDictionary.query.filter(
                    DataDictionary.id.in_(target_ids),
                    DataDictionary.project_id == project_id
                ).all()
                
                current_app.logger.info(f"Found {len(entries)} dictionary entries to index")
                
                for entry in entries:
                    text = f"Term: {entry.term} - {entry.definition}"
                    if entry.category:
                        text += f" (Category: {entry.category})"
                    
                    texts.append(text)
                    metadata.append({
                        'type': 'dictionary',
                        'id': entry.id,
                        'term': entry.term,
                        'source': 'data_dictionary'
                    })
                    
                    current_app.logger.debug(f"Added dictionary text: {text[:100]}...")
            
            elif target_type == 'columns':
                # Get column information from tables
                tables = TableInfo.query.filter(
                    TableInfo.id.in_(target_ids),
                    TableInfo.project_id == project_id
                ).all()
                
                current_app.logger.info(f"Found {len(tables)} tables for column indexing")
                
                for table in tables:
                    schema = table.get_schema()
                    if schema and 'columns' in schema:
                        for column in schema['columns']:
                            col_name = column.get('name', '')
                            col_type = column.get('data_type', 'unknown')
                            text = f"Column: {table.table_name}.{col_name} (Type: {col_type})"
                            
                            # Add sample values if available
                            sample_values = column.get('sample_values', [])
                            if sample_values:
                                text += f" Examples: {', '.join(str(v) for v in sample_values[:3])}"
                            
                            texts.append(text)
                            metadata.append({
                                'type': 'column',
                                'table_id': table.id,
                                'table_name': table.table_name,
                                'column_name': col_name,
                                'source': 'table_schema'
                            })
                            
                            current_app.logger.debug(f"Added column text: {text[:100]}...")
            
            current_app.logger.info(f"Collected {len(texts)} texts for indexing from {target_type}")
            return texts, metadata
            
        except Exception as e:
            current_app.logger.error(f"Error collecting texts for indexing: {str(e)}")
            return [], []


