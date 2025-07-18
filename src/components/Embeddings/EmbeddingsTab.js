// src/components/Embeddings/EmbeddingsTab.js
import React, { useState, useEffect } from 'react';
import {
  CpuChipIcon,
  MagnifyingGlassIcon,
  CloudArrowDownIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  PlayIcon,
  StopIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const EmbeddingsTab = () => {
  const { activeProject } = useProject();
  const [activeTab, setActiveTab] = useState('models');
  const [availableModels, setAvailableModels] = useState([]);
  const [projectModels, setProjectModels] = useState([]);
  const [searchIndexes, setSearchIndexes] = useState([]);
  const [indexingTargets, setIndexingTargets] = useState({});
  const [loading, setLoading] = useState(false);
  const [showCreateIndex, setShowCreateIndex] = useState(false);

  useEffect(() => {
    if (activeProject) {
      loadAvailableModels();
      loadProjectModels();
      loadSearchIndexes();
      loadIndexingTargets();
    }
  }, [activeProject]);

  const loadAvailableModels = async () => {
    try {
      const response = await fetch('/api/embeddings/models/available');
      const data = await response.json();
      
      if (data.status === 'success') {
        setAvailableModels(data.models);
      }
    } catch (error) {
      console.error('Error loading available models:', error);
    }
  };

  const loadProjectModels = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/embeddings/${activeProject.id}/models`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setProjectModels(data.models);
      }
    } catch (error) {
      console.error('Error loading project models:', error);
    }
  };

  const loadSearchIndexes = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/embeddings/${activeProject.id}/indexes`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setSearchIndexes(data.indexes);
      }
    } catch (error) {
      console.error('Error loading search indexes:', error);
    }
  };

  const loadIndexingTargets = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/embeddings/${activeProject.id}/targets`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setIndexingTargets(data.targets);
      }
    } catch (error) {
      console.error('Error loading indexing targets:', error);
    }
  };

  const downloadModel = async (modelName) => {
    if (!activeProject) return;

    try {
      setLoading(true);
      const response = await fetch(`/api/embeddings/${activeProject.id}/models/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model_name: modelName }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success(`Model download started: ${modelName}`);
        
        // Start polling for model status
        pollModelStatus(modelName);
      } else {
        toast.error('Failed to start model download');
      }
    } catch (error) {
      console.error('Error downloading model:', error);
      toast.error('Failed to download model');
    } finally {
      setLoading(false);
    }
  };

  const pollModelStatus = (modelName) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/embeddings/${activeProject.id}/models`);
        const data = await response.json();
        
        if (data.status === 'success') {
          const model = data.models.find(m => m.model_name === modelName);
          if (model) {
            setProjectModels(data.models);
            
            if (model.status === 'ready') {
              toast.success(`Model ready: ${modelName}`);
              clearInterval(interval);
            } else if (model.status === 'error') {
              toast.error(`Model download failed: ${model.error_message}`);
              clearInterval(interval);
            }
          }
        }
      } catch (error) {
        console.error('Error polling model status:', error);
        clearInterval(interval);
      }
    }, 3000);

    // Clear interval after 5 minutes
    setTimeout(() => clearInterval(interval), 300000);
  };

  const deleteModel = async (modelId) => {
    if (!window.confirm('Are you sure you want to delete this model?')) {
      return;
    }

    try {
      const response = await fetch(`/api/embeddings/models/${modelId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Model deleted successfully');
        loadProjectModels();
      } else {
        toast.error(data.error || 'Failed to delete model');
      }
    } catch (error) {
      console.error('Error deleting model:', error);
      toast.error('Failed to delete model');
    }
  };

  const deleteIndex = async (indexId) => {
    if (!window.confirm('Are you sure you want to delete this index?')) {
      return;
    }

    try {
      const response = await fetch(`/api/embeddings/indexes/${indexId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Index deleted successfully');
        loadSearchIndexes();
      } else {
        toast.error('Failed to delete index');
      }
    } catch (error) {
      console.error('Error deleting index:', error);
      toast.error('Failed to delete index');
    }
  };

  const testIndex = async (indexId) => {
    const query = prompt('Enter a test query:');
    if (!query) return;

    try {
      const response = await fetch(`/api/embeddings/indexes/${indexId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        alert(`Test Results:\n\nQuery: ${data.query}\nResults found: ${data.results.length}\n\n${
          data.results.map((r, i) => `${i+1}. ${r.name || r.term} (score: ${r.score?.toFixed(3)})`).join('\n')
        }`);
      } else {
        toast.error('Index test failed');
      }
    } catch (error) {
      console.error('Error testing index:', error);
      toast.error('Failed to test index');
    }
  };

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <CpuChipIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Project Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please select a project to manage embeddings and indexes.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Embeddings & Indexing</h2>
            <p className="text-sm text-gray-600 mt-1">
              Configure embedding models and create search indexes for {activeProject.name}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <nav className="flex space-x-8 px-6">
          <button
            onClick={() => setActiveTab('models')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'models'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Embedding Models
          </button>
          <button
            onClick={() => setActiveTab('indexes')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'indexes'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Search Indexes
          </button>
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'models' ? (
          <ModelsSection
            availableModels={availableModels}
            projectModels={projectModels}
            onDownload={downloadModel}
            onDelete={deleteModel}
            loading={loading}
          />
        ) : (
          <IndexesSection
            searchIndexes={searchIndexes}
            projectModels={projectModels}
            indexingTargets={indexingTargets}
            onCreateIndex={() => setShowCreateIndex(true)}
            onDeleteIndex={deleteIndex}
            onTestIndex={testIndex}
            onRefresh={loadSearchIndexes}
          />
        )}
      </div>

      {/* Create Index Modal */}
      {showCreateIndex && (
        <CreateIndexModal
          projectId={activeProject.id}
          projectModels={projectModels}
          indexingTargets={indexingTargets}
          onClose={() => setShowCreateIndex(false)}
          onSuccess={() => {
            setShowCreateIndex(false);
            loadSearchIndexes();
          }}
        />
      )}
    </div>
  );
};

