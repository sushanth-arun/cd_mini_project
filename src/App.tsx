import { useState } from 'react';
import { Play, FileCode, CheckCircle, AlertCircle, Loader2, RotateCcw } from 'lucide-react';
import CodeEditor from './components/CodeEditor';
import OutputPanel from './components/OutputPanel';

interface CompileResult {
  status: string;
  tokens?: Array<{ type: string; value: string; line: number }>;
  errors?: Array<{ type: string; message: string; line?: number }>;
  message?: string;
}

function App() {
  const defaultCode = `int main() {
    int x = 10;
    printf("Hello, World!");
    return 0;
}`;

  const [code, setCode] = useState(defaultCode);
  const [result, setResult] = useState<CompileResult | null>(null);
  const [fixes, setFixes] = useState<any[] | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const handleCompile = async () => {
    setIsCompiling(true);
    setError(null);
    
    // Use local server - no API key needed, works fully locally with Ollama
    const localServerUrl = 'http://127.0.0.1:8001';

    try {
      const response = await fetch(`${localServerUrl}/compile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Map the response to our expected format
      setResult({
        status: data.status === 'success' ? 'success' : 'error',
        message: data.message || (data.status === 'success' ? 'Compilation successful' : 'Compilation failed'),
        errors: data.errors || [],
      });
      
      // Set fixes from the response
      setFixes(data.fixes || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to local compiler server. Make sure local_server.py is running on port 8001.');
      setResult(null);
      setFixes(null);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleReset = () => {
    setIsResetting(true);
    setCode(defaultCode);
    setResult(null);
    setError(null);
    setTimeout(() => setIsResetting(false), 300);
  };

  // Apply a single fix object to the current code. fix.edit has {type,line,content} or replace
  const applyFix = (fix: any) => {
    if (!fix || !fix.edit) return;
    const edit = fix.edit;
    const lines = code.split(/\r?\n/);
    const lineIndex = Math.max(0, Math.min(lines.length, (edit.line || 1) - 1));

    if (edit.type === 'insert') {
      // insert before lineIndex (1-based line number)
      lines.splice(lineIndex, 0, ...(edit.content || '').split(/\r?\n/));
    } else if (edit.type === 'replace') {
      // replace the specific line
      if (typeof edit.line === 'number') {
        lines[lineIndex] = edit.replacement !== undefined ? edit.replacement : edit.content || '';
      }
    }

    const newCode = lines.join('\n');
    setCode(newCode);
    // after applying a fix, clear fixes/result so user can re-run compile
    setFixes(null);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      <header className="bg-white border-b border-blue-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <FileCode className="w-8 h-8 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-900">
              Adaptive Error Recovery Compiler
            </h1>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Code Input</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReset}
                  disabled={isCompiling || isResetting}
                  className={`flex items-center gap-2 px-3 py-2 bg-gray-200 hover:bg-gray-300 disabled:bg-gray-100 text-gray-700 rounded-lg transition-all shadow-sm font-medium ${
                    isResetting ? 'animate-reset-button' : ''
                  }`}
                  title="Reset code to default"
                >
                  <RotateCcw className={`w-4 h-4 ${isResetting ? 'animate-spin' : ''}`} />
                </button>
                <button
                  onClick={handleCompile}
                  disabled={isCompiling}
                  className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white rounded-lg transition-colors shadow-sm font-medium"
                >
                  {isCompiling ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Compiling...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Compile Code
                    </>
                  )}
                </button>
              </div>
            </div>

            <CodeEditor value={code} onChange={setCode} />
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-gray-900">Output</h2>
              {result && (
                result.status === 'success' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                )
              )}
            </div>

            <OutputPanel
              result={result}
              error={error}
              isCompiling={isCompiling}
              fixes={fixes}
              onApplyFix={applyFix}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
