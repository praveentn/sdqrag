// src/App.js
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import ProjectsTab from './components/Projects/ProjectsTab';
import DataSourcesTab from './components/DataSources/DataSourcesTab';
import DictionaryTab from './components/Dictionary/DictionaryTab';
import EmbeddingsTab from './components/Embeddings/EmbeddingsTab';
import SearchTab from './components/Search/SearchTab';
import ChatTab from './components/Chat/ChatTab';
import AdminTab from './components/Admin/AdminTab';
import LoadingSpinner from './components/Common/LoadingSpinner';
import { ProjectProvider } from './contexts/ProjectContext';
import './App.css';

function App() {
  const [activeProject, setActiveProject] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/projects/');
      const data = await response.json();
      
      if (data.status === 'success') {
        setProjects(data.projects);
        
        // Set first project as active if none selected
        if (data.projects.length > 0 && !activeProject) {
          setActiveProject(data.projects[0]);
        }
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = (project) => {
    setActiveProject(project);
  };

  const refreshProjects = () => {
    loadProjects();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <ProjectProvider value={{ 
      activeProject, 
      projects, 
      setActiveProject: handleProjectSelect,
      refreshProjects 
    }}>
      <Router>
        <div className="min-h-screen bg-gray-50 flex">
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                theme: {
                  primary: '#4aed88',
                },
              },
            }}
          />
          
          {/* Sidebar */}
          <Sidebar 
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
            activeProject={activeProject}
            projects={projects}
            onProjectSelect={handleProjectSelect}
          />

          {/* Main Content */}
          <div className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${
            sidebarOpen ? 'ml-64' : 'ml-16'
          }`}>
            <Header 
              onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
              activeProject={activeProject}
            />

            <main className="flex-1 overflow-auto bg-gray-50">
              <div className="h-full">
                <Routes>
                  <Route path="/" element={<Navigate to="/projects" replace />} />
                  <Route path="/projects" element={<ProjectsTab />} />
                  <Route path="/datasources" element={<DataSourcesTab />} />
                  <Route path="/dictionary" element={<DictionaryTab />} />
                  <Route path="/embeddings" element={<EmbeddingsTab />} />
                  <Route path="/search" element={<SearchTab />} />
                  <Route path="/chat" element={<ChatTab />} />
                  <Route path="/admin" element={<AdminTab />} />
                </Routes>
              </div>
            </main>
          </div>
        </div>
      </Router>
    </ProjectProvider>
  );
}

export default App;