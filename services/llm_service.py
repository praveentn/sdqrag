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
            
            if not endpoint or endpoint == 'https://your-resource.openai.azure.com/':
                current_app.logger.warning("Azure OpenAI endpoint not configured")
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
                columns.extend([col.get('name', '') for col in table_schema.get('columns', [])])
            
            dictionary_terms = [term.get('term', '') for term in schema_context.get('dictionary', [])]
            
            # Use prompt template from config
            prompt = current_app.config['PROMPTS']['entity_extraction'].format(
                query=query,
                tables=', '.join(tables[:20]),  # Limit to avoid token overflow
                columns=', '.join(columns[:50]),  # Limit to avoid token overflow
                dictionary_terms=', '.join(dictionary_terms[:30])  # Limit to avoid token overflow
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
    
    def generate_sql(self, query: str, entities: List[Dict], mappings: List[Dict], 
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
            
            # Validate the response
            if 'sql' not in result:
                return {"error": "LLM did not generate SQL", "sql": "", "confidence": 0.0}
            
            sql_query = result.get('sql', '').strip()
            if not sql_query:
                return {"error": "Empty SQL query generated", "sql": "", "confidence": 0.0}
            
            # Basic SQL validation
            if not sql_query.lower().startswith('select'):
                return {"error": "Generated query is not a SELECT statement", "sql": "", "confidence": 0.0}
            
            return {
                "sql": sql_query,
                "confidence": result.get('confidence', 0.8),
                "explanation": result.get('explanation', ''),
                "raw_response": content
            }
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error in SQL generation: {str(e)}")
            return {"error": "Failed to parse LLM response", "sql": "", "confidence": 0.0}
        except Exception as e:
            current_app.logger.error(f"SQL generation error: {str(e)}")
            return {"error": str(e), "sql": "", "confidence": 0.0}
    
    def generate_final_response(self, query: str, sql_query: str, results: List[Dict]) -> Dict[str, Any]:
        """Generate natural language response from query results"""
        if not self.is_available():
            # Fallback response when LLM is not available
            if results:
                return {
                    "response": f"Found {len(results)} results for your query. The data shows the requested information from your database.",
                    "confidence": 0.5
                }
            else:
                return {
                    "response": "No results found for your query. You may want to try rephrasing your question or checking if the data exists.",
                    "confidence": 0.5
                }
        
        try:
            # Limit results for context (to avoid token overflow)
            sample_results = results[:5] if len(results) > 5 else results
            
            # Use prompt template from config
            prompt = current_app.config['PROMPTS']['response_generation'].format(
                query=query,
                sql_query=sql_query,
                results=json.dumps(sample_results, indent=2),
                total_results=len(results)
            )
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst. Provide clear, concise answers based on query results."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.get('max_tokens', 1000),
                temperature=self.config.get('temperature', 0.1)
            )
            
            content = response.choices[0].message.content.strip()
            
            return {
                "response": content,
                "confidence": 0.9,
                "raw_response": content
            }
            
        except Exception as e:
            current_app.logger.error(f"Final response generation error: {str(e)}")
            
            # Fallback response
            if results:
                return {
                    "response": f"Found {len(results)} results for your query. The data shows the requested information from your database.",
                    "confidence": 0.5,
                    "error": str(e)
                }
            else:
                return {
                    "response": "No results found for your query. You may want to try rephrasing your question or checking if the data exists.",
                    "confidence": 0.5,
                    "error": str(e)
                }
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze the intent and complexity of a natural language query"""
        if not self.is_available():
            return {"error": "LLM service not available", "intent": "unknown"}
        
        try:
            prompt = f"""
            Analyze the following query and determine:
            1. The main intent (aggregation, filtering, lookup, comparison, etc.)
            2. Complexity level (simple, moderate, complex)
            3. Expected result type (single value, list, table, summary)
            4. Key concepts mentioned
            
            Query: "{query}"
            
            Return a JSON object with: intent, complexity, result_type, concepts, confidence
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing data queries. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Query intent analysis error: {str(e)}")
            return {"error": str(e), "intent": "unknown"}
    
    def suggest_query_improvements(self, query: str, schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest improvements to a natural language query"""
        if not self.is_available():
            return {"error": "LLM service not available", "suggestions": []}
        
        try:
            tables = list(schema_context.get('tables', {}).keys())
            
            prompt = f"""
            Given this database schema with tables: {', '.join(tables[:10])}
            
            Analyze this query and suggest improvements:
            "{query}"
            
            Consider:
            1. Clarity and specificity
            2. Use of proper terminology
            3. Missing context or constraints
            4. Potential ambiguities
            
            Return JSON with: suggestions (list), clarity_score (0-1), specificity_score (0-1)
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert at improving data queries. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Query improvement suggestion error: {str(e)}")
            return {"error": str(e), "suggestions": []}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the LLM service connection"""
        if not self.is_available():
            return {
                "status": "error",
                "message": "LLM service not initialized",
                "available": False
            }
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "user", "content": "Return a simple JSON object with message: 'test successful'"}
                ],
                max_tokens=50,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return {
                "status": "success",
                "message": "LLM service connection successful",
                "available": True,
                "test_response": result
            }
            
        except Exception as e:
            current_app.logger.error(f"LLM connection test error: {str(e)}")
            return {
                "status": "error",
                "message": f"LLM service connection failed: {str(e)}",
                "available": False
            }