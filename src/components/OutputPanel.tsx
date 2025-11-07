import { AlertCircle, CheckCircle, Code, AlertTriangle } from 'lucide-react';

interface Token {
  type: string;
  value: string;
  line: number;
}

interface Error {
  type: string;
  message: string;
  line?: number;
}

interface CompileResult {
  status: string;
  tokens?: Token[];
  errors?: Error[];
  message?: string;
}

interface OutputPanelProps {
  result: CompileResult | null;
  error: string | null;
  isCompiling: boolean;
  fixes?: any[] | null;
  onApplyFix?: (fix: any) => void;
}

function OutputPanel({ result, error, isCompiling, fixes, onApplyFix }: OutputPanelProps) {
  // sanitize any backend message to remove development words like 'mock'
  const displayMessage = result?.message
    ? (result.message as string).replace(/mock/ig, '').replace(/\s+/g, ' ').trim()
    : result?.status === 'success' ? 'Compilation successful' : 'Compilation failed';
  if (isCompiling) {
    return (
      <div className="bg-white rounded-lg border border-blue-200 shadow-sm p-8 h-[500px] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
          <p className="text-gray-600">Analyzing code...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border border-red-200 shadow-sm p-6 h-[500px]">
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900 mb-1">Connection Error</h3>
            <p className="text-sm text-red-700">{error}</p>
            <p className="text-xs text-red-600 mt-2">
              Make sure your backend server is running and set the environment variable <code>VITE_BACKEND_URL</code> to its base URL (e.g. http://localhost:8000)
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-white rounded-lg border border-blue-200 shadow-sm p-8 h-[500px] flex items-center justify-center">
        <div className="text-center text-gray-500">
          <Code className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p className="text-lg font-medium">Ready to compile</p>
          <p className="text-sm mt-2">Click the "Compile Code" button to analyze your code</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-blue-200 shadow-sm h-[500px] flex flex-col overflow-hidden">
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 px-4 py-3 border-b border-blue-200">
        <div className="flex items-center gap-2">
          {result.status === 'success' ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-orange-600" />
          )}
          <span className="font-medium text-gray-900">
            {displayMessage}
          </span>
        </div>
      </div>
      
      {result.status === 'error' && result.errors && result.errors.length > 0 && (
        <div className="px-4 py-2 bg-orange-50 border-b border-orange-200">
          <div className="flex items-center gap-2 text-orange-800">
            <AlertTriangle className="w-4 h-4" />
            <span className="text-sm font-medium">Compilation failed</span>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {result.tokens && result.tokens.length > 0 && (
          <div>
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Code className="w-4 h-4 text-primary-600" />
              Tokens Generated
            </h3>
            <div className="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-primary-100 border-b border-primary-200">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-primary-900">Type</th>
                    <th className="text-left px-3 py-2 font-semibold text-primary-900">Value</th>
                    <th className="text-left px-3 py-2 font-semibold text-primary-900">Line</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {result.tokens.map((token, idx) => (
                    <tr key={idx} className="hover:bg-gray-100 transition-colors">
                      <td className="px-3 py-2 font-mono text-primary-700">{token.type}</td>
                      <td className="px-3 py-2 font-mono text-gray-700">{token.value}</td>
                      <td className="px-3 py-2 text-gray-600">{token.line}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {result.errors && result.errors.length > 0 && (
          <div>
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              Errors Detected
            </h3>
            <div className="space-y-2">
              {result.errors.map((err, idx) => (
                <div
                  key={idx}
                  className="bg-red-50 border border-red-200 rounded-lg p-3"
                >
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-red-900 uppercase tracking-wide">
                          {err.type || 'ERROR'}
                        </span>
                        {err.line && (
                          <span className="text-xs text-red-700">(line {err.line})</span>
                        )}
                      </div>
                      <p className="text-sm text-red-800 leading-relaxed">{err.message}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {fixes && fixes.length > 0 && (
              <div className="mt-4">
                <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600" />
                  Suggested Fixes
                </h4>
                <div className="space-y-2">
                  {fixes.map((fix, i) => (
                    <div key={i} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                      <div className="text-sm text-yellow-900 mb-2">{fix.description}</div>
                      <div className="text-xs text-yellow-800 mb-2">Confidence: {Math.round((fix.confidence || 0) * 100)}%</div>
                      <div className="flex justify-end">
                        <button
                          onClick={() => onApplyFix && onApplyFix(fix)}
                          className="px-3 py-1 bg-orange-500 hover:bg-orange-600 text-white rounded text-sm font-medium transition-colors"
                        >
                          Apply
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {result.tokens && result.tokens.length === 0 && result.errors && result.errors.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <p>No output generated</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default OutputPanel;
