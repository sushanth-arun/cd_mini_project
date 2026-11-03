#!/usr/bin/env python3
"""
Local server for Adaptive Error Recovery Compiler
5th Semester Compiler Design Mini Project

Features:
- Pure-Python Full Compiler Pipeline (Lexer, Parser, AST, Scoped Symbol Table, TAC, Optimizer, Safe Execution Simulator)
- Adaptive Error Recovery & Automated One-Click Fixes
- Optional Clang & Ollama LLM integration if locally available
- Zero external Python dependencies (runs on standard Python 3.8+)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os
import tempfile
import shutil
import re
from typing import Dict, Any, List, Optional
import compiler_engine

# Ollama configuration
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '8'))


def _coerce_int(value: Any, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_fix(fix: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    """Ensure fix conforms to expected schema for frontend apply functionality."""
    if not isinstance(fix, dict):
        return None

    edit = fix.get('edit')
    if not isinstance(edit, dict):
        return None

    edit_type = edit.get('type')
    if edit_type not in {'insert', 'replace'}:
        return None

    line = _coerce_int(edit.get('line'), 1)
    edit['line'] = max(line, 1)

    if edit_type == 'insert':
        content = edit.get('content') or edit.get('replacement')
        if not isinstance(content, str):
            return None
        edit['content'] = content.rstrip('\n') + '\n'
        edit.pop('replacement', None)
        edit.pop('original', None)
    elif edit_type == 'replace':
        replacement = edit.get('replacement') or edit.get('content')
        original = edit.get('original')
        if not isinstance(replacement, str):
            return None
        lines = code.splitlines()
        idx = edit['line'] - 1
        if 0 <= idx < len(lines) and not original:
            original = lines[idx]
        if not isinstance(original, str):
            return None
        edit['replacement'] = replacement
        edit['original'] = original
        edit.pop('content', None)

    if 'confidence' in fix:
        try:
            fix['confidence'] = float(fix['confidence'])
        except (TypeError, ValueError):
            fix['confidence'] = 0.7
    else:
        fix['confidence'] = 0.7

    if 'description' not in fix or not isinstance(fix['description'], str):
        fix['description'] = 'Adaptive error recovery fix'

    fix['edit'] = edit
    return fix


class CompilerHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self.send_json_response({
                'message': 'Adaptive Error Recovery Compiler - Local Server',
                'status': 'running',
                'phases': [
                    'Lexical Analysis (Scanner)',
                    'Syntax Analysis (Recursive-Descent Parser & AST)',
                    'Semantic Analysis & Symbol Table',
                    'Intermediate Code Generation (Three-Address Code & Quadruples)',
                    'Code Optimization (Constant Folding & Dead Code Elimination)',
                    'Adaptive Recovery Engine (One-click fixes)',
                    'Program Execution Simulation'
                ],
                'endpoints': {
                    'compile': 'POST /compile'
                }
            })
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/compile':
            self.handle_compile()
        else:
            self.send_error(404)

    def handle_compile(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode('utf-8'))
            code = data.get('code', '').strip()

            if not code:
                self.send_json_response({'error': 'No code provided'}, 400)
                return

            result = self.compile_code(code)
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)

    def send_json_response(self, data, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def compile_code(self, code: str) -> Dict[str, Any]:
        """Runs full compiler pipeline and merges optional local tool diagnostics (Clang, Ollama)."""
        # 1. Execute full pure-Python compiler engine
        engine_res = compiler_engine.run_full_compiler_pipeline(code)

        merged_errors = list(engine_res.get('errors', []))
        merged_fixes = list(engine_res.get('fixes', []))

        # 2. Try Clang diagnostics if clang is installed locally
        if shutil.which('clang'):
            with tempfile.TemporaryDirectory() as tmpdir:
                src = os.path.join(tmpdir, 'main.c')
                with open(src, 'w') as f:
                    f.write(code)
                try:
                    clang_result = self.run_clang_diagnostics(src)
                    if clang_result:
                        mapped = self.map_clang_diags(clang_result)
                        existing_msgs = {e.get('message', '').lower() for e in merged_errors}
                        for err in mapped:
                            if err.get('message', '').lower() not in existing_msgs:
                                merged_errors.append(err)
                except Exception as e:
                    print(f"Clang diagnostics skipped: {e}")

        # 3. Query local Ollama if installed
        if shutil.which('ollama') and len(merged_errors) > 0:
            try:
                ai_fixes = self.get_ollama_fixes(code, merged_errors)
                if ai_fixes:
                    for af in ai_fixes:
                        normalized = normalize_fix(af, code)
                        if normalized and normalized['description'] not in {f['description'] for f in merged_fixes}:
                            merged_fixes.append(normalized)
            except Exception as e:
                print(f"Ollama integration skipped: {e}")

        # Normalize all fixes
        cleaned_fixes = []
        for f in merged_fixes:
            norm = normalize_fix(f, code)
            if norm:
                cleaned_fixes.append(norm)

        fatal_errors = [e for e in merged_errors if e.get('severity', 'error') == 'error' or e.get('type') == 'Error']

        status = 'success' if len(fatal_errors) == 0 else 'error'
        message = 'Compilation successful!' if status == 'success' else f'Compilation failed with {len(fatal_errors)} error(s)'

        return {
            'status': status,
            'message': message,
            'tokens': engine_res.get('tokens', []),
            'ast': engine_res.get('ast', {}),
            'symbol_table': engine_res.get('symbol_table', []),
            'errors': merged_errors,
            'error_count': len(fatal_errors),
            'warning_count': len(merged_errors) - len(fatal_errors),
            'tac': engine_res.get('tac', {'instructions': [], 'quadruples': []}),
            'optimization': engine_res.get('optimization', {
                'optimized_instructions': [],
                'optimized_quadruples': [],
                'logs': [],
                'reduction_pct': 0.0
            }),
            'fixes': cleaned_fixes,
            'execution_output': engine_res.get('execution_output')
        }

    def run_clang_diagnostics(self, source_path: str) -> List[Dict[str, Any]]:
        clang = shutil.which('clang')
        if not clang:
            return []
        try:
            cmd = [clang, '-fsyntax-only', '-fno-color-diagnostics', source_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=4)
            text = res.stderr.decode('utf-8', errors='replace')
            return self.parse_raw_diagnostics(text)
        except Exception:
            return []

    def parse_raw_diagnostics(self, text: str) -> List[Dict[str, Any]]:
        diagnostics = []
        if not text:
            return diagnostics
        for line in text.splitlines():
            line = line.strip()
            if 'error:' in line.lower() or 'warning:' in line.lower():
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    try:
                        line_num = int(parts[1].strip()) if parts[1].strip().isdigit() else None
                        level = 'error' if 'error' in parts[2].lower() else 'warning'
                        msg = parts[3].strip()
                        if msg:
                            diagnostics.append({
                                'level': level,
                                'message': msg,
                                'location': {'line': line_num} if line_num else {}
                            })
                    except Exception:
                        pass
        return diagnostics

    def map_clang_diags(self, diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for d in diags:
            loc = d.get('location', {})
            line = loc.get('line') if isinstance(loc, dict) else None
            level = d.get('level', 'error')
            typ = 'Error' if level == 'error' else 'Warning'
            out.append({
                'type': typ,
                'message': d.get('message', ''),
                'line': line,
                'severity': level
            })
        return out

    def get_ollama_fixes(self, code: str, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not shutil.which('ollama'):
            return []
        fixes = []
        err_summary = '\n'.join([f"Line {e.get('line', '?')}: {e.get('message', '')}" for e in errors])
        prompt = f"""You are a C compiler recovery assistant. Analyze this code and errors, and suggest fixes in JSON format:
Code:
{code}
Errors:
{err_summary}

Respond ONLY with a JSON array:
[
  {{
    "description": "Fix description",
    "confidence": 0.9,
    "edit": {{
      "type": "insert" or "replace",
      "line": 1,
      "content": "new line content"
    }}
  }}
]"""
        try:
            res = subprocess.run(
                ['ollama', 'run', OLLAMA_MODEL, '--prompt', prompt],
                capture_output=True, text=True, timeout=OLLAMA_TIMEOUT
            )
            if res.returncode == 0:
                match = re.search(r'\[.*\]', res.stdout, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                fixes.append(item)
        except Exception:
            pass
        return fixes

    def log_message(self, format, *args):
        pass


def run_server(port=8001):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, CompilerHandler)
    print(f"Adaptive Error Recovery Compiler Server running on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    run_server(port)
