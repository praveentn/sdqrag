// src/components/Admin/AdminTab.js
import React, { useState, useEffect } from 'react';
import {
  Cog6ToothIcon,
  TableCellsIcon,
  CodeBracketIcon,
  HeartIcon,
  UsersIcon,
  DocumentArrowDownIcon,
  WrenchScrewdriverIcon,
  DocumentTextIcon,
  PlayIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CpuChipIcon,
  CircleStackIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const ADMIN_TABS = [
  { id: 'database', name: 'Database Browser', icon: TableCellsIcon },
  { id: 'sql', name: 'SQL Executor', icon: CodeBracketIcon },
  { id: 'health', name: 'System Health', icon: HeartIcon },
  { id: 'users', name: 'User Management', icon: UsersIcon },
  { id: 'backup', name: 'Backup & Restore', icon: DocumentArrowDownIcon },
  { id: 'optimization', name: 'Database Optimization', icon: WrenchScrewdriverIcon },
  { id: 'logs', name: 'System Logs', icon: DocumentTextIcon }
];

const AdminTab = () => {
  const [activeTab, setActiveTab] = useState('database');
  const [loading, setLoading] = useState(false);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Admin Control Panel</h2>
            <p className="text-sm text-gray-600 mt-1">
              System administration and database management tools
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">System Online</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <nav className="flex space-x-8 px-6 overflow-x-auto">
          {ADMIN_TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'database' && <DatabaseBrowser />}
        {activeTab === 'sql' && <SQLExecutor />}
        {activeTab === 'health' && <SystemHealth />}
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'backup' && <BackupRestore />}
        {activeTab === 'optimization' && <DatabaseOptimization />}
        {activeTab === 'logs' && <SystemLogs />}
      </div>
    </div>
  );
};

