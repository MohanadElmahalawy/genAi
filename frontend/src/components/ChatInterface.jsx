import { useState, useRef, useEffect } from 'react';
import { Send, Globe, FileText, Code, CheckCircle } from 'lucide-react';

export default function ChatInterface({
  messages,
  onExplore,
  onDesign,
  onGenerate,
  onVerify,
  currentPhase,
  isConnected,
}) {
  const [url, setUrl] = useState('https://example.com');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const phaseConfig = {
    exploration: { icon: Globe, color: 'blue', label: 'Exploring Page' },
    design: { icon: FileText, color: 'purple', label: 'Designing Tests' },
    generation: { icon: Code, color: 'orange', label: 'Generating Code' },
    verification: { icon: CheckCircle, color: 'green', label: 'Verifying Tests' },
  };

  return (
    <div className="bg-white rounded-lg shadow h-[600px] flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">Agent Chat</h2>
        {currentPhase && (
          <div className="mt-2 flex items-center gap-2">
            {(() => {
              const PhaseIcon = phaseConfig[currentPhase]?.icon || Globe;
              const color = phaseConfig[currentPhase]?.color || 'blue';
              return (
                <>
                  <PhaseIcon className={`w-4 h-4 text-${color}-600 animate-pulse`} />
                  <span className={`text-sm text-${color}-600 font-medium`}>
                    {phaseConfig[currentPhase]?.label || currentPhase}
                  </span>
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.sender === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white'
                  : msg.sender === 'error'
                  ? 'bg-red-100 text-red-800'
                  : msg.sender === 'success'
                  ? 'bg-green-100 text-green-800'
                  : msg.sender === 'system'
                  ? 'bg-gray-100 text-gray-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Action Buttons */}
      <div className="px-6 py-4 border-t border-gray-200 space-y-3">
        {/* URL Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter URL to test"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={() => onExplore(url)}
            disabled={!isConnected || !url}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Globe className="w-4 h-4" />
            Explore
          </button>
        </div>

        {/* Phase Buttons */}
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={onDesign}
            disabled={!isConnected}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <FileText className="w-4 h-4" />
            Design
          </button>
          <button
            onClick={onGenerate}
            disabled={!isConnected}
            className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <Code className="w-4 h-4" />
            Generate
          </button>
          <button
            onClick={onVerify}
            disabled={!isConnected}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <CheckCircle className="w-4 h-4" />
            Verify
          </button>
        </div>
      </div>
    </div>
  );
}