// src/components/Layout/Header.js
import React from 'react';
import { useLocation } from 'react-router-dom';
import {
  Bars3Icon,
  BellIcon,
  UserCircleIcon
} from '@heroicons/react/24/outline';

const pageNames = {
  '/projects': 'Projects',
  '/datasources': 'Data Sources',
  '/dictionary': 'Data Dictionary',
  '/embeddings': 'Embeddings & Indexing',
  '/search': 'Search Testing',
  '/chat': 'Natural Language Chat',
  '/admin': 'Admin Control Panel'
};

const pageDescriptions = {
  '/projects': 'Manage and organize your data analysis projects',
  '/datasources': 'Upload files and configure database connections',
  '/dictionary': 'Build and maintain your data encyclopedia',
  '/embeddings': 'Configure embedding models and create search indexes',
  '/search': 'Test different search methods and compare results',
  '/chat': 'Query your data using natural language',
  '/admin': 'System administration and database management'
};

const Header = ({ onMenuToggle, activeProject }) => {
  const location = useLocation();
  const currentPage = pageNames[location.pathname] || 'QueryForge';
  const currentDescription = pageDescriptions[location.pathname] || '';

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={onMenuToggle}
            className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 lg:hidden"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          
          <div className="ml-4 lg:ml-0">
            <h1 className="text-2xl font-bold text-gray-900">
              {currentPage}
            </h1>
            {currentDescription && (
              <p className="text-sm text-gray-500 mt-1">
                {currentDescription}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Project Badge */}
          {activeProject && (
            <div className="hidden sm:flex items-center space-x-2 bg-blue-50 px-3 py-1 rounded-full">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm font-medium text-blue-700">
                {activeProject.name}
              </span>
            </div>
          )}

          {/* Health Status */}
          <div className="hidden md:flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs text-gray-500">System Healthy</span>
          </div>

          {/* Notifications */}
          <button className="p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100 rounded-full">
            <BellIcon className="h-5 w-5" />
          </button>

          {/* User Menu */}
          <div className="flex items-center space-x-2">
            <button className="p-1 text-gray-400 hover:text-gray-500">
              <UserCircleIcon className="h-8 w-8" />
            </button>
            <div className="hidden sm:block">
              <span className="text-sm font-medium text-gray-700">Admin</span>
              <div className="text-xs text-gray-500">Administrator</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;