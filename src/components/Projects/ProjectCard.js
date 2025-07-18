// src/components/Projects/ProjectCard.js
import React from 'react';
import { 
  DocumentIcon, 
  TableCellsIcon,
  BookOpenIcon,
  CpuChipIcon,
  ChatBubbleLeftRightIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import classNames from 'classnames';

const ProjectCard = ({ project, stats, isActive, onSelect, onEdit, onDelete }) => {
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return 'Unknown';
    }
  };

  const getStatusColor = () => {
    if (!stats) return 'gray';
    
    const hasData = stats.data_sources?.total > 0;
    const hasEmbeddings = stats.embeddings?.ready_count > 0;
    
    if (hasData && hasEmbeddings) return 'green';
    if (hasData) return 'yellow';
    return 'gray';
  };

  const statusColor = getStatusColor();
  const statusColors = {
    green: 'bg-green-100 text-green-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    gray: 'bg-gray-100 text-gray-800'
  };

  const statusLabels = {
    green: 'Ready',
    yellow: 'Setup Required',
    gray: 'New'
  };

  return (
    <div
      className={classNames(
        'relative group bg-white rounded-lg border-2 p-6 hover:shadow-lg transition-all duration-200 cursor-pointer',
        isActive 
          ? 'border-blue-500 shadow-lg ring-2 ring-blue-200' 
          : 'border-gray-200 hover:border-gray-300'
      )}
      onClick={onSelect}
    >
      {/* Active Badge */}
      {isActive && (
        <div className="absolute -top-2 -right-2">
          <div className="bg-blue-500 text-white rounded-full p-1">
            <CheckCircleIcon className="h-4 w-4" />
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-gray-900 group-hover:text-blue-600">
            {project.name}
          </h3>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
            {project.description || 'No description provided'}
          </p>
        </div>
        
        <div className="flex items-center space-x-1 ml-4">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1 text-gray-400 hover:text-gray-600 rounded"
            title="Edit Project"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 text-gray-400 hover:text-red-600 rounded"
            title="Delete Project"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Status Badge */}
      <div className="mt-4">
        <span className={classNames(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          statusColors[statusColor]
        )}>
          {statusLabels[statusColor]}
        </span>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="flex items-center space-x-2">
            <DocumentIcon className="h-4 w-4 text-gray-400" />
            <div>
              <div className="text-sm font-medium text-gray-900">
                {stats.data_sources?.total || 0}
              </div>
              <div className="text-xs text-gray-500">Sources</div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <TableCellsIcon className="h-4 w-4 text-gray-400" />
            <div>
              <div className="text-sm font-medium text-gray-900">
                {stats.tables?.total || 0}
              </div>
              <div className="text-xs text-gray-500">Tables</div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <BookOpenIcon className="h-4 w-4 text-gray-400" />
            <div>
              <div className="text-sm font-medium text-gray-900">
                {stats.dictionary?.total || 0}
              </div>
              <div className="text-xs text-gray-500">Dictionary</div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <CpuChipIcon className="h-4 w-4 text-gray-400" />
            <div>
              <div className="text-sm font-medium text-gray-900">
                {stats.embeddings?.indexes_count || 0}
              </div>
              <div className="text-xs text-gray-500">Indexes</div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Created {formatDate(project.created_at)}</span>
          {stats?.chat?.total_queries > 0 && (
            <div className="flex items-center space-x-1">
              <ChatBubbleLeftRightIcon className="h-3 w-3" />
              <span>{stats.chat.total_queries} queries</span>
            </div>
          )}
        </div>
      </div>

      {/* Hover Overlay */}
      <div className="absolute inset-0 bg-blue-50 opacity-0 group-hover:opacity-10 rounded-lg transition-opacity duration-200 pointer-events-none" />
    </div>
  );
};

export default ProjectCard;