// src/components/Chat/ChatTab.js
import React, { useState, useEffect } from 'react';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlayIcon,
  PlusIcon,
  TrashIcon,
  DocumentTextIcon,
  TableCellsIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import { useProject } from '../../contexts/ProjectContext';
import toast from 'react-hot-toast';
import LoadingSpinner from '../Common/LoadingSpinner';

const ChatTab = () => {
  const { activeProject } = useProject();
  const [query, setQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentChat, setCurrentChat] = useState(null);
  const [currentStep, setCurrentStep] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [llmAvailable, setLlmAvailable] = useState(false);

  useEffect(() => {
    if (activeProject) {
      loadSessions();
      checkLlmAvailability();
    }
  }, [activeProject]);

  useEffect(() => {
    if (selectedSession) {
      loadChatHistory(selectedSession);
    }
  }, [selectedSession]);

  const checkLlmAvailability = async () => {
    try {
      const response = await fetch(`/api/chat/${activeProject.id}/llm-status`);
      const data = await response.json();
      setLlmAvailable(data.available);
      
      if (!data.available) {
        toast.error('LLM service not available. Please configure Azure OpenAI settings.');
      }
    } catch (error) {
      console.error('Error checking LLM availability:', error);
      setLlmAvailable(false);
    }
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

  const loadChatHistory = async (sessionId) => {
    if (!activeProject || !sessionId) return;

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/sessions/${sessionId}`);
      const data = await response.json();

      if (data.status === 'success') {
        // Convert backend chat history to frontend format
        const formattedHistory = data.chat_history.map(chat => ({
          type: 'assistant',
          content: chat.final_response || 'Processing...',
          sql_query: chat.generated_sql,
          results: chat.sql_results,
          processing_time: chat.processing_time,
          timestamp: chat.created_at,
          status: chat.status,
          userQuery: chat.user_query
        }));

        setChatHistory(formattedHistory);
        setSessionId(sessionId);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const createNewSession = () => {
    setSelectedSession(null);
    setSessionId(null);
    setChatHistory([]);
    setCurrentChat(null);
    setCurrentStep(null);
  };

  const deleteSession = async (sessionId) => {
    if (!window.confirm('Are you sure you want to delete this chat session?')) return;

    try {
      const response = await fetch(`/api/chat/${activeProject.id}/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.status === 'success') {
        toast.success('Session deleted');
        loadSessions();
        if (selectedSession === sessionId) {
          createNewSession();
        }
      } else {
        toast.error('Failed to delete session');
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      toast.error('Failed to delete session');
    }
  };

  const handleQuickQuery = async () => {
    if (!query.trim() || !activeProject) return;

    if (!llmAvailable) {
      toast.error('LLM service not available. Please configure Azure OpenAI settings.');
      return;
    }

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
        toast.error(data.error || 'Query failed');
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

    if (!llmAvailable) {
      toast.error('LLM service not available. Please configure Azure OpenAI settings.');
      return;
    }

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
    if (!timestamp) return '';
    
    try {
      // Handle both ISO strings and date objects
      const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return 'Invalid time';
      }
      
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
      });
    } catch (error) {
      console.error('Error formatting timestamp:', error);
      return 'Invalid time';
    }
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '';
    
    try {
      const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
      
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      
      return date.toLocaleDateString();
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid date';
    }
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
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Chat Sessions</h3>
            <button
              onClick={createNewSession}
              className="p-2 text-gray-400 hover:text-gray-600 rounded"
              title="New Session"
            >
              <PlusIcon className="h-5 w-5" />
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {sessions.length} previous conversations
          </p>
          
          {/* LLM Status Indicator */}
          <div className={`mt-2 flex items-center text-sm ${llmAvailable ? 'text-green-600' : 'text-red-600'}`}>
            <div className={`w-2 h-2 rounded-full mr-2 ${llmAvailable ? 'bg-green-500' : 'bg-red-500'}`}></div>
            {llmAvailable ? 'LLM Available' : 'LLM Unavailable'}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="mx-auto h-8 w-8 mb-2" />
              <p className="text-sm">No chat sessions yet</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedSession === session.session_id
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedSession(session.session_id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {session.first_query || 'Untitled Chat'}
                      </p>
                      <div className="flex items-center text-xs text-gray-500 mt-1">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        {formatDate(session.last_activity)}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {session.query_count} queries
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(session.session_id);
                      }}
                      className="p-1 text-gray-400 hover:text-red-600 rounded"
                      title="Delete Session"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat History */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {chatHistory.length === 0 ? (
            <div className="text-center py-12">
              <ChatBubbleLeftRightIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                {selectedSession ? 'Chat History' : 'Start a Conversation'}
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                {selectedSession 
                  ? 'Loading chat history...' 
                  : 'Ask questions about your data using natural language'}
              </p>
            </div>
          ) : (
            chatHistory.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))
          )}

          {/* Step-by-step workflow */}
          {currentChat && currentStep && (
            <StepByStepWorkflow
              chat={currentChat}
              step={currentStep}
              onConfirm={handleStepConfirmation}
              loading={loading}
            />
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="flex space-x-4">
            <div className="flex-1">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={llmAvailable ? "Ask a question about your data..." : "LLM service unavailable - please configure Azure OpenAI"}
                disabled={loading || !llmAvailable}
                className="w-full resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                rows={2}
              />
            </div>
            <div className="flex flex-col space-y-2">
              <button
                onClick={handleQuickQuery}
                disabled={loading || !query.trim() || !llmAvailable}
                className="btn-primary disabled:opacity-50 flex items-center"
                title="Quick Query"
              >
                {loading ? (
                  <ArrowPathIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <PaperAirplaneIcon className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={handleStepByStepQuery}
                disabled={loading || !query.trim() || !llmAvailable}
                className="btn-secondary disabled:opacity-50 flex items-center"
                title="Step-by-step Query"
              >
                <PlayIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
          
          {!llmAvailable && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
              ⚠️ LLM service unavailable. Please configure Azure OpenAI in your environment variables.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Chat Message Component
const ChatMessage = ({ message }) => {
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    
    try {
      const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
      if (isNaN(date.getTime())) return 'Invalid time';
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch (error) {
      return 'Invalid time';
    }
  };

  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-2xl">
          <p>{message.content}</p>
          <p className="text-xs text-blue-100 mt-1">{formatTimestamp(message.timestamp)}</p>
        </div>
      </div>
    );
  }

  if (message.type === 'error') {
    return (
      <div className="flex">
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 max-w-2xl">
          <div className="flex items-center text-red-800">
            <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
            <p className="font-medium">Error</p>
          </div>
          <p className="text-red-700 mt-1">{message.content}</p>
          <p className="text-xs text-red-500 mt-1">{formatTimestamp(message.timestamp)}</p>
        </div>
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex">
      <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-4xl">
        {message.userQuery && (
          <div className="text-sm text-gray-600 mb-2 font-medium">
            Query: {message.userQuery}
          </div>
        )}
        
        <div className="prose max-w-none">
          <p className="text-gray-900">{message.content}</p>
        </div>

        {message.sql_query && (
          <div className="mt-3 bg-gray-800 text-gray-100 rounded p-3">
            <div className="flex items-center mb-2">
              <DocumentTextIcon className="h-4 w-4 mr-2" />
              <span className="font-medium text-sm">Generated SQL</span>
            </div>
            <pre className="text-sm overflow-x-auto">{message.sql_query}</pre>
          </div>
        )}

        {message.results && message.results.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center mb-2">
              <TableCellsIcon className="h-4 w-4 mr-2" />
              <span className="font-medium text-sm">Results ({message.result_count || message.results.length})</span>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(message.results[0]).map((key) => (
                      <th key={key} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {message.results.slice(0, 10).map((row, idx) => (
                    <tr key={idx}>
                      {Object.values(row).map((value, valueIdx) => (
                        <td key={valueIdx} className="px-3 py-2 whitespace-nowrap text-gray-900">
                          {value !== null ? String(value) : 'NULL'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {message.results.length > 10 && (
                <p className="text-xs text-gray-500 mt-2">
                  ... and {message.results.length - 10} more rows
                </p>
              )}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
          <span>{formatTimestamp(message.timestamp)}</span>
          {message.processing_time && (
            <span>Processing: {message.processing_time}s</span>
          )}
        </div>
      </div>
    </div>
  );
};

// Step-by-step Workflow Component
const StepByStepWorkflow = ({ chat, step, onConfirm, loading }) => {
  const getStepIcon = (stepName) => {
    switch (stepName) {
      case 'confirm_entities':
        return <CpuChipIcon className="h-5 w-5" />;
      case 'confirm_mappings':
        return <TableCellsIcon className="h-5 w-5" />;
      case 'execute_sql':
        return <PlayIcon className="h-5 w-5" />;
      default:
        return <CheckCircleIcon className="h-5 w-5" />;
    }
  };

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center mb-3">
        {getStepIcon(step)}
        <h4 className="ml-2 font-medium text-blue-900">
          {step === 'confirm_entities' && 'Confirm Extracted Entities'}
          {step === 'confirm_mappings' && 'Confirm Entity Mappings'}
          {step === 'execute_sql' && 'Execute Generated SQL'}
        </h4>
      </div>

      {step === 'confirm_entities' && chat.entities && (
        <div className="space-y-3">
          <p className="text-sm text-blue-800">
            I found these entities in your query. Please confirm:
          </p>
          <div className="flex flex-wrap gap-2">
            {chat.entities.map((entity, idx) => (
              <span key={idx} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                {entity.text} ({entity.type})
              </span>
            ))}
          </div>
          <button
            onClick={() => onConfirm('confirm_entities', { confirmed_entities: chat.entities })}
            disabled={loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? 'Processing...' : 'Confirm Entities'}
          </button>
        </div>
      )}

      {step === 'confirm_mappings' && chat.mapping_results && (
        <div className="space-y-3">
          <p className="text-sm text-blue-800">
            Found these potential mappings. Please confirm:
          </p>
          <div className="max-h-40 overflow-y-auto space-y-2">
            {chat.mapping_results.combined_results?.slice(0, 5).map((mapping, idx) => (
              <div key={idx} className="bg-white p-2 rounded border">
                <span className="font-medium">{mapping.name || mapping.term}</span>
                <span className="text-sm text-gray-600 ml-2">({mapping.type})</span>
              </div>
            ))}
          </div>
          <button
            onClick={() => onConfirm('confirm_mappings', { confirmed_mappings: chat.mapping_results.combined_results?.slice(0, 5) })}
            disabled={loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? 'Processing...' : 'Confirm Mappings'}
          </button>
        </div>
      )}

      {step === 'execute_sql' && chat.generated_sql && (
        <div className="space-y-3">
          <p className="text-sm text-blue-800">
            Generated SQL query. Execute to get results:
          </p>
          <div className="bg-gray-800 text-gray-100 rounded p-3">
            <pre className="text-sm overflow-x-auto">{chat.generated_sql}</pre>
          </div>
          <button
            onClick={() => onConfirm('execute_sql', { execute: true })}
            disabled={loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? 'Executing...' : 'Execute SQL'}
          </button>
        </div>
      )}
    </div>
  );
};

export default ChatTab;