// Database Browser Component
const DatabaseBrowser = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadTables();
  }, []);

  const loadTables = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/tables');
      const data = await response.json();

      if (data.status === 'success') {
        setTables(data.tables);
      } else {
        toast.error('Failed to load tables');
      }
    } catch (error) {
      console.error('Error loading tables:', error);
      toast.error('Failed to load tables');
    } finally {
      setLoading(false);
    }
  };

  const loadTableData = async (tableName, pageNum = 1) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/tables/${encodeURIComponent(tableName)}/data?page=${pageNum}&per_page=50`);
      const data = await response.json();

      if (data.status === 'success') {
        setTableData(data);
        setSelectedTable(tableName);
        setPage(pageNum);
      } else {
        toast.error('Failed to load table data');
      }
    } catch (error) {
      console.error('Error loading table data:', error);
      toast.error('Failed to load table data');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Tables List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">Database Tables</h3>
            <button
              onClick={loadTables}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
            >
              <ArrowPathIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {loading && !tableData ? (
            <div className="flex items-center justify-center h-32">
              <LoadingSpinner size="medium" />
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {tables.map((table) => (
                <button
                  key={table.name}
                  onClick={() => loadTableData(table.name)}
                  className={`w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors ${
                    selectedTable === table.name ? 'bg-blue-50 border border-blue-200' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <TableCellsIcon className="h-4 w-4 text-gray-400" />
                      <span className="font-medium text-gray-900 truncate">{table.name}</span>
                    </div>
                    <span className="text-xs text-gray-500">{table.row_count}</span>
                  </div>
                  <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                    <span>{table.type}</span>
                    {table.project_name && <span>Project: {table.project_name}</span>}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table Data */}
      <div className="flex-1 flex flex-col">
        {tableData ? (
          <>
            <div className="bg-white border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-gray-900">{selectedTable}</h4>
                  <p className="text-sm text-gray-600">
                    {tableData.pagination.total} rows • Page {page} of {tableData.pagination.pages}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex-1 overflow-auto p-6">
              {tableData.data.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No data in this table</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        {tableData.columns.map((column) => (
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
                      {tableData.data.map((row, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          {tableData.columns.map((column) => (
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
              
              {/* Pagination */}
              {tableData.pagination.pages > 1 && (
                <div className="flex items-center justify-between mt-6">
                  <button
                    onClick={() => loadTableData(selectedTable, page - 1)}
                    disabled={page === 1}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-600">
                    Page {page} of {tableData.pagination.pages}
                  </span>
                  <button
                    onClick={() => loadTableData(selectedTable, page + 1)}
                    disabled={page === tableData.pagination.pages}
                    className="btn-secondary disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <TableCellsIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No Table Selected</h3>
              <p className="mt-1 text-sm text-gray-500">
                Select a table from the list to view its data
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// SQL Executor Component
const SQLExecutor = () => {
  const [sql, setSql] = useState('SELECT * FROM projects LIMIT 10;');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [targetDb, setTargetDb] = useState('system');
  const [confirmDangerous, setConfirmDangerous] = useState(false);
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/projects/');
      const data = await response.json();
      if (data.status === 'success') {
        setProjects(data.projects);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    }
  };

  const executeSQL = async () => {
    if (!sql.trim()) {
      toast.error('Please enter a SQL query');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/admin/sql/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sql: sql,
          target_db: targetDb,
          confirm_dangerous: confirmDangerous
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setResults(data);
        toast.success('Query executed successfully');
      } else if (data.status === 'warning') {
        setResults(data);
        toast.warning('Query requires confirmation');
      } else {
        toast.error(data.error || 'Query execution failed');
        setResults({ error: data.error });
      }
    } catch (error) {
      console.error('Error executing SQL:', error);
      toast.error('Failed to execute query');
      setResults({ error: 'Network error' });
    } finally {
      setLoading(false);
      setConfirmDangerous(false);
    }
  };

  const formatSQL = () => {
    // Basic SQL formatting
    const formatted = sql
      .replace(/SELECT/gi, 'SELECT')
      .replace(/FROM/gi, '\nFROM')
      .replace(/WHERE/gi, '\nWHERE')
      .replace(/JOIN/gi, '\nJOIN')
      .replace(/ORDER BY/gi, '\nORDER BY')
      .replace(/GROUP BY/gi, '\nGROUP BY')
      .replace(/HAVING/gi, '\nHAVING')
      .replace(/LIMIT/gi, '\nLIMIT');
    
    setSql(formatted);
  };

  return (
    <div className="p-6">
      <div className="space-y-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">SQL Query Executor</h3>
            <div className="flex items-center space-x-4">
              <select
                value={targetDb}
                onChange={(e) => setTargetDb(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="system">System Database</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    Project: {project.name}
                  </option>
                ))}
              </select>
              <button
                onClick={formatSQL}
                className="btn-secondary"
              >
                Format SQL
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                SQL Query
              </label>
              <textarea
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                placeholder="Enter your SQL query here..."
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={executeSQL}
                  disabled={loading}
                  className="btn-primary disabled:opacity-50"
                >
                  {loading ? (
                    <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <PlayIcon className="h-4 w-4 mr-2" />
                  )}
                  Execute Query
                </button>
                
                {results?.requires_confirmation && (
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={confirmDangerous}
                      onChange={(e) => setConfirmDangerous(e.target.checked)}
                      className="rounded border-gray-300 text-red-600 focus:ring-red-500"
                    />
                    <span className="text-sm text-red-600">
                      Confirm dangerous operation
                    </span>
                  </label>
                )}
              </div>
              
              <div className="text-sm text-gray-500">
                Target: {targetDb === 'system' ? 'System Database' : projects.find(p => p.id == targetDb)?.name}
              </div>
            </div>
          </div>
        </div>

        {/* Results */}
        {results && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h4 className="font-medium text-gray-900 mb-4">Query Results</h4>
            
            {results.error ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                  <span className="font-medium text-red-900">Error</span>
                </div>
                <p className="text-red-700 mt-2 font-mono text-sm">{results.error}</p>
              </div>
            ) : results.requires_confirmation ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                  <span className="font-medium text-yellow-900">Warning</span>
                </div>
                <p className="text-yellow-700 mt-2">{results.message}</p>
                {results.dangerous_operations && (
                  <div className="mt-2">
                    <span className="text-yellow-700 font-medium">Dangerous operations detected:</span>
                    <ul className="mt-1 text-yellow-700">
                      {results.dangerous_operations.map((op, index) => (
                        <li key={index}>• {op}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : results.execution_type === 'SELECT' ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-600">
                    {results.row_count} rows returned
                  </span>
                  <CheckCircleIcon className="h-5 w-5 text-green-500" />
                </div>
                
                {results.data && results.data.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          {results.columns.map((column) => (
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
                        {results.data.map((row, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            {results.columns.map((column) => (
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
                ) : (
                  <p className="text-gray-500 text-center py-4">No data returned</p>
                )}
              </div>
            ) : (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <CheckCircleIcon className="h-5 w-5 text-green-500" />
                  <span className="font-medium text-green-900">Success</span>
                </div>
                <p className="text-green-700 mt-2">
                  {results.message} ({results.rows_affected} rows affected)
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// System Health Component
const SystemHealth = () => {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadHealthData();
    const interval = setInterval(loadHealthData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadHealthData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/system/health');
      const data = await response.json();

      if (data.status === 'success') {
        setHealthData(data.health);
      } else {
        toast.error('Failed to load system health');
      }
    } catch (error) {
      console.error('Error loading health data:', error);
      toast.error('Failed to load system health');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !healthData) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="large" text="Loading system health..." />
      </div>
    );
  }

  if (!healthData) {
    return (
      <div className="p-6">
        <div className="text-center">
          <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-red-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">Health Data Unavailable</h3>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <HealthCard
          title="CPU Usage"
          value={`${healthData.system.cpu_percent.toFixed(1)}%`}
          icon={<CpuChipIcon className="h-6 w-6" />}
          color={healthData.system.cpu_percent > 80 ? 'red' : healthData.system.cpu_percent > 60 ? 'yellow' : 'green'}
        />
        
        <HealthCard
          title="Memory Usage"
          value={`${healthData.system.memory.percent.toFixed(1)}%`}
          subtitle={`${healthData.system.memory.used_gb}GB / ${healthData.system.memory.total_gb}GB`}
          icon={<CircleStackIcon className="h-6 w-6" />}
          color={healthData.system.memory.percent > 80 ? 'red' : healthData.system.memory.percent > 60 ? 'yellow' : 'green'}
        />
        
        <HealthCard
          title="Disk Usage"
          value={`${healthData.system.disk.percent.toFixed(1)}%`}
          subtitle={`${healthData.system.disk.used_gb}GB / ${healthData.system.disk.total_gb}GB`}
          icon={<CircleStackIcon className="h-6 w-6" />}
          color={healthData.system.disk.percent > 90 ? 'red' : healthData.system.disk.percent > 80 ? 'yellow' : 'green'}
        />
      </div>

      {/* Services Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Services Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ServiceStatus
            name="LLM Service"
            status={healthData.services.llm_available ? 'healthy' : 'error'}
            description="Azure OpenAI"
          />
          <ServiceStatus
            name="Embedding Models"
            status="healthy"
            description={`${healthData.services.embedding_models_ready} ready`}
          />
          <ServiceStatus
            name="Search Indexes"
            status="healthy"
            description={`${healthData.services.search_indexes_ready} ready`}
          />
          <ServiceStatus
            name="Database"
            status="healthy"
            description="SQLite"
          />
        </div>
      </div>

      {/* Database Statistics */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Database Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(healthData.database.system_tables).map(([table, count]) => (
            <div key={table} className="text-center p-3 bg-gray-50 rounded">
              <div className="text-lg font-semibold text-gray-900">{count}</div>
              <div className="text-sm text-gray-600 capitalize">{table.replace('_', ' ')}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Storage Usage */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Storage Usage</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(healthData.application.storage_usage).map(([folder, usage]) => (
            <div key={folder} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900 capitalize">{folder}</span>
                <span className="text-sm text-gray-600">{usage.size_mb} MB</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">
              {healthData.application.recent_activity.recent_queries}
            </div>
            <div className="text-sm text-blue-700">Queries (24h)</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {healthData.application.recent_activity.active_sessions}
            </div>
            <div className="text-sm text-green-700">Active Sessions</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-2xl font-bold text-purple-600">
              {healthData.application.recent_activity.recent_projects}
            </div>
            <div className="text-sm text-purple-700">Recent Projects</div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Health Card Component
const HealthCard = ({ title, value, subtitle, icon, color }) => {
  const colorClasses = {
    green: 'text-green-600 bg-green-50 border-green-200',
    yellow: 'text-yellow-600 bg-yellow-50 border-yellow-200',
    red: 'text-red-600 bg-red-50 border-red-200'
  };

  return (
    <div className={`p-6 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          {icon}
        </div>
        <div className="ml-4">
          <h3 className="text-sm font-medium text-gray-900">{title}</h3>
          <p className="text-2xl font-semibold">{value}</p>
          {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
};

// Service Status Component
const ServiceStatus = ({ name, status, description }) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  return (
    <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
      {getStatusIcon()}
      <div>
        <div className="font-medium text-gray-900">{name}</div>
        <div className="text-sm text-gray-600">{description}</div>
      </div>
    </div>
  );
};

// User Management Component (placeholder)
const UserManagement = () => (
  <div className="p-6">
    <div className="text-center">
      <UsersIcon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">User Management</h3>
      <p className="mt-1 text-sm text-gray-500">User management features coming soon</p>
    </div>
  </div>
);

// Backup & Restore Component (placeholder)
const BackupRestore = () => (
  <div className="p-6">
    <div className="text-center">
      <DocumentArrowDownIcon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">Backup & Restore</h3>
      <p className="mt-1 text-sm text-gray-500">Backup and restore features coming soon</p>
    </div>
  </div>
);

// Database Optimization Component (placeholder)
const DatabaseOptimization = () => (
  <div className="p-6">
    <div className="text-center">
      <WrenchScrewdriverIcon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">Database Optimization</h3>
      <p className="mt-1 text-sm text-gray-500">Optimization tools coming soon</p>
    </div>
  </div>
);

// System Logs Component (placeholder)
const SystemLogs = () => (
  <div className="p-6">
    <div className="text-center">
      <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">System Logs</h3>
      <p className="mt-1 text-sm text-gray-500">Log viewer coming soon</p>
    </div>
  </div>
);

export default AdminTab;