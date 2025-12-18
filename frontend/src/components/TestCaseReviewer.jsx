import { CheckCircle, AlertCircle, FileText } from 'lucide-react';

export default function TestCaseReviewer({ testCases }) {
  if (!testCases || !testCases.test_cases) {
    return null;
  }

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category?.toLowerCase()) {
      case 'functional':
        return <CheckCircle className="w-4 h-4" />;
      case 'negative':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Test Cases</h3>
        <p className="text-sm text-gray-600 mt-1">
          Review and approve the proposed test cases
        </p>
      </div>

      <div className="p-6 space-y-4">
        {testCases.test_cases.map((testCase, idx) => (
          <div
            key={idx}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                {getCategoryIcon(testCase.category)}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-500">
                      {testCase.id}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-xs rounded border ${getPriorityColor(
                        testCase.priority
                      )}`}
                    >
                      {testCase.priority}
                    </span>
                  </div>
                  <h4 className="font-semibold text-gray-900 mt-1">
                    {testCase.name}
                  </h4>
                </div>
              </div>
            </div>

            {/* Steps */}
            {testCase.steps && testCase.steps.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-700">Steps:</div>
                <ol className="space-y-1">
                  {testCase.steps.map((step, stepIdx) => (
                    <li key={stepIdx} className="flex gap-2 text-sm">
                      <span className="text-gray-400 font-mono">
                        {stepIdx + 1}.
                      </span>
                      <div className="flex-1">
                        <div className="text-gray-700">{step.action}</div>
                        {step.expected && (
                          <div className="text-gray-500 text-xs mt-1">
                            Expected: {step.expected}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Category Badge */}
            {testCase.category && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <span className="text-xs text-gray-600">
                  Category: <span className="font-medium">{testCase.category}</span>
                </span>
              </div>
            )}
          </div>
        ))}

        {/* Coverage Summary */}
        {testCases.coverage && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="font-medium text-blue-900 mb-2">Coverage Summary</h4>
            <div className="space-y-1 text-sm text-blue-800">
              {testCases.coverage.elements_covered && (
                <div>
                  Elements Covered: <span className="font-bold">
                    {testCases.coverage.elements_covered}
                  </span>
                </div>
              )}
              {testCases.coverage.interaction_types && (
                <div>
                  Interaction Types:{' '}
                  {Array.isArray(testCases.coverage.interaction_types)
                    ? testCases.coverage.interaction_types.join(', ')
                    : testCases.coverage.interaction_types}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}