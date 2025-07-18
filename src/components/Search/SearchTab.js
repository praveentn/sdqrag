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
          const result = await performSearch(methodId, query);
          results[methodId] = result;
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
      return {
        results: data.results,
        count: data.result_count,
        method: data.method,
        query: data.query
      };
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
        setSearchResults(data.results);
        toast.success(`Compared ${data.methods_tested.length} methods`);
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
    <div className="h-full flex">
      {/* Left Sidebar - Search Controls */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Search Testing</h2>
          <p className="text-sm text-gray-600 mt-1">
            Test and compare different search methods
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Mode Toggle */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Mode</label>
            <div className="flex space-x-2">
              <button
                onClick={() => setBenchmarkMode(false)}
                className={`flex-1 px-3 py-2 text-sm font-medium rounded-md ${
                  !benchmarkMode
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-white text-gray-700 border border-gray-300'
                }`}
              >
                Single Query
              </button>
              <button
                onClick={() => setBenchmarkMode(true)}
                className={`flex-1 px-3 py-2 text-sm font-medium rounded-md ${
                  benchmarkMode
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-white text-gray-700 border border-gray-300'
                }`}
              >
                Benchmark
              </button>
            </div>
          </div>

          {/* Search Query */}
          {!benchmarkMode && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Search Query
              </label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your search query..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
              />
              <button
                onClick={handleAnalyzeQuery}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
              >
                <DocumentTextIcon className="h-4 w-4 inline mr-1" />
                Analyze Query
              </button>
            </div>
          )}

          {/* Benchmark Queries */}
          {benchmarkMode && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Benchmark Queries
                </label>
                <button
                  onClick={addBenchmarkQuery}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Add Query
                </button>
              </div>
              <div className="space-y-2">
                {benchmarkQueries.map((q, index) => (
                  <div key={index} className="flex space-x-2">
                    <input
                      type="text"
                      value={q}
                      onChange={(e) => updateBenchmarkQuery(index, e.target.value)}
                      placeholder={`Query ${index + 1}...`}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                    {benchmarkQueries.length > 1 && (
                      <button
                        onClick={() => removeBenchmarkQuery(index)}
                        className="px-2 py-2 text-red-600 hover:text-red-700"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Available Methods */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Search Methods
            </label>
            <div className="space-y-2">
              {SEARCH_METHODS.map((method) => {
                const isAvailable = searchMethods[method.id]?.available !== false;
                const isSelected = selectedMethods.includes(method.id);
                
                return (
                  <div
                    key={method.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      isSelected
                        ? 'border-blue-200 bg-blue-50'
                        : 'border-gray-200 bg-white hover:bg-gray-50'
                    } ${!isAvailable ? 'opacity-50 cursor-not-allowed' : ''}`}
                    onClick={() => isAvailable && toggleMethod(method.id)}
                  >
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        disabled={!isAvailable}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-lg">{method.icon}</span>
                          <span className="font-medium text-gray-900">{method.name}</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{method.description}</p>
                        {!isAvailable && (
                          <p className="text-xs text-red-600 mt-1">
                            {searchMethods[method.id]?.indexes?.length === 0
                              ? 'No indexes available'
                              : 'Not available'}
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
          <div className="space-y-3">
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

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Query Analysis */}
        {analysisResult && (
          <div className="bg-blue-50 border-b border-blue-200 p-4">
            <h3 className="font-medium text-blue-900 mb-2">Query Analysis</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-blue-700">Length:</span> {analysisResult.length} chars
              </div>
              <div>
                <span className="text-blue-700">Words:</span> {analysisResult.word_count}
              </div>
              <div>
                <span className="text-blue-700">Tables found:</span> {analysisResult.schema_matches?.tables?.length || 0}
              </div>
              <div>
                <span className="text-blue-700">Columns found:</span> {analysisResult.schema_matches?.columns?.length || 0}
              </div>
            </div>
            {analysisResult.suggestions?.length > 0 && (
              <div className="mt-2">
                <span className="text-blue-700 font-medium">Suggestions:</span>
                <ul className="mt-1 text-sm text-blue-800">
                  {analysisResult.suggestions.map((suggestion, index) => (
                    <li key={index}>• {suggestion}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Results Area */}
        <div className="flex-1 overflow-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <LoadingSpinner size="large" text="Searching..." />
            </div>
          ) : Object.keys(searchResults).length === 0 ? (
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

// Method Results Component
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

  const results = data.results || [];
  const isComplex = method === 'combined' && data.combined_results;

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">{methodInfo?.icon || '🔍'}</span>
            <h4 className="font-medium text-gray-900">{methodInfo?.name || method}</h4>
          </div>
          <div className="text-sm text-gray-500">
            {isComplex ? data.combined_results?.length : results.length} results
          </div>
        </div>
      </div>

      <div className="p-6">
        {isComplex ? (
          <CombinedResults data={data} />
        ) : results.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No results found</p>
        ) : (
          <div className="space-y-3">
            {results.slice(0, 10).map((result, index) => (
              <ResultItem key={index} result={result} rank={index + 1} />
            ))}
            {results.length > 10 && (
              <p className="text-sm text-gray-500 text-center pt-2">
                ... and {results.length - 10} more results
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
          <h4 className="font-medium text-gray-900">Query Results</h4>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Query
                </th>
                {Object.keys(performance).map((method) => (
                  <th key={method} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {method}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {Object.entries(methodResults).map(([method, queries]) => {
                if (queries.length === 0) return null;
                
                return queries.map((queryResult, index) => (
                  <tr key={`${method}-${index}`} className={index === 0 ? '' : 'bg-gray-50'}>
                    {index === 0 && (
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" rowSpan={queries.length}>
                        {queryResult.query}
                      </td>
                    )}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {queryResult.status === 'success' ? (
                        <div className="flex items-center space-x-2">
                          <CheckCircleIcon className="h-4 w-4 text-green-500" />
                          <span>{queryResult.result_count} results</span>
                          <span className="text-gray-500">({queryResult.time}s)</span>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2">
                          <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />
                          <span className="text-red-600">Error</span>
                        </div>
                      )}
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SearchTab;