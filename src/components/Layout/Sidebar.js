// src/components/Layout/Sidebar.js
import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  FolderIcon,
  DocumentIcon,
  BookOpenIcon,
  CpuChipIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline';
import classNames from 'classnames';

const navigation = [
  { name: 'Projects', href: '/projects', icon: FolderIcon },
  { name: 'Data Sources', href: '/datasources', icon: DocumentIcon },
  { name: 'Dictionary', href: '/dictionary', icon: BookOpenIcon },
  { name: 'Embeddings', href: '/embeddings', icon: CpuChipIcon },
  { name: 'Search', href: '/search', icon: MagnifyingGlassIcon },
  { name: 'Chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'Admin', href: '/admin', icon: Cog6ToothIcon },
];

const Sidebar = ({ isOpen, onToggle, activeProject, projects, onProjectSelect }) => {
  const location = useLocation();

  return (
    <div className={classNames(
      'fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-gray-200 transition-all duration-300',
      isOpen ? 'w-64' : 'w-16'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        {isOpen && (
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">QF</span>
              </div>
            </div>
            <div className="ml-3">
              <h1 className="text-lg font-semibold text-gray-900">QueryForge</h1>
            </div>
          </div>
        )}
        
        <button
          onClick={onToggle}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
        >
          {isOpen ? (
            <ChevronLeftIcon className="h-5 w-5" />
          ) : (
            <ChevronRightIcon className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* Project Selector */}
      {isOpen && (
        <div className="px-4 py-3 border-b border-gray-200">
          <label className="block text-xs font-medium text-gray-700 mb-2">
            Active Project
          </label>
          <select
            value={activeProject?.id || ''}
            onChange={(e) => {
              const project = projects.find(p => p.id === parseInt(e.target.value));
              if (project) onProjectSelect(project);
            }}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select Project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          
          {activeProject && (
            <div className="mt-2 text-xs text-gray-500">
              {activeProject.data_sources_count} sources • {activeProject.tables_count} tables
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={classNames(
                'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              )}
              title={!isOpen ? item.name : undefined}
            >
              <item.icon
                className={classNames(
                  'flex-shrink-0 h-5 w-5',
                  isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                )}
              />
              {isOpen && (
                <span className="ml-3">{item.name}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      {isOpen && (
        <div className="px-4 py-3 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <div>Version 1.0.0</div>
            <div className="mt-1">Enterprise RAG Platform</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;