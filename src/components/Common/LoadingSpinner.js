// src/components/Common/LoadingSpinner.js
import React from 'react';
import classNames from 'classnames';

const LoadingSpinner = ({ size = 'medium', className = '', text = '' }) => {
  const sizeClasses = {
    small: 'h-4 w-4',
    medium: 'h-8 w-8',
    large: 'h-12 w-12'
  };

  const textSizeClasses = {
    small: 'text-sm',
    medium: 'text-base',
    large: 'text-lg'
  };

  return (
    <div className={classNames('flex flex-col items-center justify-center', className)}>
      <div
        className={classNames(
          'animate-spin rounded-full border-2 border-gray-300 border-t-blue-600',
          sizeClasses[size]
        )}
      />
      {text && (
        <div className={classNames('mt-2 text-gray-600', textSizeClasses[size])}>
          {text}
        </div>
      )}
    </div>
  );
};

export default LoadingSpinner;