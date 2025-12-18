import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Clock, Zap, Activity } from 'lucide-react';

export default function MetricsDashboard({ metrics, currentPhase }) {
  if (!metrics) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Agent Metrics
        </h3>
        <p className="text-gray-500 text-sm">
          Metrics will appear after exploration starts
        </p>
      </div>
    );
  }

  const chartData = [
    {
      name: 'Response Time',
      value: metrics.avg_response_time || 0,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Metrics Card */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Agent Metrics
        </h3>

        <div className="space-y-4">
          {/* Current Phase */}
          {currentPhase && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-sm text-gray-600">Current Phase</div>
              <div className="text-xl font-bold text-blue-600 capitalize">
                {currentPhase}
              </div>
            </div>
          )}

          {/* Response Time */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Avg Response Time
              </span>
            </div>
            <span className="text-lg font-bold text-gray-900">
              {metrics.avg_response_time?.toFixed(2) || 0}s
            </span>
          </div>

          {/* Tokens */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-600" />
              <span className="text-sm font-medium text-gray-700">
                Total Tokens
              </span>
            </div>
            <span className="text-lg font-bold text-gray-900">
              {metrics.total_tokens?.toLocaleString() || 0}
            </span>
          </div>

          {/* Iterations */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-sm font-medium text-gray-700">Iterations</span>
            <span className="text-lg font-bold text-gray-900">
              {metrics.iterations || 0}
            </span>
          </div>

          {/* Total Time */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="text-sm font-medium text-gray-700">Total Time</span>
            <span className="text-lg font-bold text-gray-900">
              {metrics.total_time?.toFixed(2) || 0}s
            </span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Performance</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="font-medium text-blue-900 mb-2">Agent Brain</h4>
        <p className="text-sm text-blue-700">
          Real-time metrics showing the agent's thinking process, resource usage,
          and performance across all testing phases.
        </p>
      </div>
    </div>
  );
}