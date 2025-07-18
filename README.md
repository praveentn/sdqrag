# QueryForge - Enterprise RAG Platform

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

QueryForge is a professional enterprise-grade Retrieval-Augmented Generation (RAG) platform designed for structured data querying using natural language. It combines the power of Azure OpenAI with advanced embedding techniques to provide seamless data exploration capabilities.

## 🚀 Features

### Core Functionality
- **Multi-Project Management**: Organize your data analysis projects
- **Data Source Integration**: Upload CSV, Excel, JSON files or connect to databases
- **Intelligent Data Dictionary**: Auto-generate and manage data definitions
- **Multiple Embedding Models**: Support for various sentence-transformer models
- **Advanced Search**: Semantic, keyword, fuzzy, and exact search capabilities
- **Natural Language Chat**: Query your data using plain English
- **Admin Control Panel**: Complete system administration and monitoring

### Key Capabilities
- **Step-by-Step Query Processing**: Guided natural language to SQL conversion
- **Entity Extraction**: AI-powered identification of relevant data elements
- **Schema Mapping**: Intelligent mapping between natural language and database schema
- **Multiple Index Types**: FAISS, TF-IDF, and custom indexing strategies
- **Real-time Results**: Fast query execution with result visualization
- **Enterprise Security**: Role-based access and SQL injection prevention

## 📋 Requirements

### System Requirements
- **Python**: 3.8 or higher
- **Node.js**: 16 or higher (for React frontend)
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: 2GB+ free space
- **OS**: Windows, macOS, or Linux

### Services Required
- **Azure OpenAI**: For natural language processing
- **SQLite**: For data storage (included)

## 🛠️ Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd queryforge

# Run the automated setup script
python setup.py

# Follow the prompts to complete setup
```

### Option 2: Manual Setup

1. **Install Python Dependencies**
```bash
pip install -r requirements.txt
```

2. **Install Node.js Dependencies**
```bash
npm install
```

3. **Create Environment Configuration**
```bash
cp .env.example .env
# Edit .env file with your Azure OpenAI credentials
```

4. **Initialize Database**
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

5. **Download Embedding Models**
```bash
python setup.py --models sentence-transformers/all-MiniLM-L6-v2
```

6. **Build Frontend**
```bash
npm run build
```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
PORT=5000

# Database Configuration
DATABASE_URL=sqlite:///queryforge.db

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_MODEL=gpt-4

# File Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=104857600  # 100MB
```

### Azure OpenAI Setup
1. Create an Azure OpenAI resource in Azure portal
2. Deploy a GPT-4 model
3. Get your API key and endpoint
4. Update the .env file with your credentials

## 🏃‍♂️ Running the Application

### Development Mode
```bash
# Start the Flask backend
python app.py

# In another terminal, start React development server (optional)
npm start
```

### Production Mode
```bash
# Set production environment
export FLASK_ENV=production

# Start with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Accessing the Application
- **Web Interface**: http://localhost:5000
- **API Documentation**: http://localhost:5000/api/health
- **Default Login**: admin / admin123

## 📖 Usage Guide

### 1. Project Management
- **Create Project**: Click "New Project" and provide name/description
- **Select Project**: Use the sidebar dropdown to switch between projects
- **Project Stats**: View data sources, tables, and activity metrics

### 2. Data Sources
- **Upload Files**: Drag and drop CSV, Excel, or JSON files
- **View Tables**: Explore uploaded data with pagination
- **Schema Management**: Update table and column descriptions
- **Generate Dictionary**: Auto-create data definitions

### 3. Data Dictionary
- **Categories**: Encyclopedia, Abbreviations, Keywords, Domain Terms
- **Management**: Add, edit, delete, and verify dictionary entries
- **AI Enhancement**: Use LLM to improve definitions
- **Import/Export**: Bulk operations for dictionary management

### 4. Embeddings & Indexing
- **Download Models**: Choose from pre-configured embedding models
- **Create Indexes**: Build FAISS, TF-IDF, or custom search indexes
- **Monitor Progress**: Track download and build status
- **Test Searches**: Validate index performance

### 5. Search Testing
- **Multiple Methods**: Test semantic, keyword, fuzzy, and exact search
- **Compare Results**: Side-by-side comparison of search methods
- **Performance Metrics**: Analyze search speed and accuracy
- **Query Analysis**: Get suggestions for improving queries

### 6. Natural Language Chat
- **Quick Queries**: Fast natural language to SQL conversion
- **Step-by-Step**: Guided process with user confirmation
- **Query History**: Access previous conversations
- **Result Visualization**: View SQL and data results

### 7. Admin Panel
- **Database Browser**: Explore all system and project tables
- **SQL Executor**: Run custom SQL queries with syntax highlighting
- **System Health**: Monitor performance and resource usage
- **User Management**: Manage users and permissions
- **Backup/Restore**: Create and manage system backups

## 🤖 Automation Scripts

QueryForge includes powerful automation capabilities for batch operations:

### Basic Usage
```bash
# Create a new project
python automate.py create-project "My Project" --description "Description"

# Upload a file
python automate.py upload 1 /path/to/data.csv

# Bulk upload directory
python automate.py bulk-upload 1 /path/to/data/directory

# Complete project setup
python automate.py setup-project "Analytics Project" /data/folder

# Run a natural language query
python automate.py query 1 "Show me top 10 customers by revenue"

# Export project data
python automate.py export 1 project_backup.json
```

### Advanced Automation
```python
from automate import QueryForgeAutomation

# Initialize automation client
automation = QueryForgeAutomation('http://localhost:5000')

