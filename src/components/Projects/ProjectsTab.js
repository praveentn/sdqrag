// src/components/Projects/ProjectsTab.js
import React, { useState, useEffect } from 'react';
import { 
  PlusIcon, 
  FolderIcon, 
  DocumentIcon, 
  TableCellsIcon,
  BookOpenIcon,
  MagnifyingGlassIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';
import ProjectModal from './ProjectModal';
import ProjectCard from './ProjectCard';

const ProjectsTab = () => {
  const { projects, activeProject, setActiveProject, refreshProjects } = useProject();
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [projectStats, setProjectStats] = useState({});

  useEffect(() => {
    loadProjectStats();
  }, [projects]);

  const loadProjectStats = async () => {
    try {
      const stats = {};
      for (const project of projects) {
        const response = await fetch(`/api/projects/${project.id}/summary`);
        const data = await response.json();
        if (data.status === 'success') {
          stats[project.id] = data.summary;
        }
      }
      setProjectStats(stats);
    } catch (error) {
      console.error('Error loading project stats:', error);
    }
  };

  const handleCreateProject = () => {
    setEditingProject(null);
    setShowModal(true);
  };

  const handleEditProject = (project) => {
    setEditingProject(project);
    setShowModal(true);
  };

  const handleDeleteProject = async (project) => {
    if (!window.confirm(`Are you sure you want to delete "${project.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/projects/${project.id}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Project deleted successfully');
        refreshProjects();
        
        // If deleted project was active, clear selection
        if (activeProject?.id === project.id) {
          setActiveProject(null);
        }
      } else {
        toast.error(data.message || 'Failed to delete project');
      }
    } catch (error) {
      console.error('Error deleting project:', error);
      toast.error('Failed to delete project');
    }
  };

  const handleProjectSave = async (projectData) => {
    try {
      const isEditing = editingProject !== null;
      const url = isEditing 
        ? `/api/projects/${editingProject.id}` 
        : '/api/projects/';
      
      const method = isEditing ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(projectData),
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success(isEditing ? 'Project updated successfully' : 'Project created successfully');
        setShowModal(false);
        refreshProjects();
        
        // Set as active project if creating new
        if (!isEditing) {
          setActiveProject(data.project);
        }
      } else {
        toast.error(data.message || 'Failed to save project');
      }
    } catch (error) {
      console.error('Error saving project:', error);
      toast.error('Failed to save project');
    }
  };

  const handleSetActiveProject = (project) => {
    setActiveProject(project);
    toast.success(`Switched to project: ${project.name}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="large" text="Loading projects..." />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Project Management</h2>
            <p className="text-sm text-gray-600 mt-1">
              Create and manage your data analysis projects
            </p>
          </div>
          
          <button
            onClick={handleCreateProject}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon className="h-4 w-4 mr-2" />
            New Project
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {projects.length === 0 ? (
          <div className="text-center py-12">
            <FolderIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No projects</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new project.
            </p>
            <div className="mt-6">
              <button
                onClick={handleCreateProject}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <PlusIcon className="h-4 w-4 mr-2" />
                New Project
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                stats={projectStats[project.id]}
                isActive={activeProject?.id === project.id}
                onSelect={() => handleSetActiveProject(project)}
                onEdit={() => handleEditProject(project)}
                onDelete={() => handleDeleteProject(project)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Project Modal */}
      {showModal && (
        <ProjectModal
          project={editingProject}
          onSave={handleProjectSave}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
};

export default ProjectsTab;