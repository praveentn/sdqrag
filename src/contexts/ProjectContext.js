// src/contexts/ProjectContext.js
import React, { createContext, useContext } from 'react';

const ProjectContext = createContext();

export const ProjectProvider = ({ children, value }) => {
  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};

export default ProjectContext;