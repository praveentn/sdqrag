// src/components/DataSources/DataSourcesTab.js
import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  CloudArrowUpIcon,
  DocumentIcon,
  ServerIcon,
  TableCellsIcon,
  EyeIcon,
  TrashIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const DataSourcesTab = () => {
  const { activeProject } = useProject();
  const [dataSources, setDataSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [showTableData, setShowTableData] = useState(null);
  const [tableData, setTableData] = useState(null);

  useEffect(() => {
    if (activeProject) {
      loadDataSources();
    }
  }, [activeProject]);

  const loadDataSources = async () => {
    if (!activeProject) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/datasources/${activeProject.id}`);
      const data = await response.json();

      if (data.status === 'success') {
        setDataSources(data.data_sources);
      } else {
        toast.error('Failed to load data sources');
      }
    } catch (error) {
      console.error('Error loading data sources:', error);
      toast.error('Failed to load data sources');
    } finally {
      setLoading(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!activeProject) {
      toast.error('Please select a project first');
      return;
    }

    setUploading(true);

    for (const file of acceptedFiles) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('project_id', activeProject.id);

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        if (data.status === 'success') {
          toast.success(`${file.name} uploaded successfully`);
        } else {
          toast.error(`Failed to upload ${file.name}: ${data.message}`);
        }
      } catch (error) {
        console.error('Upload error:', error);
        toast.error(`Failed to upload ${file.name}`);
      }
    }

    setUploading(false);
    loadDataSources();
  }, [activeProject]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json']
    },
    multiple: true
  });

  const handleDeleteSource = async (sourceId) => {
    if (!window.confirm('Are you sure you want to delete this data source?')) {
      return;
    }

    try {
      const response = await fetch(`/api/datasources/${sourceId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Data source deleted successfully');
        loadDataSources();
      } else {
        toast.error('Failed to delete data source');
      }
    } catch (error) {
      console.error('Error deleting data source:', error);
      toast.error('Failed to delete data source');
    }
  };

  const handleViewTable = async (tableId) => {
    setShowTableData(tableId);
    setTableData(null);

    try {
      const response = await fetch(`/api/datasources/tables/${tableId}/data?page=1&per_page=20`);
      const data = await response.json();

      if (data.status === 'success') {
        setTableData(data);
      } else {
        toast.error('Failed to load table data');
      }
    } catch (error) {
      console.error('Error loading table data:', error);
      toast.error('Failed to load table data');
    }
  };

  const generateDictionary = async () => {
    if (!activeProject) return;

    try {
      setLoading(true);
      const response = await fetch(`/api/datasources/${activeProject.id}/generate-dictionary`, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success(`Data dictionary generated! ${data.entries_created} entries created`);
      } else {
        toast.error('Failed to generate data dictionary');
      }
    } catch (error) {
      console.error('Error generating dictionary:', error);
      toast.error('Failed to generate data dictionary');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <ArrowPathIcon className="h-5 w-5 text-yellow-500 animate-spin" />;
      default:
        return <DocumentIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Project Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please select a project to manage data sources.
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
            <h2 className="text-lg font-semibold text-gray-900">Data Sources</h2>
            <p className="text-sm text-gray-600 mt-1">
              Upload files and configure database connections for {activeProject.name}
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={generateDictionary}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <DocumentIcon className="h-4 w-4 mr-2" />
              Generate Dictionary
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {/* File Upload Area */}
        <div className="mb-8">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragActive
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getInputProps()} />
            <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4">
              <h3 className="text-lg font-medium text-gray-900">
                {uploading ? 'Uploading...' : 'Upload Data Files'}
              </h3>
              <p className="text-sm text-gray-600 mt-2">
                {isDragActive
                  ? 'Drop files here to upload'
                  : 'Drag and drop files here, or click to select files'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Supports CSV, Excel (.xlsx, .xls), and JSON files
              </p>
            </div>
            {uploading && (
              <div className="mt-4">
                <LoadingSpinner size="medium" />
              </div>
            )}
          </div>
        </div>

        {/* Data Sources List */}
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <LoadingSpinner size="large" text="Loading data sources..." />
          </div>
        ) : dataSources.length === 0 ? (
          <div className="text-center py-12">
            <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No data sources</h3>
            <p className="mt-1 text-sm text-gray-500">
              Upload files to get started with your data analysis.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {dataSources.map((source) => (
              <div key={source.id} className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    {getStatusIcon(source.status)}
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900">{source.name}</h3>
                      <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                        <span>{source.source_type === 'file' ? 'File' : 'Database'}</span>
                        {source.file_name && <span>{source.file_name}</span>}
                        {source.file_size && (
                          <span>{(source.file_size / 1024 / 1024).toFixed(2)} MB</span>
                        )}
                        <span>{source.tables_count} tables</span>
                      </div>
                      {source.error_message && (
                        <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                          {source.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setSelectedSource(source.id === selectedSource ? null : source.id)}
                      className="p-2 text-gray-400 hover:text-gray-600 rounded"
                      title="View Details"
                    >
                      <EyeIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDeleteSource(source.id)}
                      className="p-2 text-gray-400 hover:text-red-600 rounded"
                      title="Delete Source"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Expanded Details */}
                {selectedSource === source.id && (
                  <div className="mt-6 pt-6 border-t border-gray-200">
                    <TablesSection 
                      sourceId={source.id} 
                      onViewTable={handleViewTable}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Table Data Modal */}
      {showTableData && (
        <TableDataModal
          tableId={showTableData}
          data={tableData}
          onClose={() => setShowTableData(null)}
        />
      )}
    </div>
  );
};

// Tables Section Component
const TablesSection = ({ sourceId, onViewTable }) => {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTables();
  }, [sourceId]);

  const loadTables = async () => {
    try {
      const response = await fetch(`/api/datasources/${sourceId}`);
      const data = await response.json();

      if (data.status === 'success') {
        setTables(data.data_source.tables || []);
      }
    } catch (error) {
      console.error('Error loading tables:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner size="medium" text="Loading tables..." />;
  }

  return (
    <div>
      <h4 className="text-sm font-medium text-gray-900 mb-3">Tables ({tables.length})</h4>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tables.map((table) => (
          <div key={table.id} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h5 className="font-medium text-gray-900">{table.table_name}</h5>
                <p className="text-sm text-gray-500 mt-1">
                  {table.row_count} rows • {table.column_count} columns
                </p>
                {table.description && (
                  <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                    {table.description}
                  </p>
                )}
              </div>
              <button
                onClick={() => onViewTable(table.id)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
                title="View Data"
              >
                <TableCellsIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Table Data Modal Component
const TableDataModal = ({ tableId, data, onClose }) => {
  if (!data) {
    return (
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
          <div className="relative bg-white rounded-lg p-6">
            <LoadingSpinner size="large" text="Loading table data..." />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
        
        <div className="relative bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Table Data</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="overflow-auto max-h-96 p-6">
            {data.data.length === 0 ? (
              <p className="text-gray-500">No data available</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      {data.columns.map((column) => (
                        <th
                          key={column}
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {data.data.map((row, index) => (
                      <tr key={index}>
                        {data.columns.map((column) => (
                          <td
                            key={column}
                            className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                          >
                            {row[column] !== null && row[column] !== undefined
                              ? String(row[column])
                              : '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-sm text-gray-600">
            Showing {data.data.length} of {data.pagination.total} rows
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataSourcesTab;