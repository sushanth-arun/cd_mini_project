import { useState } from 'react';
import {
  Play,
  FileCode,
  Loader2,
  RotateCcw,
  BookOpen
} from 'lucide-react';
import CodeEditor from './components/CodeEditor';
import OutputPanel, { CompileResult } from './components/OutputPanel';

const PRESET_EXAMPLES = [
  {
    id: 'missing_semicolon_header',
    name: '1. Missing Semicolon & Header',
    description: 'Demonstrates automated header injection and phrase-level semicolon insertion.',
    code: `int main() {
    int x = 10;
    printf("Hello, World!")
    return 0;
}`
  },
  {
    id: 'scanf_pointer_error',
    name: '2. Scanf Missing & Operator',
    description: 'Demonstrates semantic pointer detection and automatic address-of (&) fix.',
    code: `#include <stdio.h>
int main() {
    int age;
    printf("Enter your age: ");
    scanf("%d", age);
    printf("Age is %d\\n", age);
    return 0;
}`
  },
  {
    id: 'semantic_type_undeclared',
    name: '3. Undeclared Var & Type Mismatch',
    description: 'Demonstrates Symbol Table lookup, undeclared identifier, and type checking.',
    code: `#include <stdio.h>
int main() {
    int count = 5;
    total = count + 10;
    int invalid = "hello";
    return 0;
}`
  },
  {
    id: 'control_flow_tac',
    name: '4. Control Flow & 3-Address Code',
    description: 'Generates Three-Address Code (TAC), Labels, and Quadruples for branches.',
    code: `#include <stdio.h>
int main() {
    int score = 85;
    if (score >= 50) {
        printf("Passed!\\n");
    } else {
        printf("Failed!\\n");
    }
    return 0;
}`
  },
  {
    id: 'clean_optimization',
    name: '5. Optimization Suite (Folding, Strength Reduction, CSE, DCE)',
    description: 'Demonstrates Constant Folding, Strength Reduction (x*2 -> x+x), Algebraic Identities, CSE, and DCE.',
    code: `#include <stdio.h>

int compute(int x) {
    // 1. Strength Reduction: multiplication by 2 -> addition (x + x)
    int double_val = x * 2;
    // 2. Strength Reduction: power-of-2 multiplication -> bitwise left-shift (x << 2)
    int quad_val = x * 4;
    // 3. Strength Reduction: power-of-2 division -> bitwise right-shift (x >> 1)
    int div_val = x / 2;

    // 4. Algebraic Transformations (Additive/Multiplicative Identity & Zero Property)
    int ident_add = x + 0;
    int ident_mul = x * 1;
    int zero_prop = x * 0;

    // 5. Common Subexpression Elimination (CSE: reuses calculation)
    int cse1 = x + 15;
    int cse2 = x + 15;

    return double_val + cse1 + cse2;
}

int main() {
    // 6. Constant Folding (evaluated at compile-time: 5 * 2 = 10)
    int count = 5 * 2;
    int result = compute(count);
    printf("Result is %d\\n", result);
    return 0;

    // 7. Dead Code Elimination (unreachable code pruned)
    int dead_audit = 999;
}`
  }
];

function App() {
  const [selectedExampleId, setSelectedExampleId] = useState<string>('missing_semicolon_header');
  const [code, setCode] = useState(PRESET_EXAMPLES[0].code);
  const [result, setResult] = useState<CompileResult | null>(null);
  const [fixes, setFixes] = useState<any[] | null>(null);
  const [isCompiling, setIsCompiling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const handleSelectExample = (id: string) => {
    setSelectedExampleId(id);
    const ex = PRESET_EXAMPLES.find(e => e.id === id);
    if (ex) {
      setCode(ex.code);
      setResult(null);
      setFixes(null);
      setError(null);
    }
  };

  const handleCompile = async () => {
    setIsCompiling(true);
    setError(null);

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

      const data: CompileResult = await response.json();
      setResult(data);
      setFixes(data.fixes || null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to connect to local compiler server. Ensure python local_server.py is running on port 8001.'
      );
      setResult(null);
      setFixes(null);
    } finally {
      setIsCompiling(false);
    }
  };

  const handleReset = () => {
    setIsResetting(true);
    const ex = PRESET_EXAMPLES.find(e => e.id === selectedExampleId) || PRESET_EXAMPLES[0];
    setCode(ex.code);
    setResult(null);
    setFixes(null);
    setError(null);
    setTimeout(() => setIsResetting(false), 300);
  };

  const applyFix = (fix: any) => {
    if (!fix || !fix.edit) return;
    const edit = fix.edit;
    const lines = code.split(/\r?\n/);
    const lineIndex = Math.max(0, Math.min(lines.length, (edit.line || 1) - 1));

    if (edit.type === 'insert') {
      const contentLines = (edit.content || '').replace(/\r\n/g, '\n').split('\n');
      if (contentLines[contentLines.length - 1] === '') {
        contentLines.pop();
      }
      lines.splice(lineIndex, 0, ...contentLines);
    } else if (edit.type === 'replace') {
      if (typeof edit.line === 'number') {
        lines[lineIndex] = edit.replacement !== undefined ? edit.replacement : edit.content || '';
      }
    }

    const newCode = lines.join('\n');
    setCode(newCode);

    setTimeout(() => {
      fetch('http://127.0.0.1:8001/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: newCode }),
      })
        .then(res => res.json())
        .then(data => {
          setResult(data);
          setFixes(data.fixes || null);
        })
        .catch(() => {
          setFixes(null);
          setResult(null);
        });
    }, 100);
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-slate-900 border-b border-slate-800 text-white shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-xl shadow-inner">
              <FileCode className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">
                Adaptive Error Recovery Compiler
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex-1 w-full space-y-4">
        {/* Toolbar: Example Selector & Primary Actions */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-1">
            <BookOpen className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">
              Test Presets:
            </span>
            <select
              value={selectedExampleId}
              onChange={e => handleSelectExample(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-300 text-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500 font-medium flex-1 max-w-md"
            >
              {PRESET_EXAMPLES.map(ex => (
                <option key={ex.id} value={ex.id}>
                  {ex.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 justify-end">
            <button
              onClick={handleReset}
              disabled={isCompiling || isResetting}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-all shadow-xs"
              title="Reset code editor"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              <span>Reset</span>
            </button>

            <button
              onClick={handleCompile}
              disabled={isCompiling}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg text-xs font-semibold transition-all shadow-sm"
            >
              {isCompiling ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Compiling...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Compile Code</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 2-Column Split View: Editor on Left, Output on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <div className="space-y-2">
            <div className="px-1">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Source Code Input
              </span>
            </div>
            <CodeEditor value={code} onChange={setCode} />
          </div>

          <div className="space-y-2">
            <div className="px-1">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Compiler Analysis & Pipeline
              </span>
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

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-2.5 text-center text-xs text-slate-400 font-medium">
        Adaptive Error Recovery Compiler
      </footer>
    </div>
  );
}

export default App;