# Setup complete project
project = automation.setup_complete_project(
    name="Sales Analysis",
    data_directory="/data/sales",
    description="Q4 sales analysis project",
    embedding_model="sentence-transformers/all-mpnet-base-v2"
)

# Run multiple queries
queries = [
    "What are the top products by sales?",
    "Show monthly revenue trends",
    "List customers with orders > $1000"
]

for query in queries:
    result = automation.run_query(project['id'], query)
    print(f"Query: {query}")
    print(f"Response: {result['final_response']}")
```

## 🏗️ Architecture

### Backend Stack
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQLite (easily switchable to PostgreSQL)
- **AI Services**: Azure OpenAI GPT-4
- **Search**: FAISS, scikit-learn, fuzzy matching
- **Embeddings**: Sentence Transformers

### Frontend Stack
- **Framework**: React 18 with Hooks
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **State Management**: Context API
- **HTTP Client**: Fetch API

### Key Components
```
queryforge/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── config.py              # Configuration management
├── services/              # Core business logic
│   ├── llm_service.py     # Azure OpenAI integration
│   ├── embedding_service.py # Embedding and indexing
│   ├── search_service.py   # Search functionality
│   └── data_service.py    # Data processing
├── routes/                # API endpoints
├── src/                   # React frontend
└── automate.py           # Automation scripts
```

## 🔧 Development

### Adding New Features
1. **Backend**: Add routes in `routes/` and logic in `services/`
2. **Frontend**: Create components in `src/components/`
3. **Database**: Add models in `models.py` and run migrations
4. **Tests**: Add tests in `tests/` directory

### API Development
```python
# Example: Adding a new route
from flask import Blueprint, request, jsonify

new_bp = Blueprint('new_feature', __name__)

@new_bp.route('/endpoint', methods=['POST'])
def new_endpoint():
    data = request.get_json()
    # Process data
    return jsonify({'status': 'success', 'data': result})

# Register in app.py
app.register_blueprint(new_bp, url_prefix='/api/new')
```

### Frontend Development
```javascript
// Example: Adding a new component
import React, { useState, useEffect } from 'react';
import { useProject } from '../contexts/ProjectContext';

const NewComponent = () => {
  const { activeProject } = useProject();
  const [data, setData] = useState([]);

  // Component logic here

  return (
    <div className="p-6">
      {/* Component JSX */}
    </div>
  );
};

export default NewComponent;
```

## 🚀 Deployment

### Production Checklist
- [ ] Change SECRET_KEY in .env
- [ ] Set FLASK_ENV=production
- [ ] Use production database (PostgreSQL)
- [ ] Configure proper logging
- [ ] Set up SSL/HTTPS
- [ ] Configure backup strategy
- [ ] Monitor system resources

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN npm install && npm run build

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Cloud Deployment
- **Azure**: Use Azure App Service with PostgreSQL
- **AWS**: Deploy on EC2 with RDS
- **GCP**: Use Cloud Run with Cloud SQL

## 📊 Performance Optimization

### Database Optimization
- **Indexing**: Add indexes for frequently queried columns
- **Connection Pooling**: Configure SQLAlchemy pool settings
- **Query Optimization**: Use database profiling tools

### Search Performance
- **Model Selection**: Choose appropriate embedding models
- **Index Tuning**: Optimize FAISS parameters
- **Caching**: Implement Redis for search results

### Frontend Optimization
- **Code Splitting**: Implement lazy loading
- **Caching**: Use service workers
- **Bundle Optimization**: Configure webpack

## 🔒 Security

### Authentication & Authorization
- **User Management**: Role-based access control
- **Session Security**: Secure session management
- **API Security**: Rate limiting and validation

### Data Security
- **SQL Injection Prevention**: Parameterized queries
- **File Upload Security**: Type and size validation
- **Data Encryption**: Encrypt sensitive data

## 🐛 Troubleshooting

### Common Issues

**1. Azure OpenAI Connection Error**
```
Solution: Check API key, endpoint, and deployment name in .env
Test: python -c "from services.llm_service import LLMService; print(LLMService().test_connection())"
```

**2. Embedding Model Download Fails**
```
Solution: Check internet connection and disk space
Alternative: Download manually and place in models/ directory
```

**3. File Upload Errors**
```
Solution: Check file size limits and supported formats
Debug: Check server logs for detailed error messages
```

**4. Search Results Empty**
```
Solution: Ensure indexes are built and models are ready
Debug: Test individual search methods in Search tab
```

### Logs and Debugging
- **Application Logs**: `logs/app.log`
- **Error Logs**: Check browser console for frontend errors
- **Database Logs**: Enable SQLAlchemy logging in config
- **API Testing**: Use `/api/health` endpoint

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Setup
```bash
# Clone your fork
git clone <your-fork-url>
cd queryforge

# Create development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
npm install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check this README and code comments
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team

## 🗺️ Roadmap

### Upcoming Features
- [ ] Multi-database support (PostgreSQL, MySQL)
- [ ] Advanced analytics dashboard
- [ ] Real-time collaboration
- [ ] API authentication tokens
- [ ] Advanced visualization options
- [ ] Machine learning model integration
- [ ] Custom embedding models
- [ ] Multi-language support

### Long-term Goals
- [ ] Enterprise SSO integration
- [ ] Advanced security features
- [ ] Performance monitoring
- [ ] Cloud-native deployment
- [ ] Mobile application
- [ ] Voice query support

---

**QueryForge** - Transforming natural language into actionable data insights.

For more information, visit our [GitHub repository](https://github.com/your-org/queryforge) or contact the development team.