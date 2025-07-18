# automate.py
import os
import sys
import json
import argparse
import requests
import time
from pathlib import Path
import pandas as pd

class QueryForgeAutomation:
    """Automation script for QueryForge operations"""
    
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def _api_call(self, method, endpoint, **kwargs):
        """Make API call with error handling"""
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code >= 400:
                print(f"❌ API Error {response.status_code}: {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def create_project(self, name, description=""):
        """Create a new project"""
        print(f"📁 Creating project: {name}")
        
        data = {
            'name': name,
            'description': description
        }
        
        result = self._api_call('POST', '/projects/', json=data)
        
        if result and result.get('status') == 'success':
            project = result['project']
            print(f"✅ Project created: {project['name']} (ID: {project['id']})")
            return project
        else:
            print(f"❌ Failed to create project: {name}")
            return None
    
    def upload_file(self, project_id, file_path):
        """Upload a file to a project"""
        print(f"📤 Uploading file: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
        
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'project_id': project_id}
            
            result = self._api_call('POST', '/upload', files=files, data=data)
        
        if result and result.get('status') == 'success':
            print(f"✅ File uploaded successfully")
            return result
        else:
            print(f"❌ Failed to upload file: {file_path}")
            return None
    
    def generate_dictionary(self, project_id):
        """Generate data dictionary for a project"""
        print(f"📚 Generating data dictionary for project {project_id}")
        
        result = self._api_call('POST', f'/datasources/{project_id}/generate-dictionary')
        
        if result and result.get('status') == 'success':
            print(f"✅ Dictionary generated: {result.get('entries_created', 0)} entries")
            return result
        else:
            print(f"❌ Failed to generate dictionary")
            return None
    
    def download_embedding_model(self, project_id, model_name):
        """Download an embedding model"""
        print(f"🤖 Downloading embedding model: {model_name}")
        
        data = {'model_name': model_name}
        result = self._api_call('POST', f'/embeddings/{project_id}/models/download', json=data)
        
        if result and result.get('status') == 'success':
            print(f"✅ Model download started: {model_name}")
            return self._wait_for_model_download(project_id, model_name)
        else:
            print(f"❌ Failed to start model download")
            return None
    
    def _wait_for_model_download(self, project_id, model_name, timeout=300):
        """Wait for model download to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            models = self._api_call('GET', f'/embeddings/{project_id}/models')
            
            if models and models.get('status') == 'success':
                for model in models['models']:
                    if model['model_name'] == model_name:
                        if model['status'] == 'ready':
                            print(f"✅ Model ready: {model_name}")
                            return model
                        elif model['status'] == 'error':
                            print(f"❌ Model download failed: {model.get('error_message')}")
                            return None
                        else:
                            progress = model.get('download_progress', 0)
                            print(f"   Progress: {progress:.1f}%")
            
            time.sleep(5)
        
        print(f"⏰ Model download timeout: {model_name}")
        return None
    
    def create_search_index(self, project_id, index_name, index_type, target_type, embedding_model_id=None):
        """Create a search index"""
        print(f"🔍 Creating search index: {index_name}")
        
        data = {
            'index_name': index_name,
            'index_type': index_type,
            'target_type': target_type,
            'target_ids': [],  # Empty means all available targets
            'config': {}
        }
        
        if embedding_model_id:
            data['embedding_model_id'] = embedding_model_id
        
        result = self._api_call('POST', f'/embeddings/{project_id}/indexes', json=data)
        
        if result and result.get('status') == 'success':
            print(f"✅ Index creation started: {index_name}")
            return self._wait_for_index_build(project_id, index_name)
        else:
            print(f"❌ Failed to start index creation")
            return None
    
    def _wait_for_index_build(self, project_id, index_name, timeout=300):
        """Wait for index build to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            indexes = self._api_call('GET', f'/embeddings/{project_id}/indexes')
            
            if indexes and indexes.get('status') == 'success':
                for index in indexes['indexes']:
                    if index['index_name'] == index_name:
                        if index['status'] == 'ready':
                            print(f"✅ Index ready: {index_name}")
                            return index
                        elif index['status'] == 'error':
                            print(f"❌ Index build failed: {index.get('error_message')}")
                            return None
                        else:
                            progress = index.get('build_progress', 0)
                            print(f"   Progress: {progress:.1f}%")
            
            time.sleep(5)
        
        print(f"⏰ Index build timeout: {index_name}")
        return None
    
    def run_query(self, project_id, query, method='quick'):
        """Run a natural language query"""
        print(f"💬 Running query: {query}")
        
        data = {'query': query}
        
        if method == 'quick':
            result = self._api_call('POST', f'/chat/{project_id}/quick-query', json=data)
        else:
            # Step-by-step method would require multiple API calls
            result = self._api_call('POST', f'/chat/{project_id}/query', json=data)
        
        if result and result.get('status') == 'success':
            print(f"✅ Query completed successfully")
            if 'final_response' in result:
                print(f"📋 Response: {result['final_response']}")
            if 'results' in result:
                print(f"📊 Found {len(result['results'])} results")
            return result
        else:
            print(f"❌ Query failed")
            return None
    
    def bulk_upload_directory(self, project_id, directory_path, file_extensions=None):
        """Upload all files in a directory"""
        if file_extensions is None:
            file_extensions = ['.csv', '.xlsx', '.xls', '.json']
        
        directory = Path(directory_path)
        if not directory.exists():
            print(f"❌ Directory not found: {directory_path}")
            return []
        
        uploaded_files = []
        
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in file_extensions:
                result = self.upload_file(project_id, str(file_path))
                if result:
                    uploaded_files.append(result)
                time.sleep(1)  # Small delay between uploads
        
        print(f"✅ Uploaded {len(uploaded_files)} files")
        return uploaded_files
    
    def setup_complete_project(self, name, data_directory, description="", 
                             embedding_model='sentence-transformers/all-MiniLM-L6-v2'):
        """Complete project setup automation"""
        print(f"🚀 Setting up complete project: {name}")
        
        # Step 1: Create project
        project = self.create_project(name, description)
        if not project:
            return None
        
        project_id = project['id']
        
        # Step 2: Upload data files
        if os.path.exists(data_directory):
            self.bulk_upload_directory(project_id, data_directory)
            time.sleep(2)
        
        # Step 3: Generate data dictionary
        self.generate_dictionary(project_id)
        time.sleep(2)
        
        # Step 4: Download embedding model
        model = self.download_embedding_model(project_id, embedding_model)
        if not model:
            print("⚠️ Continuing without embedding model")
            return project
        
        # Step 5: Create search indexes
        model_id = model['id']
        
        # Create FAISS index for tables
        self.create_search_index(project_id, 'tables_semantic', 'faiss', 'tables', model_id)
        time.sleep(2)
        
        # Create FAISS index for dictionary
        self.create_search_index(project_id, 'dictionary_semantic', 'faiss', 'dictionary', model_id)
        time.sleep(2)
        
        # Create TF-IDF index
        self.create_search_index(project_id, 'keyword_search', 'tfidf', 'tables')
        
        print(f"🎉 Project setup completed: {name}")
        return project
    
    def export_project_data(self, project_id, output_file):
        """Export project data to JSON"""
        print(f"💾 Exporting project data to: {output_file}")
        
        export_data = {
            'project': None,
            'data_sources': [],
            'tables': [],
            'dictionary': [],
            'chat_history': []
        }
        
        # Get project info
        project = self._api_call('GET', f'/projects/{project_id}')
        if project and project.get('status') == 'success':
            export_data['project'] = project['project']
        
        # Get data sources
        sources = self._api_call('GET', f'/datasources/{project_id}')
        if sources and sources.get('status') == 'success':
            export_data['data_sources'] = sources['data_sources']
        
        # Get dictionary
        dictionary = self._api_call('GET', f'/dictionary/{project_id}')
        if dictionary and dictionary.get('status') == 'success':
            export_data['dictionary'] = dictionary['entries']
        
        # Get chat sessions
        sessions = self._api_call('GET', f'/chat/{project_id}/sessions')
        if sessions and sessions.get('status') == 'success':
            for session in sessions['sessions']:
                history = self._api_call('GET', f'/chat/{project_id}/sessions/{session["session_id"]}')
                if history and history.get('status') == 'success':
                    export_data['chat_history'].extend(history['chat_history'])
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✅ Export completed: {output_file}")
        return export_data

def main():
    parser = argparse.ArgumentParser(description='QueryForge Automation Script')
    parser.add_argument('--base-url', default='http://localhost:5000', 
                       help='Base URL of QueryForge instance')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create project command
    create_parser = subparsers.add_parser('create-project', help='Create a new project')
    create_parser.add_argument('name', help='Project name')
    create_parser.add_argument('--description', default='', help='Project description')
    
    # Upload file command
    upload_parser = subparsers.add_parser('upload', help='Upload file to project')
    upload_parser.add_argument('project_id', type=int, help='Project ID')
    upload_parser.add_argument('file_path', help='Path to file')
    
    # Bulk upload command
    bulk_parser = subparsers.add_parser('bulk-upload', help='Upload directory of files')
    bulk_parser.add_argument('project_id', type=int, help='Project ID')
    bulk_parser.add_argument('directory', help='Directory path')
    
    # Setup project command
    setup_parser = subparsers.add_parser('setup-project', help='Complete project setup')
    setup_parser.add_argument('name', help='Project name')
    setup_parser.add_argument('data_directory', help='Data directory path')
    setup_parser.add_argument('--description', default='', help='Project description')
    setup_parser.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2', 
                             help='Embedding model')
    
    # Run query command
    query_parser = subparsers.add_parser('query', help='Run natural language query')
    query_parser.add_argument('project_id', type=int, help='Project ID')
    query_parser.add_argument('query', help='Natural language query')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export project data')
    export_parser.add_argument('project_id', type=int, help='Project ID')
    export_parser.add_argument('output_file', help='Output JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    automation = QueryForgeAutomation(args.base_url)
    
    if args.command == 'create-project':
        automation.create_project(args.name, args.description)
    
    elif args.command == 'upload':
        automation.upload_file(args.project_id, args.file_path)
    
    elif args.command == 'bulk-upload':
        automation.bulk_upload_directory(args.project_id, args.directory)
    
    elif args.command == 'setup-project':
        automation.setup_complete_project(
            args.name, args.data_directory, args.description, args.model
        )
    
    elif args.command == 'query':
        automation.run_query(args.project_id, args.query)
    
    elif args.command == 'export':
        automation.export_project_data(args.project_id, args.output_file)

if __name__ == '__main__':
    main()