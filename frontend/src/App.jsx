import { useState, useEffect, useRef } from 'react';
import ChatInterface from './components/ChatInterface';
import MetricsDashboard from './components/MetricsDashboard';
import TestCaseReviewer from './components/TestCaseReviewer';
import { Activity, RotateCcw } from 'lucide-react';

function App() {
  const [messages, setMessages] = useState([]);
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentPhase, setCurrentPhase] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [testCases, setTestCases] = useState(null);
  const [generatedCode, setGeneratedCode] = useState(null);
  const [verificationResults, setVerificationResults] = useState(null);

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket('ws://localhost:8000/ws');

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      addMessage('system', 'Connected to Testing Agent');
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      addMessage('system', 'Disconnected from server');
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      addMessage('error', 'Connection error occurred');
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  const handleWebSocketMessage = (data) => {
    console.log('Received:', data);

    switch (data.type) {
      case 'phase_start':
        setCurrentPhase(data.phase);
        addMessage('agent', data.message);
        break;

      case 'progress':
        addMessage('agent', data.message);
        break;

      case 'phase_complete':
        addMessage('success', `${data.phase} phase completed!`);
        setMetrics(data.metrics);

        // Store phase-specific data
        if (data.phase === 'exploration') {
          addMessage('agent', `Found ${data.data.elements.length} testable elements`);
        } else if (data.phase === 'design') {
          setTestCases(data.data);
          addMessage('agent', `Created ${data.data.test_cases.length} test cases`);
        } else if (data.phase === 'design_refinement') {
          setTestCases(data.data);
          addMessage('success', 'Test cases refined successfully');
        } else if (data.phase === 'generation') {
          setGeneratedCode(data.data.code);
          // If backend included verification results with generation, store them
          if (data.data.verification) {
            setVerificationResults(data.data.verification);
            addMessage('success', `Verification: ${data.data.verification.passed} passed, ${data.data.verification.failed} failed`);
          } else {
            addMessage('agent', 'Test code generated successfully');
          }
        } else if (data.phase === 'generation_refinement') {
          setGeneratedCode(data.data.code);
          addMessage('success', 'Generated code refined successfully');
        } else if (data.phase === 'verification') {
          setVerificationResults(data.data);
          addMessage('success', `Tests: ${data.data.passed} passed, ${data.data.failed} failed`);
        }
        break;

      case 'error':
        addMessage('error', `Error: ${data.message}`);
        break;

      case 'info':
        addMessage('agent', data.message);
        break;

      case 'chat_response':
        addMessage('agent', data.message);
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  };

  const addMessage = (sender, text) => {
    setMessages((prev) => [...prev, { sender, text, timestamp: Date.now() }]);
  };

  const sendCommand = (command, payload = {}) => {
    if (ws && isConnected) {
      ws.send(JSON.stringify({ command, payload }));
      return true;
    }
    return false;
  };

  const handleExplore = (url) => {
    addMessage('user', `Explore: ${url}`);
    sendCommand('explore', { url });
  };

  const handleDesign = () => {
    addMessage('user', 'Design test cases');
    sendCommand('design');
  };

  const handleGenerate = () => {
    addMessage('user', 'Generate test code');
    sendCommand('generate');
  };

  const handleVerify = () => {
    addMessage('user', 'Verify tests');
    sendCommand('verify');
  };

  const handleReset = () => {
    sendCommand('reset');
    setMessages([]);
    setCurrentPhase(null);
    setMetrics(null);
    setTestCases(null);
    setGeneratedCode(null);
    setVerificationResults(null);
    addMessage('system', 'Agent reset');
  };

  const handleRefine = (feedback) => {
    if (!testCases) {
      addMessage('error', 'No test cases to refine');
      return;
    }

    addMessage('user', `Refine feedback: ${feedback}`);
    sendCommand('refine', { feedback, current_cases: testCases });
  };

  const [codeIssue, setCodeIssue] = useState('');

  const handleRefineCode = () => {
    if (!generatedCode) {
      addMessage('error', 'No generated code to refine');
      return;
    }

    addMessage('user', `Refine code issue: ${codeIssue}`);
    sendCommand('refine_code', { issue: codeIssue, current_code: generatedCode });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">
              Web Testing Agent
            </h1>
            <span
              className={`px-2 py-1 text-xs rounded-full ${
                isConnected
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}
            >
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset Agent
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Chat Interface */}
          <div className="lg:col-span-2">
            <ChatInterface
              messages={messages}
              onExplore={handleExplore}
              onDesign={handleDesign}
              onGenerate={handleGenerate}
              onVerify={handleVerify}
              currentPhase={currentPhase}
              isConnected={isConnected}
            />

            {/* Test Cases Reviewer */}
            {testCases && (
              <div className="mt-6">
                <TestCaseReviewer testCases={testCases} onRefine={handleRefine} />
              </div>
            )}

            {/* Generated Code */}
            {generatedCode && (
              <div className="mt-6 bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Generated Test Code</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-x-auto text-sm max-h-80">
                  <code>{generatedCode}</code>
                </pre>

                <div className="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
                  <h4 className="font-medium mb-2">Report Issue / Request Fix</h4>
                  <textarea
                    value={codeIssue}
                    onChange={(e) => setCodeIssue(e.target.value)}
                    placeholder="Describe the issue or requested change (e.g. failing assertion, selector problem)"
                    className="w-full p-3 border border-gray-300 rounded-md text-sm"
                    rows={3}
                  />
                  <div className="mt-3 flex gap-2 justify-end">
                    <button
                      onClick={() => setCodeIssue('')}
                      className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200"
                    >
                      Clear
                    </button>
                    <button
                      onClick={handleRefineCode}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                    >
                      Refine Code
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Verification Results */}
            {verificationResults && (
              <div className="mt-6 bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Test Results</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Passed:</span>
                    <span className="font-bold text-green-600">
                      {verificationResults.passed}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Failed:</span>
                    <span className="font-bold text-red-600">
                      {verificationResults.failed}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Execution Time:</span>
                    <span>{verificationResults.execution_time.toFixed(2)}s</span>
                  </div>
                </div>
                <pre className="mt-4 bg-gray-100 p-4 rounded text-xs overflow-x-auto max-h-64">
                  {verificationResults.output}
                </pre>
              </div>
            )}
          </div>

          {/* Right Column - Metrics Dashboard */}
          <div className="lg:col-span-1">
            <MetricsDashboard metrics={metrics} currentPhase={currentPhase} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;