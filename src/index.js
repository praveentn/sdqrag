// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import './App.css';
import App from './App';

// Performance monitoring
if (process.env.NODE_ENV === 'development') {
  console.log('QueryForge - Development Mode');
}

// Create React root
const root = ReactDOM.createRoot(document.getElementById('root'));

// Render the app
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Performance measurement
if ('performance' in window) {
  window.addEventListener('load', () => {
    const navigation = performance.getEntriesByType('navigation')[0];
    if (navigation) {
      console.log('QueryForge Performance Metrics:', {
        'DNS Lookup': navigation.domainLookupEnd - navigation.domainLookupStart,
        'TCP Connection': navigation.connectEnd - navigation.connectStart,
        'Request/Response': navigation.responseEnd - navigation.requestStart,
        'DOM Processing': navigation.domComplete - navigation.responseEnd,
        'Total Load Time': navigation.loadEventEnd - navigation.navigationStart
      });
    }
  });
}

// Service Worker registration for PWA features (future)
if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered: ', registration);
      })
      .catch((registrationError) => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}

// Error boundary for development
if (process.env.NODE_ENV === 'development') {
  window.addEventListener('error', (event) => {
    console.error('Global error caught:', event.error);
  });

  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
  });
}