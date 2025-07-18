# services/llm_service.py
import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import AzureOpenAI
from flask import current_app

class LLMService:
    def __init__(self):
        self.client = None
        self.config = current_app.config.get('LLM_CONFIG', {}).get('azure', {})
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client"""
        try:
            api_key = os.environ.get('AZURE_OPENAI_API_KEY') or self.config.get('api_key')
            endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT') or self.config.get('endpoint')
            api_version = os.environ.get('AZURE_OPENAI_API_VERSION') or self.config.get('api_version')
            
            if not api_key or api_key == 'your-azure-openai-api-key':
                current_app.logger.warning("Azure OpenAI API key not configured")
                return
            
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint
            )
            
            self.deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT') or self.config.get('deployment_name', 'gpt-4')
            current_app.logger.info("Azure OpenAI client initialized successfully")
            
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.client is not None
    
    def extract_entities(self, query: str, schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from natural language query"""
        if not self.is_available():
            return {"error": "LLM service not available", "entities": []}
        
        try:
            # Prepare schema context
            tables = list(schema_context.get('tables', {}).keys())
            columns = []
            for table_schema in schema_context.get('tables', {}).values():
                columns.extend(table_schema.get('columns', []))
            
            dictionary_terms = [term['term'] for term in schema_context.get('dictionary', [])]
            
            # Use prompt template from config
            prompt = current_app.config['PROMPTS']['entity_extraction'].format(
                query=query,
                tables=', '.join(tables),
                columns=', '.join(columns),
                dictionary_terms=', '.join(dictionary_terms)
            )
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert data analyst. Extract entities from queries and return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 2000),
                temperature=self.config.get('temperature', 0.1),
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Ensure we have the expected format
            if isinstance(result, list):
                return {"entities": result, "raw_response": content}
            elif 'entities' in result:
                return result
            else:
                return {"entities": [result] if result else [], "raw_response": content}
                
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error in entity extraction: {str(e)}")
            return {"error": "Failed to parse LLM response", "entities": [], "raw_response": content}
        except Exception as e:
            current_app.logger.error(f"Entity extraction error: {str(e)}")
            return {"error": str(e), "entities": []}
    
    def generate_sql(self, query: str, entities: List[Dict], mappings: Dict[str, Any], 
                     schema: Dict[str, Any], relationships: List[Dict] = None) -> Dict[str, Any]:
        """Generate SQL query from natural language query and context"""
        if not self.is_available():
            return {"error": "LLM service not available", "sql": "", "confidence": 0.0}
        
        try:
            # Use prompt template from config
            prompt = current_app.config['PROMPTS']['sql_generation'].format(
                query=query,
                entities=json.dumps(entities, indent=2),
                mappings=json.dumps(mappings, indent=2),
                schema=json.dumps(schema, indent=2),
                relationships=json.dumps(relationships or [], indent=2)
            )
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert SQL developer. Generate safe SELECT queries and return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 2000),
                temperature=self.config.get('temperature', 0.1),
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Validate SQL security
            sql = result.get('sql', '')
            if self._validate_sql_security(sql):
                return result
            else:
                return {
                    "error": "Generated SQL contains forbidden operations",
                    "sql": "",
                    "confidence": 0.0
                }
                
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error in SQL generation: {str(e)}")
            return {"error": "Failed to parse LLM response", "sql": "", "confidence": 0.0}
        except Exception as e:
            current_app.logger.error(f"SQL generation error: {str(e)}")
            return {"error": str(e), "sql": "", "confidence": 0.0}
    
    def generate_answer(self, original_query: str, sql_query: str, results: List[Dict], 
                       row_count: int) -> str:
        """Generate natural language answer from SQL results"""
        if not self.is_available():
            return "LLM service not available. Please configure Azure OpenAI."
        
        try:
            # Limit results for prompt to avoid token limits
            limited_results = results[:20] if len(results) > 20 else results
            
            prompt = current_app.config['PROMPTS']['answer_generation'].format(
                original_query=original_query,
                sql_query=sql_query,
                results=json.dumps(limited_results, indent=2),
                row_count=row_count
            )
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a business analyst. Provide clear, concise answers based on data results."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            current_app.logger.error(f"Answer generation error: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def enhance_dictionary_definition(self, term: str, definition: str, context_type: str, 
                                    tables: List[str]) -> str:
        """Enhance data dictionary definition using LLM"""
        if not self.is_available():
            return definition  # Return original if LLM not available
        
        try:
            prompt = current_app.config['PROMPTS']['dictionary_enhancement'].format(
                term=term,
                definition=definition,
                context_type=context_type,
                tables=', '.join(tables)
            )
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a data documentation expert. Improve data dictionary definitions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            enhanced_definition = response.choices[0].message.content.strip()
            return enhanced_definition if enhanced_definition else definition
            
        except Exception as e:
            current_app.logger.error(f"Dictionary enhancement error: {str(e)}")
            return definition
    
    def _validate_sql_security(self, sql: str) -> bool:
        """Validate SQL query for security"""
        if not sql:
            return False
        
        sql_upper = sql.upper().strip()
        
        # Check for forbidden keywords
        forbidden_keywords = current_app.config['SECURITY_CONFIG']['forbidden_sql_keywords']
        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                return False
        
        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return False
        
        # Check length
        max_length = current_app.config['SECURITY_CONFIG']['max_query_length']
        if len(sql) > max_length:
            return False
        
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Azure OpenAI connection"""
        if not self.is_available():
            return {
                "status": "error",
                "message": "Azure OpenAI client not initialized",
                "details": "Check API key and endpoint configuration"
            }
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "user", "content": "Say 'Connection test successful' if you can see this message."}
                ],
                max_tokens=50,
                temperature=0
            )
            
            return {
                "status": "success",
                "message": "Azure OpenAI connection successful",
                "response": response.choices[0].message.content,
                "model": self.deployment_name
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
                "details": "Check API key, endpoint, and deployment name"
            }