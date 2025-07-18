# services/data_service.py
import os
import pandas as pd
import sqlite3
import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from werkzeug.utils import secure_filename
import numpy as np
from openpyxl import load_workbook
from flask import current_app
from models import Project, DataSource, TableInfo, DataDictionary, db
import chardet

class DataService:
    def __init__(self):
        self.supported_extensions = {
            '.csv': self._process_csv,
            '.xlsx': self._process_excel,
            '.xls': self._process_excel,
            '.json': self._process_json
        }
    
    def process_uploaded_file(self, file_path: str, project_id: int, 
                            filename: str) -> Dict[str, Any]:
        """Process uploaded file and create database tables"""
        try:
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in self.supported_extensions:
                return {
                    "status": "error",
                    "message": f"Unsupported file type: {file_ext}"
                }
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create data source record
            data_source = DataSource(
                project_id=project_id,
                name=os.path.splitext(filename)[0],
                source_type='file',
                file_path=file_path,
                file_name=filename,
                file_size=file_size,
                status='processing'
            )
            db.session.add(data_source)
            db.session.commit()
            
            # Process file based on extension
            processor = self.supported_extensions[file_ext]
            result = processor(file_path, project_id, data_source.id)
            
            # Update data source status
            if result['status'] == 'success':
                data_source.status = 'active'
            else:
                data_source.status = 'error'
                data_source.error_message = result.get('message', 'Unknown error')
            
            db.session.commit()
            
            # Add data source info to result
            result['data_source'] = data_source.to_dict()
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"File processing error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _process_csv(self, file_path: str, project_id: int, 
                    data_source_id: int) -> Dict[str, Any]:
        """Process CSV file"""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding_result = chardet.detect(raw_data)
                encoding = encoding_result.get('encoding', 'utf-8')
            
            # Read CSV
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Clean column names
            df.columns = [self._clean_column_name(col) for col in df.columns]
            
            # Get table name from filename
            table_name = os.path.splitext(os.path.basename(file_path))[0]
            table_name = self._clean_table_name(table_name)
            
            # Create database table
            db_path = self._get_project_db_path(project_id)
            result = self._create_db_table(df, db_path, table_name)
            
            if result['status'] == 'success':
                # Create table info record
                table_info = self._create_table_info(
                    project_id, data_source_id, table_name, table_name, df
                )
                
                return {
                    "status": "success",
                    "message": f"CSV processed successfully: {table_name}",
                    "tables_created": [table_info.to_dict()]
                }
            else:
                return result
                
        except Exception as e:
            current_app.logger.error(f"CSV processing error: {str(e)}")
            return {
                "status": "error",
                "message": f"CSV processing failed: {str(e)}"
            }
    
    def _process_excel(self, file_path: str, project_id: int, 
                      data_source_id: int) -> Dict[str, Any]:
        """Process Excel file (multiple sheets)"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            tables_created = []
            
            db_path = self._get_project_db_path(project_id)
            
            for sheet_name in excel_file.sheet_names:
                # Read sheet
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Skip empty sheets
                if df.empty:
                    continue
                
                # Clean column names
                df.columns = [self._clean_column_name(col) for col in df.columns]
                
                # Create table name
                table_name = self._clean_table_name(f"{os.path.splitext(os.path.basename(file_path))[0]}_{sheet_name}")
                
                # Create database table
                result = self._create_db_table(df, db_path, table_name)
                
                if result['status'] == 'success':
                    # Create table info record
                    table_info = self._create_table_info(
                        project_id, data_source_id, table_name, sheet_name, df
                    )
                    tables_created.append(table_info.to_dict())
                else:
                    current_app.logger.warning(f"Failed to process sheet {sheet_name}: {result.get('message')}")
            
            if tables_created:
                return {
                    "status": "success",
                    "message": f"Excel processed successfully: {len(tables_created)} sheets",
                    "tables_created": tables_created
                }
            else:
                return {
                    "status": "error",
                    "message": "No valid sheets found in Excel file"
                }
                
        except Exception as e:
            current_app.logger.error(f"Excel processing error: {str(e)}")
            return {
                "status": "error",
                "message": f"Excel processing failed: {str(e)}"
            }
    
    def _process_json(self, file_path: str, project_id: int, 
                     data_source_id: int) -> Dict[str, Any]:
        """Process JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.json_normalize(data)
            elif isinstance(data, dict):
                # Check if it's a nested structure
                if any(isinstance(v, list) for v in data.values()):
                    # Find the main data array
                    main_key = next((k for k, v in data.items() if isinstance(v, list)), None)
                    if main_key:
                        df = pd.json_normalize(data[main_key])
                    else:
                        df = pd.json_normalize([data])
                else:
                    df = pd.json_normalize([data])
            else:
                return {
                    "status": "error",
                    "message": "Unsupported JSON structure"
                }
            
            # Clean column names
            df.columns = [self._clean_column_name(col) for col in df.columns]
            
            # Get table name
            table_name = os.path.splitext(os.path.basename(file_path))[0]
            table_name = self._clean_table_name(table_name)
            
            # Create database table
            db_path = self._get_project_db_path(project_id)
            result = self._create_db_table(df, db_path, table_name)
            
            if result['status'] == 'success':
                # Create table info record
                table_info = self._create_table_info(
                    project_id, data_source_id, table_name, table_name, df
                )
                
                return {
                    "status": "success",
                    "message": f"JSON processed successfully: {table_name}",
                    "tables_created": [table_info.to_dict()]
                }
            else:
                return result
                
        except Exception as e:
            current_app.logger.error(f"JSON processing error: {str(e)}")
            return {
                "status": "error",
                "message": f"JSON processing failed: {str(e)}"
            }
    
    def _create_db_table(self, df: pd.DataFrame, db_path: str, 
                        table_name: str) -> Dict[str, Any]:
        """Create SQLite table from DataFrame"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Connect to database
            conn = sqlite3.connect(db_path)
            
            # Handle mixed data types
            df_clean = df.copy()
            
            # Convert object columns to string where appropriate
            for col in df_clean.columns:
                if df_clean[col].dtype == 'object':
                    # Try to convert to numeric first
                    try:
                        numeric_series = pd.to_numeric(df_clean[col], errors='coerce')
                        if numeric_series.notna().sum() / len(df_clean) > 0.8:  # 80% numeric
                            df_clean[col] = numeric_series
                        else:
                            df_clean[col] = df_clean[col].astype(str)
                    except:
                        df_clean[col] = df_clean[col].astype(str)
            
            # Save to database
            df_clean.to_sql(table_name, conn, if_exists='replace', index=False)
            conn.close()
            
            return {
                "status": "success",
                "message": f"Table {table_name} created successfully"
            }
            
        except Exception as e:
            current_app.logger.error(f"Database table creation error: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to create database table: {str(e)}"
            }
    
    def _create_table_info(self, project_id: int, data_source_id: int, 
                          table_name: str, original_name: str, 
                          df: pd.DataFrame) -> TableInfo:
        """Create TableInfo record with schema and sample data"""
        try:
            # Generate schema information
            schema = {
                'columns': [],
                'indexes': [],
                'constraints': []
            }
            
            # Get sample data (first 5 rows)
            sample_data = df.head(5).to_dict('records')
            
            # Process each column
            for col in df.columns:
                col_info = {
                    'name': col,
                    'type': str(df[col].dtype),
                    'nullable': df[col].isnull().any(),
                    'unique_count': df[col].nunique(),
                    'sample_values': df[col].dropna().head(5).tolist()
                }
                
                # Detect data type
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info['data_type'] = 'numeric'
                    col_info['min_value'] = float(df[col].min()) if not df[col].empty else None
                    col_info['max_value'] = float(df[col].max()) if not df[col].empty else None
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    col_info['data_type'] = 'datetime'
                else:
                    col_info['data_type'] = 'text'
                    col_info['max_length'] = int(df[col].astype(str).str.len().max()) if not df[col].empty else 0
                
                schema['columns'].append(col_info)
            
            # Create TableInfo record
            table_info = TableInfo(
                project_id=project_id,
                data_source_id=data_source_id,
                table_name=table_name,
                original_name=original_name,
                row_count=len(df),
                column_count=len(df.columns)
            )
            
            table_info.set_schema(schema)
            table_info.set_sample_data(sample_data)
            
            db.session.add(table_info)
            db.session.commit()
            
            return table_info
            
        except Exception as e:
            current_app.logger.error(f"Table info creation error: {str(e)}")
            raise e
    
    def generate_data_dictionary(self, project_id: int, 
                               config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Auto-generate data dictionary from table schemas"""
        try:
            config = config or {}
            entries_created = 0
            
            tables = TableInfo.query.filter_by(project_id=project_id).all()
            
            for table in tables:
                schema = table.get_schema()
                
                # Generate table-level entry
                table_entry = DataDictionary(
                    project_id=project_id,
                    term=table.table_name,
                    definition=f"Data table containing {table.row_count} rows and {table.column_count} columns",
                    category='encyclopedia',
                    source_table=table.table_name,
                    confidence_score=0.8
                )
                
                # Check if entry already exists
                existing = DataDictionary.query.filter_by(
                    project_id=project_id,
                    term=table.table_name,
                    category='encyclopedia'
                ).first()
                
                if not existing:
                    db.session.add(table_entry)
                    entries_created += 1
                
                # Generate column-level entries
                for column in schema.get('columns', []):
                    col_name = column['name']
                    
                    # Generate definition based on column properties
                    definition_parts = []
                    
                    if column.get('data_type') == 'numeric':
                        definition_parts.append(f"Numeric field")
                        if column.get('min_value') is not None:
                            definition_parts.append(f"(range: {column['min_value']:.2f} - {column['max_value']:.2f})")
                    elif column.get('data_type') == 'datetime':
                        definition_parts.append("Date/time field")
                    else:
                        definition_parts.append("Text field")
                        if column.get('max_length'):
                            definition_parts.append(f"(max length: {column['max_length']})")
                    
                    if column.get('unique_count'):
                        definition_parts.append(f"with {column['unique_count']} unique values")
                    
                    definition = ' '.join(definition_parts)
                    
                    # Create column entry
                    col_entry = DataDictionary(
                        project_id=project_id,
                        term=col_name,
                        definition=definition,
                        category='encyclopedia',
                        source_table=table.table_name,
                        source_column=col_name,
                        confidence_score=0.7
                    )
                    
                    # Set examples from sample values
                    sample_values = column.get('sample_values', [])
                    if sample_values:
                        col_entry.set_examples([str(v) for v in sample_values[:3]])
                    
                    # Check if entry already exists
                    existing_col = DataDictionary.query.filter_by(
                        project_id=project_id,
                        term=col_name,
                        source_table=table.table_name,
                        source_column=col_name
                    ).first()
                    
                    if not existing_col:
                        db.session.add(col_entry)
                        entries_created += 1
                
                # Generate abbreviations from column names
                abbreviations = self._extract_abbreviations([col['name'] for col in schema.get('columns', [])])
                
                for abbr, expansion in abbreviations.items():
                    abbr_entry = DataDictionary(
                        project_id=project_id,
                        term=abbr,
                        definition=f"Abbreviation for '{expansion}'",
                        category='abbreviation',
                        source_table=table.table_name,
                        confidence_score=0.6
                    )
                    
                    # Check if entry already exists
                    existing_abbr = DataDictionary.query.filter_by(
                        project_id=project_id,
                        term=abbr,
                        category='abbreviation'
                    ).first()
                    
                    if not existing_abbr:
                        db.session.add(abbr_entry)
                        entries_created += 1
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": f"Data dictionary generated successfully",
                "entries_created": entries_created
            }
            
        except Exception as e:
            current_app.logger.error(f"Data dictionary generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _extract_abbreviations(self, column_names: List[str]) -> Dict[str, str]:
        """Extract potential abbreviations from column names"""
        abbreviations = {}
        
        # Common abbreviations mapping
        common_abbrevs = {
            'id': 'identifier',
            'qty': 'quantity',
            'amt': 'amount',
            'desc': 'description',
            'addr': 'address',
            'num': 'number',
            'dt': 'date',
            'tm': 'time',
            'cd': 'code',
            'nm': 'name',
            'val': 'value',
            'pct': 'percent',
            'cnt': 'count',
            'avg': 'average',
            'max': 'maximum',
            'min': 'minimum',
            'std': 'standard',
            'temp': 'temperature'
        }
        
        for col_name in column_names:
            # Split by common separators
            parts = re.split(r'[_\-\s]', col_name.lower())
            
            for part in parts:
                if part in common_abbrevs:
                    abbreviations[part.upper()] = common_abbrevs[part]
                
                # Look for potential abbreviations (short words with consonants)
                if len(part) <= 4 and len(part) >= 2:
                    if not re.match(r'^[aeiou]+$', part):  # Not all vowels
                        # This could be an abbreviation
                        abbreviations[part.upper()] = f"Possible abbreviation found in column '{col_name}'"
        
        return abbreviations
    
    def _clean_column_name(self, col_name: str) -> str:
        """Clean and standardize column names"""
        # Convert to string and strip whitespace
        cleaned = str(col_name).strip()
        
        # Replace special characters with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned)
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # Ensure it doesn't start with a number
        if cleaned and cleaned[0].isdigit():
            cleaned = f"col_{cleaned}"
        
        # Handle empty names
        if not cleaned:
            cleaned = "unnamed_column"
        
        return cleaned
    
    def _clean_table_name(self, table_name: str) -> str:
        """Clean and standardize table names"""
        # Convert to string and strip whitespace
        cleaned = str(table_name).strip()
        
        # Replace special characters with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned)
        
        # Remove multiple consecutive underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        
        # Ensure it doesn't start with a number
        if cleaned and cleaned[0].isdigit():
            cleaned = f"table_{cleaned}"
        
        # Handle empty names
        if not cleaned:
            cleaned = "unnamed_table"
        
        return cleaned.lower()
    
    def _get_project_db_path(self, project_id: int) -> str:
        """Get database file path for project"""
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return os.path.join(upload_folder, f"project_{project_id}.db")
    
    def test_database_connection(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test database connection"""
        try:
            db_type = connection_config.get('type', '').lower()
            
            if db_type == 'sqlite':
                db_path = connection_config.get('path', '')
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()
                    
                    return {
                        "status": "success",
                        "message": "SQLite connection successful",
                        "tables_found": len(tables),
                        "tables": [table[0] for table in tables]
                    }
                else:
                    return {
                        "status": "error",
                        "message": "SQLite database file not found"
                    }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported database type: {db_type}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}"
            }