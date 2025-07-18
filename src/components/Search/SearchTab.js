// src/components/Search/SearchTab.js
import React, { useState, useEffect } from 'react';
import {
  MagnifyingGlassIcon,
  BeakerIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  AdjustmentsHorizontalIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const SEARCH_METHODS = [
  {
    id: 'semantic',
    name: 'Semantic Search',
    description: 'Vector-based similarity using embeddings',
    icon: '🧠',
    color: 'blue'
  },
  {
    id: 'keyword',
    name: 'Keyword Search',
    description: 'TF-IDF based text matching',
    icon: '🔍',
    color: 'green'
  },
  {
    id: 'fuzzy',
    name: 'Fuzzy Matching',
    description: 'Approximate string matching',
    icon: '📝',
    color: 'yellow'
  },
  {
    id: 'exact',
    name: 'Exact Matching',
    description: 'Precise string matching',
    icon: '🎯',
    color: 'red'
  },
  {
    id: 'combined',
    name: 'Combined Search',
    description: 'All methods with intelligent ranking',
    icon: '⚡',
    color: 'purple'
  }
];

const SearchTab = () => {
  const { activeProject } = useProject();
  const [searchMethods, setSearchMethods] = useState({});
  const [query, setQuery] = useState('');
  const [selectedMethods, setSelectedMethods] = useState(['semantic', 'keyword']);
  const [searchResults, setSearchResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [benchmarkMode, setBenchmarkMode] = useState(false);
  const [benchmarkQueries, setBenchmarkQueries] = useState(['']);

  useEffect(() => {
    if (activeProject) {
      loadSearchMethods();
    }
  }, [activeProject]);

  const loadSearchMethods = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/search/${activeProject.id}/methods`);
      const data = await response.json();

      if (data.status === 'success') {
        setSearchMethods(data.methods);
      }
    } catch (error) {
      console.error('Error loading search methods:', error);
    }
  };

  const handleSearch = async (method = null) => {
    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setLoading(true);
    setSearchResults({});

    try {
      if (method) {
        // Single method search
        const result = await performSearch(method, query);
        setSearchResults({ [method]: result });
      } else {
        // Multiple methods search
        const results = {};
        
        for (const methodId of selectedMethods) {
          try {
            const result = await performSearch(methodId, query);
            results[methodId] = result;
          } catch (error) {
            console.error(`Error searching with ${methodId}:`, error);
            results[methodId] = {
              error: error.message || 'Search failed',
              results: []
            };
          }
        }
        
        setSearchResults(results);
      }
    } catch (error) {
      console.error('Search error:', error);
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const performSearch = async (method, searchQuery) => {
    const response = await fetch(`/api/search/${activeProject.id}/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: searchQuery,
        method: method,
        config: {
          semantic_top_k: 10,
          keyword_top_k: 10,
          fuzzy_threshold: 70,
          max_combined_results: 20
        }
      }),
    });

    const data = await response.json();
    
    if (data.status === 'success') {
      // Normalize the response structure
      let results = data.results;
      
      // Handle different response structures
      if (method === 'combined' && typeof results === 'object' && results !== null) {
        // For combined search, extract the combined_results or use the whole object
        return {
          results: results.combined_results || results,
          count: Array.isArray(results.combined_results) ? results.combined_results.length : 
                 (data.result_count || 0),
          method: data.method,
          query: data.query,
          details: results // Keep full details for combined search
        };
      } else {
        // For single method search, ensure results is an array
        const resultArray = Array.isArray(results) ? results : [];
        return {
          results: resultArray,
          count: resultArray.length,
          method: data.method,
          query: data.query
        };
      }
    } else {
      throw new Error(data.error || 'Search failed');
    }
  };

  const handleCompareSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`/api/search/${activeProject.id}/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          methods: selectedMethods,
          config: {}
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        // Normalize the comparison results
        const normalizedResults = {};
        Object.entries(data.results || {}).forEach(([method, methodData]) => {
          if (methodData.error) {
            normalizedResults[method] = {
              error: methodData.error,
              results: []
            };
          } else {
            // Ensure results is an array
            let results = methodData.results || [];
            if (!Array.isArray(results)) {
              results = [];
            }
            normalizedResults[method] = {
              results: results,
              count: results.length
            };
          }
        });
        
        setSearchResults(normalizedResults);
        toast.success(`Compared ${Object.keys(normalizedResults).length} methods`);
      } else {
        toast.error('Comparison failed');
      }
    } catch (error) {
      console.error('Comparison error:', error);
      toast.error('Comparison failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeQuery = async () => {
    if (!query.trim()) {
      toast.error('Please enter a query to analyze');
      return;
    }

    try {
      const response = await fetch(`/api/search/${activeProject.id}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setAnalysisResult(data.analysis);
      } else {
        toast.error('Analysis failed');
      }
    } catch (error) {
      console.error('Analysis error:', error);
      toast.error('Analysis failed');
    }
  };

  const handleBenchmark = async () => {
    const validQueries = benchmarkQueries.filter(q => q.trim());
    
    if (validQueries.length === 0) {
      toast.error('Please enter at least one benchmark query');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`/api/search/${activeProject.id}/benchmark`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          queries: validQueries,
          methods: selectedMethods
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setSearchResults({ benchmark: data.benchmark });
        toast.success(`Benchmarked ${validQueries.length} queries`);
      } else {
        toast.error('Benchmark failed');
      }
    } catch (error) {
      console.error('Benchmark error:', error);
      toast.error('Benchmark failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleMethod = (methodId) => {
    setSelectedMethods(prev =>
      prev.includes(methodId)
        ? prev.filter(id => id !== methodId)
        : [...prev, methodId]
    );
  };

  const addBenchmarkQuery = () => {
    setBenchmarkQueries(prev => [...prev, '']);
  };

  const updateBenchmarkQuery = (index, value) => {
    setBenchmarkQueries(prev => prev.map((q, i) => i === index ? value : q));
  };

  const removeBenchmarkQuery = (index) => {
    setBenchmarkQueries(prev => prev.filter((_, i) => i !== index));
  };

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Project Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please select a project to test search methods.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Search Testing</h2>
          <p className="text-sm text-gray-600 mt-1">
            Test and compare different search methods for your data
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setBenchmarkMode(!benchmarkMode)}
            className={`btn-secondary ${benchmarkMode ? 'bg-blue-100 text-blue-700' : ''}`}
          >
            <BeakerIcon className="h-4 w-4 mr-2" />
            {benchmarkMode ? 'Exit Benchmark' : 'Benchmark Mode'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Search Configuration */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              {benchmarkMode ? 'Benchmark Configuration' : 'Search Configuration'}
            </h3>

            {!benchmarkMode ? (
              <div className="space-y-4">
                {/* Query Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Search Query
                  </label>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Enter your search query..."
                    className="w-full input-field"
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  />
                </div>

                {/* Quick Action Buttons */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={handleAnalyzeQuery}
                    disabled={!query.trim()}
                    className="btn-ghost text-sm disabled:opacity-50"
                  >
                    <DocumentTextIcon className="h-4 w-4 mr-1" />
                    Analyze
                  </button>
                </div>

                {/* Analysis Results */}
                {analysisResult && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <h4 className="font-medium text-blue-900 mb-2">Query Analysis</h4>
                    <div className="text-sm text-blue-700 space-y-1">
                      <p>Length: {analysisResult.length} chars, {analysisResult.word_count} words</p>
                      {analysisResult.suggestions?.length > 0 && (
                        <div>
                          <p className="font-medium">Suggestions:</p>
                          <ul className="list-disc list-inside">
                            {analysisResult.suggestions.map((suggestion, idx) => (
                              <li key={idx}>{suggestion}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Benchmark Mode */
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Test Queries
                  </label>
                  {benchmarkQueries.map((q, index) => (
                    <div key={index} className="flex items-center space-x-2 mb-2">
                      <input
                        type="text"
                        value={q}
                        onChange={(e) => updateBenchmarkQuery(index, e.target.value)}
                        placeholder={`Query ${index + 1}...`}
                        className="flex-1 input-field"
                      />
                      {benchmarkQueries.length > 1 && (
                        <button
                          onClick={() => removeBenchmarkQuery(index)}
                          className="text-red-600 hover:text-red-800"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    onClick={addBenchmarkQuery}
                    className="btn-ghost text-sm"
                  >
                    + Add Query
                  </button>
                </div>
              </div>
            )}

            {/* Method Selection */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Search Methods
              </label>
              <div className="space-y-3">
                {SEARCH_METHODS.map((method) => {
                  const isAvailable = searchMethods[method.id]?.available;
                  const isSelected = selectedMethods.includes(method.id);
                  
                  return (
                    <div
                      key={method.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      } ${!isAvailable ? 'opacity-50' : ''}`}
                      onClick={() => isAvailable && toggleMethod(method.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => isAvailable && toggleMethod(method.id)}
                            disabled={!isAvailable}
                            className="rounded"
                          />
                          <span className="text-lg">{method.icon}</span>
                          <div>
                            <p className="font-medium text-gray-900">{method.name}</p>
                            <p className="text-sm text-gray-600">{method.description}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`text-sm font-medium ${
                            isAvailable ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {isAvailable ? 'Available' : 'Not Available'}
                          </p>
                          {searchMethods[method.id]?.indexes?.length > 0 && (
                            <p className="text-xs text-gray-500">
                              {searchMethods[method.id].indexes.length} indexes
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3 mt-6">
              {!benchmarkMode ? (
                <>
                  <button
                    onClick={() => handleSearch()}
                    disabled={loading || selectedMethods.length === 0 || !query.trim()}
                    className="w-full btn-primary disabled:opacity-50"
                  >
                    {loading ? (
                      <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <MagnifyingGlassIcon className="h-4 w-4 mr-2" />
                    )}
                    Search Selected Methods
                  </button>
                  
                  <button
                    onClick={handleCompareSearch}
                    disabled={loading || selectedMethods.length < 2 || !query.trim()}
                    className="w-full btn-secondary disabled:opacity-50"
                  >
                    <ChartBarIcon className="h-4 w-4 mr-2" />
                    Compare Methods
                  </button>
                </>
              ) : (
                <button
                  onClick={handleBenchmark}
                  disabled={loading || selectedMethods.length === 0 || benchmarkQueries.filter(q => q.trim()).length === 0}
                  className="w-full btn-primary disabled:opacity-50"
                >
                  {loading ? (
                    <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <BeakerIcon className="h-4 w-4 mr-2" />
                  )}
                  Run Benchmark
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Results</h3>
            
            {loading && (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="large" />
              </div>
            )}

            {!loading && Object.keys(searchResults).length === 0 ? (
              <div className="text-center py-12">
                <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No search results</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {benchmarkMode
                    ? 'Run a benchmark to see performance results'
                    : 'Enter a query and select methods to start searching'}
                </p>
              </div>
            ) : searchResults.benchmark ? (
              <BenchmarkResults results={searchResults.benchmark} />
            ) : (
              <SearchResults results={searchResults} query={query} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Search Results Component
const SearchResults = ({ results, query }) => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">
          Search Results for "{query}"
        </h3>
        <div className="text-sm text-gray-500">
          {Object.keys(results).length} method(s)
        </div>
      </div>

      {Object.entries(results).map(([method, data]) => (
        <MethodResults key={method} method={method} data={data} />
      ))}
    </div>
  );
};

// Method Results Component - FIXED VERSION
const MethodResults = ({ method, data }) => {
  const methodInfo = SEARCH_METHODS.find(m => m.id === method);
  
  if (data.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
          <h4 className="font-medium text-red-900">
            {methodInfo?.name || method} - Error
          </h4>
        </div>
        <p className="text-red-700 mt-1">{data.error}</p>
      </div>
    );
  }

  // Safely extract results - handle different response structures
  let results = [];
  let resultCount = 0;
  let isComplex = false;

  if (method === 'combined' && data.details) {
    // For combined search, check if we have combined_results
    if (data.details.combined_results && Array.isArray(data.details.combined_results)) {
      results = data.details.combined_results;
      isComplex = true;
    } else if (Array.isArray(data.results)) {
      results = data.results;
    }
  } else if (Array.isArray(data.results)) {
    results = data.results;
  } else if (data.results && typeof data.results === 'object') {
    // If results is an object, try to extract an array
    results = [];
  }

  resultCount = results.length;

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">{methodInfo?.icon || '🔍'}</span>
            <h4 className="font-medium text-gray-900">{methodInfo?.name || method}</h4>
          </div>
          <div className="text-sm text-gray-500">
            {resultCount} results
          </div>
        </div>
      </div>

      <div className="p-6">
        {isComplex ? (
          <CombinedResults data={data.details} />
        ) : resultCount === 0 ? (
          <p className="text-gray-500 text-center py-4">No results found</p>
        ) : (
          <div className="space-y-3">
            {results.slice(0, 10).map((result, index) => (
              <ResultItem key={index} result={result} rank={index + 1} />
            ))}
            {resultCount > 10 && (
              <p className="text-sm text-gray-500 text-center pt-2">
                ... and {resultCount - 10} more results
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Combined Results Component
const CombinedResults = ({ data }) => {
  const combined = data.combined_results || [];
  
  return (
    <div className="space-y-4">
      {/* Method Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        {Object.entries(data).map(([key, value]) => {
          if (key.endsWith('_results') && Array.isArray(value)) {
            const methodName = key.replace('_results', '').replace('_', ' ');
            return (
              <div key={key} className="text-center p-2 bg-gray-50 rounded">
                <div className="font-medium text-gray-900">{value.length}</div>
                <div className="text-gray-600 capitalize">{methodName}</div>
              </div>
            );
          }
          return null;
        })}
      </div>

      {/* Combined Results */}
      {combined.length > 0 ? (
        <div className="space-y-3">
          <h5 className="font-medium text-gray-900">Combined & Ranked Results</h5>
          {combined.slice(0, 15).map((result, index) => (
            <ResultItem key={index} result={result} rank={index + 1} showMethods />
          ))}
        </div>
      ) : (
        <p className="text-gray-500 text-center py-4">No combined results</p>
      )}
    </div>
  );
};

// Result Item Component
const ResultItem = ({ result, rank, showMethods = false }) => {
  const getTypeIcon = (type) => {
    switch (type) {
      case 'table': return '📊';
      case 'column': return '📋';
      case 'dictionary': return '📖';
      default: return '📄';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'table': return 'bg-blue-100 text-blue-800';
      case 'column': return 'bg-green-100 text-green-800';
      case 'dictionary': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex-shrink-0 w-8 h-8 bg-white rounded-full flex items-center justify-center text-sm font-medium text-gray-600">
        {rank}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getTypeIcon(result.type)}</span>
          <span className="font-medium text-gray-900">
            {result.name || result.term || result.table_name || 'Unknown'}
          </span>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getTypeColor(result.type)}`}>
            {result.type}
          </span>
          {result.score && (
            <span className="text-sm text-gray-500">
              {(result.score * 100).toFixed(1)}%
            </span>
          )}
        </div>
        
        {result.definition && (
          <p className="text-sm text-gray-600 mt-1 line-clamp-2">{result.definition}</p>
        )}
        
        {result.table_name && result.column_name && (
          <p className="text-sm text-gray-500 mt-1">
            {result.table_name}.{result.column_name}
          </p>
        )}
        
        {showMethods && result.search_methods && (
          <div className="flex items-center space-x-1 mt-2">
            {result.search_methods.map((method) => (
              <span
                key={method}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {method}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Benchmark Results Component
const BenchmarkResults = ({ results }) => {
  const { performance = {}, results: methodResults = {} } = results;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Benchmark Results</h3>

      {/* Performance Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="font-medium text-gray-900 mb-4">Performance Summary</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(performance).map(([method, stats]) => (
            <div key={method} className="text-center p-4 bg-gray-50 rounded-lg">
              <h5 className="font-medium text-gray-900 capitalize">{method}</h5>
              <div className="mt-2 space-y-1 text-sm">
                <div>
                  <span className="text-gray-600">Avg Time:</span>
                  <span className="ml-1 font-medium">{stats.average_time}s</span>
                </div>
                <div>
                  <span className="text-gray-600">Success Rate:</span>
                  <span className="ml-1 font-medium">{(stats.success_rate * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-gray-600">Total Time:</span>
                  <span className="ml-1 font-medium">{stats.total_time}s</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Results */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h4 className="font-medium text-gray-900">Detailed Results</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Method
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Queries
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Results
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Success Rate
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Object.entries(methodResults).map(([method, data]) => (
                <tr key={method}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {SEARCH_METHODS.find(m => m.id === method)?.name || method}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {Array.isArray(data) ? data.length : 0}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {Array.isArray(data) ? 
                      (data.reduce((sum, d) => sum + (d.result_count || 0), 0) / data.length).toFixed(1) : 
                      'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {performance[method]?.average_time || 'N/A'}s
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {performance[method] ? 
                      (performance[method].success_rate * 100).toFixed(1) + '%' : 
                      'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SearchTab;