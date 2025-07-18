// src/components/Chat/ChatTab.js
import React, { useState, useEffect, useRef } from 'react';
import {
  PaperAirplaneIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CodeBracketIcon,
  TableCellsIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const ChatTab = () => {
  const { activeProject } = useProject();
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [currentChat, setCurrentChat] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const chatEndRef = useRef(null);
  const queryInputRef = useRef(null);

  useEffect(() => {
    if (activeProject) {
      loadSessions();
    }
  }, [activeProject]);

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, currentChat]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSessions = async () => {
    if (!activeProject) return;

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/sessions`);
      const data = await response.json();

      if (data.status === 'success') {
        setSessions(data.sessions);
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
    }
  };

  const loadChatHistory = async (selectedSessionId) => {
    try {
      const response = await fetch(`/api/chat/${activeProject.id}/sessions/${selectedSessionId}`);
      const data = await response.json();

      if (data.status === 'success') {
        setChatHistory(data.chat_history);
        setSessionId(selectedSessionId);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const handleQuickQuery = async () => {
    if (!query.trim() || !activeProject) return;

    setLoading(true);
    setCurrentChat(null);
    setCurrentStep(null);

    const userMessage = {
      type: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/quick-query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        const assistantMessage = {
          type: 'assistant',
          content: data.final_response,
          sql_query: data.sql_query,
          results: data.results,
          result_count: data.result_count,
          processing_time: data.processing_time,
          timestamp: new Date().toISOString()
        };

        setChatHistory(prev => [...prev, assistantMessage]);
        setQuery('');
        
        // Update session if new
        if (data.session_id && data.session_id !== sessionId) {
          setSessionId(data.session_id);
          loadSessions();
        }

        toast.success('Query completed successfully');
      } else {
        const errorMessage = {
          type: 'error',
          content: data.error || 'Query failed',
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, errorMessage]);
        toast.error('Query failed');
      }
    } catch (error) {
      console.error('Error running query:', error);
      const errorMessage = {
        type: 'error',
        content: 'Network error occurred',
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, errorMessage]);
      toast.error('Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleStepByStepQuery = async () => {
    if (!query.trim() || !activeProject) return;

    setLoading(true);
    setCurrentStep('extract_entities');

    const userMessage = {
      type: 'user',
      content: query,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query,
          step: 'extract_entities'
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setCurrentChat(data);
        setCurrentStep(data.step);
        setSessionId(data.session_id);
        setQuery('');
      } else {
        toast.error(data.message || 'Failed to start query processing');
      }
    } catch (error) {
      console.error('Error starting step-by-step query:', error);
      toast.error('Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleStepConfirmation = async (step, confirmationData) => {
    if (!activeProject || !sessionId) return;

    setLoading(true);

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentChat?.query || '',
          session_id: sessionId,
          step,
          confirmation_data: confirmationData
        }),
      });

      const data = await response.json();

      if (data.status === 'success') {
        setCurrentChat(data);
        setCurrentStep(data.step);

        if (data.step === 'completed') {
          const assistantMessage = {
            type: 'assistant',
            content: data.final_response,
            sql_query: data.sql_query,
            results: data.results,
            result_count: data.result_count,
            timestamp: new Date().toISOString()
          };

          setChatHistory(prev => [...prev, assistantMessage]);
          setCurrentChat(null);
          setCurrentStep(null);
          loadSessions();
        }
      } else {
        toast.error(data.message || 'Step processing failed');
      }
    } catch (error) {
      console.error('Error processing step:', error);
      toast.error('Network error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuickQuery();
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  if (!activeProject) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No Project Selected</h3>
          <p className="mt-1 text-sm text-gray-500">
            Please select a project to start querying your data.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Sidebar - Chat Sessions */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Chat Sessions</h3>
          <p className="text-sm text-gray-500 mt-1">
            {sessions.length} previous conversations
          </p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <p className="text-sm">No previous sessions</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => loadChatHistory(session.session_id)}
                  className={`w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors ${
                    session.session_id === sessionId ? 'bg-blue-50 border border-blue-200' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {session.first_query}
                      </p>
                      <div className="flex items-center mt-1 text-xs text-gray-500">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        {new Date(session.last_activity).toLocaleDateString()}
                      </div>
                    </div>
                    <span className="text-xs text-gray-400 ml-2">
                      {session.query_count}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Natural Language Chat
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Ask questions about your data in plain English
              </p>
            </div>

            {sessionId && (
              <div className="text-sm text-gray-500">
                Session: {sessionId.slice(0, 8)}...
              </div>
            )}
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          {chatHistory.length === 0 && !currentChat ? (
            <div className="text-center py-12">
              <SparklesIcon className="mx-auto h-12 w-12 text-blue-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                Start a conversation
              </h3>
              <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
                Ask questions about your data, and I'll help you find the answers using natural language processing.
              </p>
              
              <div className="mt-6 space-y-2">
                <p className="text-sm font-medium text-gray-700">Try asking:</p>
                <div className="space-y-1 text-sm text-gray-600">
                  <p>"Show me all customers from last month"</p>
                  <p>"What are the top 10 products by sales?"</p>
                  <p>"How many orders were placed this year?"</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Chat History */}
              {chatHistory.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}

              {/* Current Step-by-Step Processing */}
              {currentChat && (
                <StepByStepInterface
                  chat={currentChat}
                  step={currentStep}
                  onConfirm={handleStepConfirmation}
                  loading={loading}
                />
              )}

              {/* Loading Indicator */}
              {loading && !currentChat && (
                <div className="flex items-center space-x-2 text-gray-500">
                  <LoadingSpinner size="small" />
                  <span className="text-sm">Processing your query...</span>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex items-end space-x-3">
            <div className="flex-1">
              <textarea
                ref={queryInputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about your data..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={2}
                disabled={loading}
              />
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={handleQuickQuery}
                disabled={!query.trim() || loading}
                className="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Quick Query"
              >
                <PaperAirplaneIcon className="h-5 w-5" />
              </button>
              
              <button
                onClick={handleStepByStepQuery}
                disabled={!query.trim() || loading}
                className="p-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title="Step-by-Step Query"
              >
                <SparklesIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <div className="flex space-x-4">
              <span>Quick: Fast processing</span>
              <span>Step-by-step: Guided with confirmations</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Chat Message Component
const ChatMessage = ({ message }) => {
  const isUser = message.type === 'user';
  const isError = message.type === 'error';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-3xl ${isUser ? 'ml-12' : 'mr-12'}`}>
        <div
          className={`p-4 rounded-lg ${
            isUser
              ? 'bg-blue-600 text-white'
              : isError
              ? 'bg-red-50 border border-red-200 text-red-800'
              : 'bg-gray-100 text-gray-900'
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
          
          {/* SQL Query Display */}
          {message.sql_query && (
            <div className="mt-3 p-3 bg-gray-900 text-gray-100 rounded text-sm font-mono overflow-x-auto">
              <div className="flex items-center mb-2">
                <CodeBracketIcon className="h-4 w-4 mr-2" />
                <span className="font-medium">Generated SQL:</span>
              </div>
              <pre>{message.sql_query}</pre>
            </div>
          )}
          
          {/* Results Summary */}
          {message.results && (
            <div className="mt-3 p-3 bg-white bg-opacity-20 rounded">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center">
                  <TableCellsIcon className="h-4 w-4 mr-2" />
                  <span>{message.result_count} results found</span>
                </div>
                {message.processing_time && (
                  <span>{message.processing_time}s</span>
                )}
              </div>
            </div>
          )}
        </div>
        
        <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
};

// Step-by-Step Interface Component
const StepByStepInterface = ({ chat, step, onConfirm, loading }) => {
  const [selectedEntities, setSelectedEntities] = useState([]);
  const [selectedMappings, setSelectedMappings] = useState([]);

  const handleConfirmEntities = () => {
    onConfirm('confirm_entities', { confirmed_entities: selectedEntities });
  };

  const handleConfirmMappings = () => {
    onConfirm('confirm_mappings', { selected_mappings: selectedMappings });
  };

  const handleGenerateSQL = () => {
    onConfirm('generate_sql', {});
  };

  const handleExecuteSQL = () => {
    onConfirm('execute_sql', {});
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
      <div className="flex items-center mb-4">
        <ArrowPathIcon className="h-5 w-5 text-blue-600 mr-2" />
        <h4 className="font-medium text-blue-900">Step-by-Step Processing</h4>
      </div>

      {step === 'confirm_entities' && (
        <EntityConfirmation
          entities={chat.entities}
          selectedEntities={selectedEntities}
          setSelectedEntities={setSelectedEntities}
          onConfirm={handleConfirmEntities}
          loading={loading}
        />
      )}

      {step === 'confirm_mappings' && (
        <MappingConfirmation
          mappings={chat.mapping_results}
          selectedMappings={selectedMappings}
          setSelectedMappings={setSelectedMappings}
          onConfirm={handleConfirmMappings}
          loading={loading}
        />
      )}

      {step === 'generate_sql' && (
        <SQLGeneration
          onConfirm={handleGenerateSQL}
          loading={loading}
        />
      )}

      {step === 'execute_sql' && (
        <SQLExecution
          sqlQuery={chat.generated_sql}
          onConfirm={handleExecuteSQL}
          loading={loading}
        />
      )}
    </div>
  );
};

// Entity Confirmation Component
const EntityConfirmation = ({ entities, selectedEntities, setSelectedEntities, onConfirm, loading }) => {
  const toggleEntity = (entity) => {
    setSelectedEntities(prev => {
      const exists = prev.find(e => e.text === entity.text);
      if (exists) {
        return prev.filter(e => e.text !== entity.text);
      } else {
        return [...prev, entity];
      }
    });
  };

  return (
    <div>
      <h5 className="font-medium text-gray-900 mb-3">
        Confirm Extracted Entities ({entities.length})
      </h5>
      
      <div className="space-y-2 mb-4">
        {entities.map((entity, index) => (
          <label key={index} className="flex items-center space-x-3 p-2 hover:bg-white rounded">
            <input
              type="checkbox"
              checked={selectedEntities.some(e => e.text === entity.text)}
              onChange={() => toggleEntity(entity)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <span className="font-medium">{entity.text}</span>
              <span className="ml-2 text-sm text-gray-500">({entity.type})</span>
              {entity.confidence && (
                <span className="ml-2 text-xs text-gray-400">
                  {Math.round(entity.confidence * 100)}%
                </span>
              )}
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={onConfirm}
        disabled={selectedEntities.length === 0 || loading}
        className="btn-primary disabled:opacity-50"
      >
        {loading ? 'Processing...' : `Confirm ${selectedEntities.length} Entities`}
      </button>
    </div>
  );
};

// Mapping Confirmation Component
const MappingConfirmation = ({ mappings, selectedMappings, setSelectedMappings, onConfirm, loading }) => {
  const combinedResults = mappings.combined_results || [];

  const toggleMapping = (mapping) => {
    setSelectedMappings(prev => {
      const exists = prev.find(m => 
        m.type === mapping.type && 
        m.id === mapping.id && 
        m.name === mapping.name
      );
      if (exists) {
        return prev.filter(m => !(m.type === mapping.type && m.id === mapping.id));
      } else {
        return [...prev, mapping];
      }
    });
  };

  return (
    <div>
      <h5 className="font-medium text-gray-900 mb-3">
        Confirm Entity Mappings ({combinedResults.length})
      </h5>
      
      <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
        {combinedResults.map((mapping, index) => (
          <label key={index} className="flex items-center space-x-3 p-2 hover:bg-white rounded">
            <input
              type="checkbox"
              checked={selectedMappings.some(m => 
                m.type === mapping.type && m.id === mapping.id
              )}
              onChange={() => toggleMapping(mapping)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <span className="font-medium">
                {mapping.name || mapping.term || mapping.table_name}
              </span>
              <span className="ml-2 text-sm text-gray-500">({mapping.type})</span>
              <span className="ml-2 text-xs text-blue-600">
                {Math.round(mapping.confidence * 100)}%
              </span>
              {mapping.table_name && mapping.column_name && (
                <div className="text-xs text-gray-500">
                  {mapping.table_name}.{mapping.column_name}
                </div>
              )}
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={onConfirm}
        disabled={selectedMappings.length === 0 || loading}
        className="btn-primary disabled:opacity-50"
      >
        {loading ? 'Processing...' : `Confirm ${selectedMappings.length} Mappings`}
      </button>
    </div>
  );
};

// SQL Generation Component
const SQLGeneration = ({ onConfirm, loading }) => (
  <div>
    <h5 className="font-medium text-gray-900 mb-3">Generate SQL Query</h5>
    <p className="text-sm text-gray-600 mb-4">
      Ready to generate SQL query based on confirmed entities and mappings.
    </p>
    <button
      onClick={onConfirm}
      disabled={loading}
      className="btn-primary disabled:opacity-50"
    >
      {loading ? 'Generating...' : 'Generate SQL'}
    </button>
  </div>
);

// SQL Execution Component
const SQLExecution = ({ sqlQuery, onConfirm, loading }) => (
  <div>
    <h5 className="font-medium text-gray-900 mb-3">Execute SQL Query</h5>
    <div className="bg-gray-900 text-gray-100 p-3 rounded text-sm font-mono mb-4 overflow-x-auto">
      <pre>{sqlQuery}</pre>
    </div>
    <button
      onClick={onConfirm}
      disabled={loading}
      className="btn-primary disabled:opacity-50"
    >
      {loading ? 'Executing...' : 'Execute Query'}
    </button>
  </div>
);

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString();
};

export default ChatTab;