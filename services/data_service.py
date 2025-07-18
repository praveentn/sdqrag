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
                try:
                    # Read sheet
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Skip empty sheets
                    if df.empty:
                        current_app.logger.info(f"Skipping empty sheet: {sheet_name}")
                        continue
                    
                    # Clean column names
                    df.columns = [self._clean_column_name(col) for col in df.columns]
                    
                    # Create table name
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    table_name = self._clean_table_name(f"{base_name}_{sheet_name}")
                    
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
                        
                except Exception as e:
                    current_app.logger.error(f"Error processing sheet {sheet_name}: {str(e)}")
                    continue
            
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
        """Create SQLite table from DataFrame with proper data type handling"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Connect to database
            with sqlite3.connect(db_path) as conn:
                # Clean data before insertion
                df_clean = df.copy()
                
                # Handle different data types properly
                for col in df_clean.columns:
                    if df_clean[col].dtype == 'object':
                        # Handle mixed types and NaN values in object columns
                        df_clean[col] = df_clean[col].astype(str)
                        df_clean[col] = df_clean[col].replace(['nan', 'None', 'NaT'], '')
                    elif pd.api.types.is_numeric_dtype(df_clean[col]):
                        # Round numeric values to 3 decimal places as requested
                        df_clean[col] = df_clean[col].round(3)
                        # Fill NaN with None for proper NULL handling in SQLite
                        df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
                    elif pd.api.types.is_bool_dtype(df_clean[col]):
                        # Convert boolean to integer (SQLite doesn't have native boolean)
                        df_clean[col] = df_clean[col].astype(int)
                    elif pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                        # Convert datetime to string for SQLite
                        df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                        df_clean[col] = df_clean[col].fillna('')
                
                # Create table (replace if exists)
                df_clean.to_sql(table_name, conn, if_exists='replace', index=False)
                
                return {
                    "status": "success",
                    "message": f"Table {table_name} created successfully",
                    "row_count": len(df_clean),
                    "column_count": len(df_clean.columns)
                }
                
        except Exception as e:
            current_app.logger.error(f"Database table creation error: {str(e)}")
            return {
                "status": "error",
                "message": f"Table creation failed: {str(e)}"
            }

    def _create_table_info(self, project_id: int, data_source_id: int, 
                        table_name: str, original_name: str, df: pd.DataFrame) -> TableInfo:
        """Create TableInfo record with proper JSON serialization"""
        try:
            # Generate column information with JSON-safe types
            columns_info = []
            sample_data = []
            
            # Get sample rows (first 5 rows) for sample data
            if not df.empty:
                sample_rows = df.head(5).to_dict('records')
                # Convert to JSON-safe format
                for row in sample_rows:
                    clean_row = {}
                    for key, value in row.items():
                        if pd.isna(value):
                            clean_row[key] = None
                        elif isinstance(value, (bool, np.bool_)):
                            clean_row[key] = bool(value)  # Convert numpy bool to Python bool
                        elif isinstance(value, (int, np.integer)):
                            clean_row[key] = int(value)
                        elif isinstance(value, (float, np.floating)):
                            # Round to 3 decimal places as requested
                            clean_row[key] = round(float(value), 3) if not pd.isna(value) else None
                        else:
                            clean_row[key] = str(value)
                    sample_data.append(clean_row)
            
            # Generate schema information
            schema = {
                'table_name': table_name,
                'columns': []
            }
            
            for col in df.columns:
                # Get basic column info
                col_info = {
                    'name': col,
                    'type': str(df[col].dtype),
                    'nullable': bool(df[col].isnull().any()),  # Explicitly convert to Python bool
                    'unique_count': int(df[col].nunique()) if not df.empty else 0,
                    'null_count': int(df[col].isnull().sum()) if not df.empty else 0
                }
                
                # Get sample values (non-null, first 3 unique values)
                sample_values = df[col].dropna().unique()[:3].tolist()
                col_info['sample_values'] = [str(v) for v in sample_values]
                
                # Detect data type and add type-specific info
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info['data_type'] = 'numeric'
                    if not df[col].empty:
                        min_val = float(df[col].min())
                        max_val = float(df[col].max())
                        # Round to 3 decimal places as requested
                        col_info['min_value'] = round(min_val, 3) if not pd.isna(min_val) else None
                        col_info['max_value'] = round(max_val, 3) if not pd.isna(max_val) else None
                    else:
                        col_info['min_value'] = None
                        col_info['max_value'] = None
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
            
            # Set schema and sample data using the model methods
            table_info.set_schema(schema)
            table_info.set_sample_data(sample_data)
            
            db.session.add(table_info)
            db.session.commit()
            
            return table_info
            
        except Exception as e:
            current_app.logger.error(f"Table info creation error: {str(e)}")
            raise e

    def _clean_column_name(self, column_name: str) -> str:
        """Clean column name for database compatibility"""
        # Convert to string if not already
        column_name = str(column_name).strip()
        
        # Replace spaces and special characters with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', column_name)
        
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
        
        return cleaned.lower()

    def _clean_table_name(self, table_name: str) -> str:
        """Clean table name for database compatibility"""
        # Convert to string and strip whitespace
        table_name = str(table_name).strip()
        
        # Replace special characters with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)  # Fixed: use table_name not cleaned
        
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


    def generate_data_dictionary(self, project_id: int, 
                            config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Auto-generate data dictionary from table schemas"""
        try:
            config = config or {}
            entries_created = 0
            
            tables = TableInfo.query.filter_by(project_id=project_id).all()
            
            if not tables:
                return {
                    "status": "error",
                    "message": "No tables found to generate dictionary from"
                }
            
            for table in tables:
                schema = table.get_schema() if hasattr(table, 'get_schema') else {}
                
                # Generate table-level entry
                table_entry = DataDictionary(
                    project_id=project_id,
                    term=table.table_name,
                    definition=f"Data table containing {table.row_count} rows and {table.column_count} columns",
                    category='table',
                    source_table=table.table_name,
                    confidence_score=0.85
                )
                
                # Check if entry already exists
                existing = DataDictionary.query.filter_by(
                    project_id=project_id,
                    term=table.table_name,
                    category='table'
                ).first()
                
                if not existing:
                    db.session.add(table_entry)
                    entries_created += 1
                
                # Generate column-level entries
                columns = schema.get('columns', []) if schema else []
                
                # If no schema info, try to get from database directly
                if not columns:
                    try:
                        db_path = self._get_project_db_path(project_id)
                        if os.path.exists(db_path):
                            with sqlite3.connect(db_path) as conn:
                                cursor = conn.cursor()
                                cursor.execute(f"PRAGMA table_info({table.table_name})")
                                table_info = cursor.fetchall()
                                
                                for col_info in table_info:
                                    col_name = col_info[1]  # Column name
                                    col_type = col_info[2]  # Column type
                                    
                                    columns.append({
                                        'name': col_name,
                                        'type': col_type,
                                        'data_type': 'text' if 'text' in col_type.lower() else 'numeric' if any(x in col_type.lower() for x in ['int', 'real', 'num']) else 'unknown'
                                    })
                    except Exception as e:
                        current_app.logger.warning(f"Could not extract column info for {table.table_name}: {str(e)}")
                
                for column in columns:
                    col_name = column['name']
                    
                    # Generate definition based on column properties
                    definition_parts = []
                    
                    if column.get('data_type') == 'numeric':
                        definition_parts.append("Numeric field")
                        if column.get('min_value') is not None and column.get('max_value') is not None:
                            min_val = round(column['min_value'], 2) if isinstance(column['min_value'], float) else column['min_value']
                            max_val = round(column['max_value'], 2) if isinstance(column['max_value'], float) else column['max_value']
                            definition_parts.append(f"(range: {min_val} - {max_val})")
                    elif column.get('data_type') == 'datetime':
                        definition_parts.append("Date/time field")
                    else:
                        definition_parts.append("Text field")
                        if column.get('max_length'):
                            definition_parts.append(f"(max length: {column['max_length']})")
                    
                    if column.get('unique_count'):
                        definition_parts.append(f"with {column['unique_count']} unique values")
                    
                    definition = ' '.join(definition_parts) if definition_parts else f"Column in {table.table_name} table"
                    
                    # Create column entry
                    col_entry = DataDictionary(
                        project_id=project_id,
                        term=col_name,
                        definition=definition,
                        category='column',
                        source_table=table.table_name,
                        source_column=col_name,
                        confidence_score=0.75
                    )
                    
                    # Set examples from sample values
                    sample_values = column.get('sample_values', [])
                    if sample_values and hasattr(col_entry, 'set_examples'):
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
                
                # Generate potential abbreviations from column names
                column_names = [col['name'] for col in columns]
                abbreviations = self._extract_abbreviations(column_names)
                
                for abbr, expansion in abbreviations.items():
                    abbr_entry = DataDictionary(
                        project_id=project_id,
                        term=abbr,
                        definition=f"Abbreviation for '{expansion}'",
                        category='abbreviation',
                        source_table=table.table_name,
                        confidence_score=0.60
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
            db.session.rollback()
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
            'num': 'number',
            'desc': 'description',
            'addr': 'address',
            'tel': 'telephone',
            'fax': 'facsimile',
            'ref': 'reference',
            'seq': 'sequence',
            'temp': 'temperature',
            'max': 'maximum',
            'min': 'minimum',
            'avg': 'average',
            'std': 'standard',
            'pct': 'percent',
            'cnt': 'count',
            'src': 'source',
            'dest': 'destination',
            'curr': 'current',
            'prev': 'previous',
            'yr': 'year',
            'mo': 'month',
            'dt': 'date',
            'tm': 'time',
            'ts': 'timestamp'
        }
        
        for col_name in column_names:
            # Split column name by underscores
            parts = col_name.lower().split('_')
            
            for part in parts:
                if part in common_abbrevs:
                    abbreviations[part] = common_abbrevs[part]
                
                # Check for common patterns
                if len(part) <= 4 and part.endswith('_id'):
                    base = part[:-3]
                    if base:
                        abbreviations[part] = f"{base} identifier"
                
                # Numbers at end might indicate sequence
                if len(part) > 2 and part[-1].isdigit():
                    base = part[:-1]
                    if base in common_abbrevs:
                        abbreviations[part] = f"{common_abbrevs[base]} {part[-1]}"
        
        return abbreviations

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