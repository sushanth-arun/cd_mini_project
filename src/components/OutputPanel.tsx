import { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Code,
  Table,
  GitBranch,
  Cpu,
  Zap,
  Terminal,
  Search,
  Wand2,
  Check,
  Flame,
  Calculator,
  Shuffle
} from 'lucide-react';

export interface Token {
  type: string;
  value: string;
  line: number;
  col?: number;
}

export interface CompilerError {
  type: string;
  message: string;
  line?: number;
  severity?: string;
}

export interface SymbolItem {
  name: string;
  type: string;
  scope: string;
  line: number;
  size?: number;
  initialized?: boolean;
  is_function?: boolean;
  references?: number;
}

export interface Quadruple {
  op: string;
  arg1: string;
  arg2: string;
  result: string;
}

export interface OptimizationData {
  optimized_instructions?: string[];
  optimized_quadruples?: Quadruple[];
  logs?: string[];
  categories?: {
    constant_folding?: number;
    algebraic_transformations?: number;
    strength_reduction?: number;
    common_subexpressions?: number;
    dead_code_elimination?: number;
    copy_propagation?: number;
  };
  reduction_pct?: number;
}

export interface CompileResult {
  status: string;
  message?: string;
  tokens?: Token[];
  ast?: any;
  symbol_table?: SymbolItem[];
  errors?: CompilerError[];
  error_count?: number;
  warning_count?: number;
  tac?: {
    instructions?: string[];
    quadruples?: Quadruple[];
  };
  optimization?: OptimizationData;
  fixes?: any[];
  execution_output?: string | null;
}

interface OutputPanelProps {
  result: CompileResult | null;
  error: string | null;
  isCompiling: boolean;
  fixes?: any[] | null;
  onApplyFix?: (fix: any) => void;
}

type TabType = 'errors' | 'tokens' | 'ast' | 'symbol_table' | 'tac' | 'optimization';

function OutputPanel({ result, error, isCompiling, fixes, onApplyFix }: OutputPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('errors');
  const [tokenSearch, setTokenSearch] = useState('');
  const [appliedFixIdx, setAppliedFixIdx] = useState<number | null>(null);

  if (isCompiling) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 h-[540px] flex items-center justify-center">
        <div className="text-center">
          <div className="relative inline-block mb-4">
            <div className="w-14 h-14 rounded-full border-4 border-blue-100 border-t-primary-600 animate-spin"></div>
            <Cpu className="w-6 h-6 text-primary-600 absolute inset-0 m-auto" />
          </div>
          <h3 className="text-base font-semibold text-slate-800">Compiling & Analyzing</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Running Lexer, Recursive-Descent Parser, Semantic Checks, TAC Generation, Optimizer, and Adaptive Recovery...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6 h-[540px] flex flex-col justify-center">
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 max-w-lg mx-auto">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900 mb-1">Compiler Server Offline</h3>
              <p className="text-sm text-red-700 leading-relaxed">{error}</p>
              <div className="mt-4 bg-white/80 p-3 rounded-lg border border-red-200 font-mono text-xs text-red-800">
                python local_server.py 8001
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 h-[540px] flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-100 shadow-inner">
            <Code className="w-8 h-8 text-primary-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-800">Ready to Compile</h3>
          <p className="text-sm text-slate-500 mt-2 leading-relaxed">
            Click <strong>"Compile Code"</strong> or select a preset example to run all compiler phases.
          </p>
        </div>
      </div>
    );
  }

  const isSuccess = result.status === 'success';
  const errors = result.errors || [];
  const fatalErrors = errors.filter(e => e.severity === 'error' || e.type.toLowerCase().includes('error'));
  const warnings = errors.filter(e => e.severity === 'warning' || e.type.toLowerCase().includes('warning'));
  const tokens = result.tokens || [];
  const filteredTokens = tokens.filter(t =>
    t.value.toLowerCase().includes(tokenSearch.toLowerCase()) ||
    t.type.toLowerCase().includes(tokenSearch.toLowerCase())
  );
  const symbolList = result.symbol_table || [];
  const tac = result.tac || { instructions: [], quadruples: [] };
  const opt = result.optimization || { optimized_instructions: [], logs: [], reduction_pct: 0 };
  const categories = opt.categories || {};
  const availableFixes = fixes || result.fixes || [];

  const handleApply = (fix: any, index: number) => {
    setAppliedFixIdx(index);
    if (onApplyFix) {
      onApplyFix(fix);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm h-[540px] flex flex-col overflow-hidden">
      {/* Status Bar */}
      <div className={`px-4 py-2.5 border-b flex items-center justify-between ${
        isSuccess ? 'bg-emerald-50/80 border-emerald-200' : 'bg-amber-50/80 border-amber-200'
      }`}>
        <div className="flex items-center gap-2.5">
          {isSuccess ? (
            <div className="flex items-center gap-1.5 text-emerald-800 font-semibold text-sm">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span>Compilation Successful</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-amber-900 font-semibold text-sm">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>Issues Detected: {fatalErrors.length} Error{fatalErrors.length === 1 ? '' : 's'}, {warnings.length} Warning{warnings.length === 1 ? '' : 's'}</span>
            </div>
          )}
        </div>
        {availableFixes.length > 0 && (
          <div className="flex items-center gap-1.5 bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-full text-xs font-medium">
            <Wand2 className="w-3 h-3 text-blue-600" />
            <span>{availableFixes.length} Auto-Fix{availableFixes.length === 1 ? '' : 'es'} Ready</span>
          </div>
        )}
      </div>

      {/* Compiler Phase Tabs */}
      <div className="bg-slate-100 border-b border-slate-200 px-2 flex items-center overflow-x-auto text-xs font-medium gap-1 py-1.5 scrollbar-none">
        <button
          onClick={() => setActiveTab('errors')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'errors'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <AlertCircle className={`w-3.5 h-3.5 ${fatalErrors.length > 0 ? 'text-red-500' : 'text-slate-400'}`} />
          <span>Diagnostics & Fixes</span>
          {errors.length > 0 && (
            <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
              fatalErrors.length > 0 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
            }`}>
              {errors.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('tokens')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'tokens'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <Code className="w-3.5 h-3.5 text-blue-500" />
          <span>1. Lexer ({tokens.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('ast')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'ast'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <GitBranch className="w-3.5 h-3.5 text-purple-500" />
          <span>2. Parser & AST</span>
        </button>

        <button
          onClick={() => setActiveTab('symbol_table')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'symbol_table'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <Table className="w-3.5 h-3.5 text-emerald-500" />
          <span>3. Symbol Table ({symbolList.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('tac')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'tac'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <Cpu className="w-3.5 h-3.5 text-orange-500" />
          <span>4. TAC (IR)</span>
        </button>

        <button
          onClick={() => setActiveTab('optimization')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
            activeTab === 'optimization'
              ? 'bg-white text-slate-900 shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <Zap className="w-3.5 h-3.5 text-amber-500" />
          <span>5. Optimizer & Output</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="flex-1 overflow-y-auto p-4 bg-slate-50/50">
        {/* TAB 1: DIAGNOSTICS & ADAPTIVE FIXES */}
        {activeTab === 'errors' && (
          <div className="space-y-4">
            {availableFixes.length > 0 && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Wand2 className="w-4 h-4 text-blue-600" />
                    <h4 className="text-sm font-semibold text-blue-900">
                      Adaptive Error Recovery (One-Click Fixes)
                    </h4>
                  </div>
                  <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded font-mono">
                    Autonomous Fixer
                  </span>
                </div>
                <div className="space-y-2.5">
                  {availableFixes.map((fix: any, idx: number) => {
                    const confidence = Math.round((fix.confidence || 0.85) * 100);
                    return (
                      <div
                        key={idx}
                        className="bg-white rounded-lg p-3 border border-blue-100 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 hover:border-blue-300 transition-all"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                              {fix.category || 'Adaptive Patch'}
                            </span>
                            <span className="text-xs text-slate-500">
                              Confidence: <strong className="text-blue-700">{confidence}%</strong>
                            </span>
                          </div>
                          <p className="text-xs font-medium text-slate-800">{fix.description}</p>
                          {fix.edit && (
                            <p className="text-[11px] font-mono text-slate-500">
                              Target Line: {fix.edit.line} &bull; Action: {fix.edit.type}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => handleApply(fix, idx)}
                          className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-lg text-xs font-medium transition-all shadow-sm flex-shrink-0"
                        >
                          {appliedFixIdx === idx ? (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              Applied!
                            </>
                          ) : (
                            <>
                              <Wand2 className="w-3.5 h-3.5" />
                              Apply Fix
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {errors.length > 0 ? (
              <div className="space-y-2.5">
                <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Diagnostic Reports ({errors.length})
                </h4>
                {errors.map((err, idx) => {
                  const isErr = err.severity === 'error' || err.type.toLowerCase().includes('error');
                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border text-xs ${
                        isErr
                          ? 'bg-red-50/80 border-red-200 text-red-900'
                          : 'bg-amber-50/80 border-amber-200 text-amber-900'
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        {isErr ? (
                          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1 space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[11px] uppercase tracking-wide">
                              {err.type || (isErr ? 'Syntax Error' : 'Warning')}
                            </span>
                            {err.line && (
                              <span className="font-mono bg-white/70 px-1.5 py-0.5 rounded text-[10px] border">
                                Line {err.line}
                              </span>
                            )}
                          </div>
                          <p className="leading-relaxed font-mono">{err.message}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-500">
                <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
                <h4 className="text-base font-semibold text-slate-800">Clean Compilation!</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Zero syntax or semantic errors found. Check the other tabs for Tokens, AST, Symbol Table, and TAC!
                </p>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: LEXICAL ANALYSIS (TOKENS) */}
        {activeTab === 'tokens' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Filter tokens by type or value..."
                  value={tokenSearch}
                  onChange={e => setTokenSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
                />
              </div>
              <span className="text-xs text-slate-500 font-mono whitespace-nowrap">
                {filteredTokens.length} / {tokens.length} tokens
              </span>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="text-left px-3 py-2">Index</th>
                    <th className="text-left px-3 py-2">Token Type</th>
                    <th className="text-left px-3 py-2">Lexeme (Value)</th>
                    <th className="text-left px-3 py-2">Line</th>
                    <th className="text-left px-3 py-2">Column</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredTokens.map((tok, idx) => (
                    <tr key={idx} className="hover:bg-blue-50/40 transition-colors">
                      <td className="px-3 py-1.5 text-slate-400">{idx + 1}</td>
                      <td className="px-3 py-1.5">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          tok.type === 'KEYWORD' ? 'bg-purple-100 text-purple-700' :
                          tok.type === 'IDENTIFIER' ? 'bg-blue-100 text-blue-700' :
                          tok.type === 'OPERATOR' ? 'bg-amber-100 text-amber-700' :
                          tok.type.includes('LITERAL') ? 'bg-emerald-100 text-emerald-700' :
                          tok.type === 'PREPROCESSOR' ? 'bg-indigo-100 text-indigo-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {tok.type}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 text-slate-900 font-bold">{tok.value}</td>
                      <td className="px-3 py-1.5 text-slate-500">{tok.line}</td>
                      <td className="px-3 py-1.5 text-slate-500">{tok.col || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: SYNTAX ANALYSIS & AST */}
        {activeTab === 'ast' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-mono">
                Abstract Syntax Tree (AST) generated via Recursive-Descent Parsing
              </span>
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded font-mono font-medium">
                Phase 2: Syntax
              </span>
            </div>

            <div className="bg-slate-950 text-slate-200 p-4 rounded-xl border border-slate-800 font-mono text-xs overflow-x-auto shadow-inner max-h-[380px]">
              <pre>{JSON.stringify(result.ast, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* TAB 4: SYMBOL TABLE */}
        {activeTab === 'symbol_table' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-mono">
                Identifier Symbol Table with Scopes & Types
              </span>
              <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono font-medium">
                Phase 3: Semantic
              </span>
            </div>

            <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-xs">
              <table className="w-full text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="text-left px-3 py-2">Identifier</th>
                    <th className="text-left px-3 py-2">Type</th>
                    <th className="text-left px-3 py-2">Scope</th>
                    <th className="text-left px-3 py-2">Size</th>
                    <th className="text-left px-3 py-2">Line</th>
                    <th className="text-left px-3 py-2">Init</th>
                    <th className="text-left px-3 py-2">Refs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {symbolList.map((sym, idx) => (
                    <tr key={idx} className="hover:bg-emerald-50/40 transition-colors">
                      <td className="px-3 py-2 font-bold text-slate-900 flex items-center gap-1.5">
                        {sym.name}
                        {sym.is_function && (
                          <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.2 rounded font-sans">
                            func
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-primary-700 font-semibold">{sym.type}</td>
                      <td className="px-3 py-2 text-slate-600">{sym.scope}</td>
                      <td className="px-3 py-2 text-slate-500">{sym.size !== undefined ? `${sym.size}B` : '-'}</td>
                      <td className="px-3 py-2 text-slate-500">{sym.line}</td>
                      <td className="px-3 py-2">
                        {sym.initialized ? (
                          <span className="text-emerald-600 font-semibold">Yes</span>
                        ) : (
                          <span className="text-red-500 font-semibold">No</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600">{sym.references || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: THREE-ADDRESS CODE (TAC) */}
        {activeTab === 'tac' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500 font-mono">
                Intermediate Code Generation (Three-Address Code & Quadruples)
              </span>
              <span className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded font-mono font-medium">
                Phase 4: Intermediate Code
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950 text-emerald-400 p-4 rounded-xl border border-slate-800 font-mono text-xs overflow-y-auto max-h-[350px] shadow-inner">
                <div className="text-slate-400 text-[11px] mb-2 border-b border-slate-800 pb-1 font-semibold">
                  ; Linear TAC Instructions:
                </div>
                {tac.instructions && tac.instructions.length > 0 ? (
                  tac.instructions.map((line, idx) => (
                    <div key={idx} className="leading-6">
                      {line}
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500">No TAC instructions generated</div>
                )}
              </div>

              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs max-h-[350px] overflow-y-auto">
                <div className="bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 border-b border-slate-200">
                  Quadruples Table (Op, Arg1, Arg2, Result)
                </div>
                <table className="w-full text-xs font-mono">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
                    <tr>
                      <th className="px-2 py-1.5 text-left">#</th>
                      <th className="px-2 py-1.5 text-left">Op</th>
                      <th className="px-2 py-1.5 text-left">Arg1</th>
                      <th className="px-2 py-1.5 text-left">Arg2</th>
                      <th className="px-2 py-1.5 text-left">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(tac.quadruples || []).map((q, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="px-2 py-1 text-slate-400">{idx}</td>
                        <td className="px-2 py-1 font-bold text-orange-600">{q.op}</td>
                        <td className="px-2 py-1 text-slate-700">{q.arg1 || '-'}</td>
                        <td className="px-2 py-1 text-slate-700">{q.arg2 || '-'}</td>
                        <td className="px-2 py-1 text-primary-700 font-semibold">{q.result || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 6: OPTIMIZATION & OUTPUT */}
        {activeTab === 'optimization' && (
          <div className="space-y-4">
            {/* Optimization Techniques Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Constant Folding</div>
                <div className="text-base font-bold text-blue-600 mt-0.5">
                  {categories.constant_folding || 0}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Strength Red. (x*2→x+x)</div>
                <div className="text-base font-bold text-amber-600 mt-0.5">
                  {categories.strength_reduction || 0}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Algebraic Ident. (x+0)</div>
                <div className="text-base font-bold text-purple-600 mt-0.5">
                  {categories.algebraic_transformations || 0}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Common Subexpr. (CSE)</div>
                <div className="text-base font-bold text-indigo-600 mt-0.5">
                  {categories.common_subexpressions || 0}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Dead Code (DCE)</div>
                <div className="text-base font-bold text-red-600 mt-0.5">
                  {categories.dead_code_elimination || 0}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs text-center">
                <div className="text-[10px] text-slate-500 font-medium">Total Reduction</div>
                <div className="text-base font-bold text-emerald-600 mt-0.5 flex items-center justify-center gap-0.5">
                  <Flame className="w-3.5 h-3.5 text-orange-500" />
                  {opt.reduction_pct || 0}%
                </div>
              </div>
            </div>

            {/* Optimization Technique Badges */}
            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs">
              <div className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500" />
                Active Machine-Independent Optimization Passes:
              </div>
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                  <Calculator className="w-3 h-3" /> Constant Folding & Propagation
                </span>
                <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Strength Reduction (x*2 &rarr; x+x, x*4 &rarr; x&lt;&lt;2)
                </span>
                <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 flex items-center gap-1">
                  <Shuffle className="w-3 h-3" /> Algebraic Identities (x+0 &rarr; x, x*1 &rarr; x, x*0 &rarr; 0)
                </span>
                <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Common Subexpression Elimination (CSE)
                </span>
                <span className="px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">
                  Dead Code & Dead Store Elimination (DCE)
                </span>
              </div>
            </div>

            {/* Detailed Optimization Logs */}
            {opt.logs && opt.logs.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs space-y-1 font-mono text-emerald-400 max-h-[160px] overflow-y-auto shadow-inner">
                <div className="text-slate-400 text-[11px] font-semibold border-b border-slate-800 pb-1 mb-1 flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Optimization Transformations Applied ({opt.logs.length}):
                </div>
                {opt.logs.map((log, idx) => (
                  <div key={idx} className="leading-5">
                    <span className="text-slate-600 mr-1.5">{idx + 1}.</span>
                    {log}
                  </div>
                ))}
              </div>
            )}

            {/* Side-by-side TAC Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-900 text-slate-300 p-3 rounded-lg font-mono text-xs overflow-y-auto max-h-[160px]">
                <div className="text-slate-400 text-[11px] mb-1 font-semibold border-b border-slate-800 pb-1">
                  Unoptimized TAC:
                </div>
                {(tac.instructions || []).map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
              </div>
              <div className="bg-slate-950 text-emerald-400 p-3 rounded-lg font-mono text-xs overflow-y-auto max-h-[160px]">
                <div className="text-emerald-500 text-[11px] mb-1 font-semibold border-b border-slate-800 pb-1">
                  Optimized TAC:
                </div>
                {(opt.optimized_instructions || []).map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
              </div>
            </div>

            {/* Simulated Program Output Terminal */}
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-3.5 shadow-inner">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-mono mb-1.5 border-b border-slate-800 pb-1.5">
                <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                <span>Simulated Program Output:</span>
              </div>
              <div className="text-emerald-400 font-mono text-xs whitespace-pre-wrap leading-relaxed min-h-[35px]">
                {result.execution_output || (
                  <span className="text-slate-500 italic">
                    Clean compilation output will appear here.
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default OutputPanel;