// Models Section Component
const ModelsSection = ({ availableModels, projectModels, onDownload, onDelete, loading }) => {
  const getModelStatus = (modelName) => {
    const projectModel = projectModels.find(m => m.model_name === modelName);
    return projectModel || null;
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-2">Available Models</h3>
        <p className="text-sm text-gray-600">
          Choose embedding models to download and use for semantic search
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {availableModels.map((model) => {
          const status = getModelStatus(model.name);
          
          return (
            <div key={model.name} className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h4 className="font-medium text-gray-900">{model.name.split('/')[1] || model.name}</h4>
                  <p className="text-sm text-gray-500 mt-1">{model.description}</p>
                  
                  <div className="mt-3 space-y-1 text-sm text-gray-600">
                    <div>Dimensions: {model.dimension}</div>
                    <div>Size: {model.size}</div>
                    <div>Type: {model.type}</div>
                  </div>
                </div>
                
                <div className="ml-4">
                  {status ? (
                    <ModelStatusBadge status={status} onDelete={() => onDelete(status.id)} />
                  ) : (
                    <button
                      onClick={() => onDownload(model.name)}
                      disabled={loading}
                      className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      <CloudArrowDownIcon className="h-4 w-4 mr-1" />
                      Download
                    </button>
                  )}
                </div>
              </div>

              {status && status.status === 'downloading' && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                    <span>Downloading...</span>
                    <span>{status.download_progress.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${status.download_progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Model Status Badge Component
const ModelStatusBadge = ({ status, onDelete }) => {
  const getStatusDisplay = () => {
    switch (status.status) {
      case 'ready':
        return {
          icon: <CheckCircleIcon className="h-4 w-4" />,
          text: 'Ready',
          className: 'bg-green-100 text-green-800'
        };
      case 'downloading':
        return {
          icon: <ArrowPathIcon className="h-4 w-4 animate-spin" />,
          text: 'Downloading',
          className: 'bg-yellow-100 text-yellow-800'
        };
      case 'error':
        return {
          icon: <ExclamationTriangleIcon className="h-4 w-4" />,
          text: 'Error',
          className: 'bg-red-100 text-red-800'
        };
      default:
        return {
          icon: <ArrowPathIcon className="h-4 w-4" />,
          text: 'Pending',
          className: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="flex items-center space-x-2">
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusDisplay.className}`}>
        {statusDisplay.icon}
        <span className="ml-1">{statusDisplay.text}</span>
      </span>
      
      {status.status === 'ready' && (
        <button
          onClick={onDelete}
          className="p-1 text-gray-400 hover:text-red-600 rounded"
          title="Delete Model"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
};

// Indexes Section Component
const IndexesSection = ({ searchIndexes, projectModels, indexingTargets, onCreateIndex, onDeleteIndex, onTestIndex, onRefresh }) => {
  const readyModels = projectModels.filter(m => m.status === 'ready');

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Search Indexes</h3>
          <p className="text-sm text-gray-600 mt-1">
            Create and manage search indexes for different data types
          </p>
        </div>
        
        <div className="flex space-x-3">
          <button
            onClick={onRefresh}
            className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            <ArrowPathIcon className="h-4 w-4 mr-2" />
            Refresh
          </button>
          
          <button
            onClick={onCreateIndex}
            disabled={readyModels.length === 0 && Object.keys(indexingTargets).length === 0}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Index
          </button>
        </div>
      </div>

      {searchIndexes.length === 0 ? (
        <div className="text-center py-12">
          <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No search indexes</h3>
          <p className="mt-1 text-sm text-gray-500">
            Create your first search index to enable semantic and keyword search.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {searchIndexes.map((index) => (
            <IndexCard
              key={index.id}
              index={index}
              onDelete={() => onDeleteIndex(index.id)}
              onTest={() => onTestIndex(index.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// Index Card Component
const IndexCard = ({ index, onDelete, onTest }) => {
  const getStatusDisplay = () => {
    switch (index.status) {
      case 'ready':
        return {
          icon: <CheckCircleIcon className="h-5 w-5 text-green-500" />,
          text: 'Ready',
          className: 'text-green-600'
        };
      case 'building':
        return {
          icon: <ArrowPathIcon className="h-5 w-5 text-yellow-500 animate-spin" />,
          text: 'Building',
          className: 'text-yellow-600'
        };
      case 'error':
        return {
          icon: <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />,
          text: 'Error',
          className: 'text-red-600'
        };
      default:
        return {
          icon: <ArrowPathIcon className="h-5 w-5 text-gray-500" />,
          text: 'Pending',
          className: 'text-gray-600'
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-medium text-gray-900">{index.index_name}</h4>
            {statusDisplay.icon}
          </div>
          
          <div className="mt-2 space-y-1 text-sm text-gray-600">
            <div>Type: {index.index_type.toUpperCase()}</div>
            <div>Target: {index.target_type}</div>
            {index.vector_count > 0 && <div>Vectors: {index.vector_count.toLocaleString()}</div>}
            {index.embedding_model && (
              <div>Model: {index.embedding_model.model_name.split('/')[1]}</div>
            )}
          </div>

          {index.status === 'building' && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                <span>Building...</span>
                <span>{index.build_progress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${index.build_progress}%` }}
                />
              </div>
            </div>
          )}

          {index.error_message && (
            <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
              {index.error_message}
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-1 ml-4">
          {index.status === 'ready' && (
            <button
              onClick={onTest}
              className="p-2 text-gray-400 hover:text-green-600 rounded"
              title="Test Index"
            >
              <PlayIcon className="h-4 w-4" />
            </button>
          )}
          
          <button
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-600 rounded"
            title="Delete Index"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

// Create Index Modal Component
const CreateIndexModal = ({ projectId, projectModels, indexingTargets, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    index_name: '',
    index_type: 'faiss',
    target_type: 'tables',
    embedding_model_id: '',
    target_ids: []
  });
  const [creating, setCreating] = useState(false);

  const readyModels = projectModels.filter(m => m.status === 'ready');
  const requiresEmbedding = formData.index_type === 'faiss';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setCreating(true);

    try {
      const response = await fetch(`/api/embeddings/${projectId}/indexes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Index creation started');
        onSuccess();
      } else {
        toast.error(data.message || 'Failed to create index');
      }
    } catch (error) {
      console.error('Error creating index:', error);
      toast.error('Failed to create index');
    } finally {
      setCreating(false);
    }
  };

  const handleTargetSelection = (targetId) => {
    setFormData(prev => ({
      ...prev,
      target_ids: prev.target_ids.includes(targetId)
        ? prev.target_ids.filter(id => id !== targetId)
        : [...prev.target_ids, targetId]
    }));
  };

  const selectAllTargets = () => {
    const allIds = indexingTargets[formData.target_type]?.map(t => t.id) || [];
    setFormData(prev => ({ ...prev, target_ids: allIds }));
  };

  const clearTargets = () => {
    setFormData(prev => ({ ...prev, target_ids: [] }));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
        
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full">
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">Create Search Index</h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Index Name</label>
                <input
                  type="text"
                  required
                  value={formData.index_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, index_name: e.target.value }))}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="e.g., tables_semantic_search"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Index Type</label>
                  <select
                    value={formData.index_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, index_type: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="faiss">FAISS (Semantic)</option>
                    <option value="tfidf">TF-IDF (Keyword)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Target Type</label>
                  <select
                    value={formData.target_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, target_type: e.target.value, target_ids: [] }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="tables">Tables</option>
                    <option value="columns">Columns</option>
                    <option value="dictionary">Dictionary</option>
                  </select>
                </div>
              </div>

              {requiresEmbedding && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Embedding Model</label>
                  <select
                    required={requiresEmbedding}
                    value={formData.embedding_model_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, embedding_model_id: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select a model</option>
                    {readyModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.model_name.split('/')[1]} ({model.embedding_dimension}d)
                      </option>
                    ))}
                  </select>
                  {readyModels.length === 0 && (
                    <p className="mt-1 text-sm text-red-600">
                      No embedding models available. Please download a model first.
                    </p>
                  )}
                </div>
              )}

              {indexingTargets[formData.target_type] && (
                <div>
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-gray-700">
                      Select Targets ({formData.target_ids.length} selected)
                    </label>
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={selectAllTargets}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        Select All
                      </button>
                      <button
                        type="button"
                        onClick={clearTargets}
                        className="text-sm text-gray-600 hover:text-gray-700"
                      >
                        Clear
                      </button>
                    </div>
                  </div>
                  
                  <div className="mt-2 max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2">
                    {indexingTargets[formData.target_type].map((target) => (
                      <label key={target.id} className="flex items-center space-x-2 p-1 hover:bg-gray-50 rounded">
                        <input
                          type="checkbox"
                          checked={formData.target_ids.includes(target.id)}
                          onChange={() => handleTargetSelection(target.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-900">
                          {target.name || target.term}
                          {target.description && (
                            <span className="text-gray-500 ml-1">- {target.description}</span>
                          )}
                        </span>
                      </label>
                    ))}
                  </div>
                  
                  <p className="mt-1 text-sm text-gray-500">
                    Leave empty to include all available targets
                  </p>
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating || (requiresEmbedding && !formData.embedding_model_id)}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create Index'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default EmbeddingsTab;