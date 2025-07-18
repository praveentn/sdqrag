// src/components/Dictionary/DictionaryTab.js
import React, { useState, useEffect } from 'react';
import {
  PlusIcon,
  BookOpenIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  SparklesIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const CATEGORIES = [
  { id: 'encyclopedia', name: 'Encyclopedia', description: 'General data definitions' },
  { id: 'abbreviation', name: 'Abbreviations', description: 'Short forms and acronyms' },
  { id: 'keyword', name: 'Keywords', description: 'Important business terms' },
  { id: 'domain_term', name: 'Domain Terms', description: 'Domain-specific terminology' }
];

const DictionaryTab = () => {
  const { activeProject } = useProject();
  const [entries, setEntries] = useState([]);
  const [groupedEntries, setGroupedEntries] = useState({});
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [categoryStats, setCategoryStats] = useState({});

  useEffect(() => {
    if (activeProject) {
      loadEntries();
      loadCategoryStats();
    }
  }, [activeProject, searchTerm, selectedCategory, verifiedOnly]);

  const loadEntries = async () => {
    if (!activeProject) return;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (selectedCategory) params.append('category', selectedCategory);
      if (verifiedOnly) params.append('verified_only', 'true');

      const response = await fetch(`/api/dictionary/${activeProject.id}?${params}`);
      const data = await response.json();

      if (data.status === 'success') {
        setEntries(data.entries);
        setGroupedEntries(data.grouped_entries);
      } else {
        toast.error('Failed to load dictionary entries');
      }
    } catch (error) {
      console.error('Error loading entries:', error);
      toast.error('Failed to load dictionary entries');
    } finally {
      setLoading(false);
    }
  };

  const loadCategoryStats = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/dictionary/${activeProject.id}/categories`);
      const data = await response.json();

      if (data.status === 'success') {
        setCategoryStats(data.category_stats);
      }
    } catch (error) {
      console.error('Error loading category stats:', error);
    }
  };

  const handleCreateEntry = () => {
    setEditingEntry(null);
    setShowModal(true);
  };

  const handleEditEntry = (entry) => {
    setEditingEntry(entry);
    setShowModal(true);
  };

  const handleDeleteEntry = async (entryId) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) {
      return;
    }

    try {
      const response = await fetch(`/api/dictionary/entries/${entryId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Entry deleted successfully');
        loadEntries();
        loadCategoryStats();
      } else {
        toast.error('Failed to delete entry');
      }
    } catch (error) {
      console.error('Error deleting entry:', error);
      toast.error('Failed to delete entry');
    }
  };

  const handleEnhanceEntry = async (entryId) => {
    try {
      const response = await fetch(`/api/dictionary/entries/${entryId}/enhance`, {
        method: 'POST',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Entry enhanced successfully');
        loadEntries();
      } else {
        toast.error('Failed to enhance entry');
      }
    } catch (error) {
      console.error('Error enhancing entry:', error);
      toast.error('Failed to enhance entry');
    }
  };

  const handleVerifyEntries = async (entryIds, verified = true) => {
    try {
      const response = await fetch(`/api/dictionary/${activeProject.id}/bulk-verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          entry_ids: entryIds,
          verified: verified
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success(`${data.updated_count} entries updated`);
        loadEntries();
        loadCategoryStats();
      } else {
        toast.error('Failed to update entries');
      }
    } catch (error) {
      console.error('Error updating entries:', error);
      toast.error('Failed to update entries');
    }
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category', selectedCategory);
      if (verifiedOnly) params.append('verified_only', 'true');

      const response = await fetch(`/api/dictionary/${activeProject.id}/export?${params}`);
      const data = await response.json();

      if (data.status === 'success') {
        const blob = new Blob([JSON.stringify(data.export_data, null, 2)], {
          type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dictionary_${activeProject.name}_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('Dictionary exported successfully');
      } else {
        toast.error('Failed to export dictionary');
      }
    } catch (error) {
      console.error('Error exporting dictionary:', error);
      toast.error('Failed to export dictionary');
    }
  };

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Project Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please select a project to manage the data dictionary.
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
            <h2 className="text-lg font-semibold text-gray-900">Data Dictionary</h2>
            <p className="text-sm text-gray-600 mt-1">
              Manage your data encyclopedia and terminology for {activeProject.name}
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={handleExport}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
              Export
            </button>
            
            <button
              onClick={handleCreateEntry}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              New Entry
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search entries..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
          
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={verifiedOnly}
              onChange={(e) => setVerifiedOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">Verified only</span>
          </label>
        </div>
      </div>

      {/* Category Stats */}
      <div className="bg-gray-50 px-6 py-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {CATEGORIES.map((category) => {
            const stats = categoryStats[category.id] || { total: 0, verified: 0 };
            return (
              <div key={category.id} className="bg-white rounded-lg p-4 border border-gray-200">
                <h4 className="font-medium text-gray-900">{category.name}</h4>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-2xl font-bold text-blue-600">{stats.total}</span>
                  <div className="text-xs text-gray-500">
                    {stats.verified} verified
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <LoadingSpinner size="large" text="Loading dictionary entries..." />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-12">
            <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No dictionary entries</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || selectedCategory || verifiedOnly
                ? 'No entries match your current filters.'
                : 'Get started by creating your first dictionary entry.'}
            </p>
            {!searchTerm && !selectedCategory && !verifiedOnly && (
              <div className="mt-6">
                <button
                  onClick={handleCreateEntry}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Entry
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedEntries).map(([category, categoryEntries]) => (
              <CategorySection
                key={category}
                category={category}
                entries={categoryEntries}
                onEdit={handleEditEntry}
                onDelete={handleDeleteEntry}
                onEnhance={handleEnhanceEntry}
                onVerify={handleVerifyEntries}
              />
            ))}
          </div>
        )}
      </div>

      {/* Entry Modal */}
      {showModal && (
        <EntryModal
          entry={editingEntry}
          projectId={activeProject.id}
          onClose={() => setShowModal(false)}
          onSave={() => {
            setShowModal(false);
            loadEntries();
            loadCategoryStats();
          }}
        />
      )}
    </div>
  );
};

// Category Section Component
const CategorySection = ({ category, entries, onEdit, onDelete, onEnhance, onVerify }) => {
  const [selectedEntries, setSelectedEntries] = useState([]);
  const [showAll, setShowAll] = useState(false);

  const categoryInfo = CATEGORIES.find(c => c.id === category) || { name: category, description: '' };
  const displayEntries = showAll ? entries : entries.slice(0, 10);

  const toggleEntrySelection = (entryId) => {
    setSelectedEntries(prev => 
      prev.includes(entryId) 
        ? prev.filter(id => id !== entryId)
        : [...prev, entryId]
    );
  };

  const selectAllEntries = () => {
    setSelectedEntries(entries.map(entry => entry.id));
  };

  const clearSelection = () => {
    setSelectedEntries([]);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{categoryInfo.name}</h3>
            <p className="text-sm text-gray-500">{categoryInfo.description} • {entries.length} entries</p>
          </div>
          
          {selectedEntries.length > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">{selectedEntries.length} selected</span>
              <button
                onClick={() => onVerify(selectedEntries, true)}
                className="text-sm text-green-600 hover:text-green-700"
              >
                Verify
              </button>
              <button
                onClick={() => onVerify(selectedEntries, false)}
                className="text-sm text-red-600 hover:text-red-700"
              >
                Unverify
              </button>
              <button
                onClick={clearSelection}
                className="text-sm text-gray-600 hover:text-gray-700"
              >
                Clear
              </button>
            </div>
          )}
        </div>
        
        {entries.length > 10 && (
          <div className="mt-2 flex items-center justify-between">
            <button
              onClick={selectAllEntries}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Select All
            </button>
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showAll ? 'Show Less' : `Show All (${entries.length})`}
            </button>
          </div>
        )}
      </div>

      <div className="divide-y divide-gray-200">
        {displayEntries.map((entry) => (
          <EntryRow
            key={entry.id}
            entry={entry}
            isSelected={selectedEntries.includes(entry.id)}
            onSelect={() => toggleEntrySelection(entry.id)}
            onEdit={() => onEdit(entry)}
            onDelete={() => onDelete(entry.id)}
            onEnhance={() => onEnhance(entry.id)}
          />
        ))}
      </div>
    </div>
  );
};

// Entry Row Component
const EntryRow = ({ entry, isSelected, onSelect, onEdit, onDelete, onEnhance }) => {
  return (
    <div className={`px-6 py-4 hover:bg-gray-50 ${isSelected ? 'bg-blue-50' : ''}`}>
      <div className="flex items-start space-x-4">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelect}
          className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h4 className="font-medium text-gray-900">{entry.term}</h4>
                {entry.is_verified ? (
                  <CheckCircleIcon className="h-4 w-4 text-green-500" title="Verified" />
                ) : (
                  <XCircleIcon className="h-4 w-4 text-gray-400" title="Not verified" />
                )}
                {entry.confidence_score && (
                  <span className="text-xs text-gray-500">
                    {Math.round(entry.confidence_score * 100)}%
                  </span>
                )}
              </div>
              
              <p className="text-sm text-gray-600 mt-1 line-clamp-2">{entry.definition}</p>
              
              {entry.aliases && entry.aliases.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-gray-500">Aliases: </span>
                  <span className="text-xs text-gray-700">{entry.aliases.join(', ')}</span>
                </div>
              )}
              
              {(entry.source_table || entry.source_column) && (
                <div className="mt-1 text-xs text-gray-500">
                  Source: {entry.source_table}{entry.source_column ? `.${entry.source_column}` : ''}
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-1 ml-4">
              <button
                onClick={onEnhance}
                className="p-1 text-gray-400 hover:text-purple-600 rounded"
                title="Enhance with AI"
              >
                <SparklesIcon className="h-4 w-4" />
              </button>
              <button
                onClick={onEdit}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
                title="Edit Entry"
              >
                <PencilIcon className="h-4 w-4" />
              </button>
              <button
                onClick={onDelete}
                className="p-1 text-gray-400 hover:text-red-600 rounded"
                title="Delete Entry"
              >
                <TrashIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Entry Modal Component
const EntryModal = ({ entry, projectId, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    term: '',
    definition: '',
    category: 'encyclopedia',
    source_table: '',
    source_column: '',
    aliases: [],
    examples: [],
    tags: [],
    is_verified: false
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (entry) {
      setFormData({
        term: entry.term || '',
        definition: entry.definition || '',
        category: entry.category || 'encyclopedia',
        source_table: entry.source_table || '',
        source_column: entry.source_column || '',
        aliases: entry.aliases || [],
        examples: entry.examples || [],
        tags: entry.tags || [],
        is_verified: entry.is_verified || false
      });
    }
  }, [entry]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      const url = entry 
        ? `/api/dictionary/entries/${entry.id}`
        : `/api/dictionary/${projectId}`;
      
      const method = entry ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success(entry ? 'Entry updated successfully' : 'Entry created successfully');
        onSave();
      } else {
        toast.error(data.message || 'Failed to save entry');
      }
    } catch (error) {
      console.error('Error saving entry:', error);
      toast.error('Failed to save entry');
    } finally {
      setSaving(false);
    }
  };

  const handleArrayFieldChange = (field, value) => {
    const array = value.split(',').map(item => item.trim()).filter(item => item);
    setFormData(prev => ({ ...prev, [field]: array }));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />
        
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                {entry ? 'Edit Dictionary Entry' : 'Create Dictionary Entry'}
              </h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Term *</label>
                  <input
                    type="text"
                    required
                    value={formData.term}
                    onChange={(e) => setFormData(prev => ({ ...prev, term: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Category</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {CATEGORIES.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Definition *</label>
                <textarea
                  required
                  rows={4}
                  value={formData.definition}
                  onChange={(e) => setFormData(prev => ({ ...prev, definition: e.target.value }))}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Source Table</label>
                  <input
                    type="text"
                    value={formData.source_table}
                    onChange={(e) => setFormData(prev => ({ ...prev, source_table: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Source Column</label>
                  <input
                    type="text"
                    value={formData.source_column}
                    onChange={(e) => setFormData(prev => ({ ...prev, source_column: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Aliases (comma-separated)
                </label>
                <input
                  type="text"
                  value={formData.aliases.join(', ')}
                  onChange={(e) => handleArrayFieldChange('aliases', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="synonym1, synonym2, abbreviation"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Examples (comma-separated)
                </label>
                <input
                  type="text"
                  value={formData.examples.join(', ')}
                  onChange={(e) => handleArrayFieldChange('examples', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="example1, example2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={formData.tags.join(', ')}
                  onChange={(e) => handleArrayFieldChange('tags', e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="tag1, tag2"
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_verified"
                  checked={formData.is_verified}
                  onChange={(e) => setFormData(prev => ({ ...prev, is_verified: e.target.checked }))}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="is_verified" className="ml-2 text-sm text-gray-700">
                  Mark as verified
                </label>
              </div>
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
                disabled={saving}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : (entry ? 'Update Entry' : 'Create Entry')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default DictionaryTab;