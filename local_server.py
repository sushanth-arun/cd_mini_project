#!/usr/bin/env python3
"""
Simple local server for Adaptive Error Recovery Compiler
Works fully locally with Ollama - no external API needed
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os
import tempfile
import shutil
import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List, Optional

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
        fix['description'] = 'AI suggested fix'

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
        content_length = int(self.headers['Content-Length'])
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
        except BrokenPipeError:
            # Client disconnected before response finished; ignore.
            pass
        except ConnectionResetError:
            pass

    def compile_code(self, code: str) -> Dict[str, Any]:
        """Compile code and return errors/fixes using local tools"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'main.c')
            with open(src, 'w') as f:
                f.write(code)

            # Try to get clang diagnostics
            errors = []
            try:
                clang_result = self.run_clang_diagnostics(src)
                if clang_result:
                    mapped = self.map_clang_diags(clang_result)
                    # Include both errors and warnings (treat scanf format warnings as errors)
                    errors.extend(mapped)
            except FileNotFoundError as e:
                # If clang not found, still try to detect errors heuristically
                print(f"Clang not found: {e}")
                # Check for common errors in code
                if 'printf(' in code and '#include <stdio.h>' not in code:
                    errors.append({
                        'type': 'Error',
                        'message': 'printf may be undeclared (missing #include <stdio.h>)',
                        'line': None
                    })
            except Exception as e:
                print(f"Error running diagnostics: {e}")
                # Fallback: check for common errors
                if 'printf(' in code and '#include <stdio.h>' not in code:
                    errors.append({
                        'type': 'Error',
                        'message': 'printf may be undeclared (missing #include <stdio.h>)',
                        'line': None
                    })
            
            # Enhanced heuristic error detection
            errors.extend(self.detect_heuristic_errors(code))
            
            # Use Ollama for AI-powered error detection (integrated, not optional)
            ollama_errors = self.get_ollama_error_detection(code, errors)
            if ollama_errors:
                # Merge Ollama errors, avoiding duplicates
                existing_messages = {e.get('message', '') for e in errors}
                for err in ollama_errors:
                    if err.get('message', '') not in existing_messages:
                        errors.append(err)

            # Generate fixes (heuristic + AI)
            fixes = self.generate_fixes(code, errors)
            
            # If no errors, success
            if not errors:
                return {
                    'status': 'success',
                    'message': 'Compilation successful',
                    'errors': [],
                    'fixes': []
                }

            return {
                'status': 'error',
                'message': 'Compilation failed',
                'errors': errors,
                'fixes': fixes
            }

    def run_clang_diagnostics(self, source_path: str) -> Dict[str, Any]:
        """Run clang diagnostics on source file"""
        def find_clang():
            candidates = [
                shutil.which('clang'),
                shutil.which('clang-14'),
                shutil.which('clang-13'),
                '/opt/homebrew/opt/llvm/bin/clang',
                '/usr/local/opt/llvm/bin/clang',
                '/usr/local/bin/clang',
                '/usr/bin/clang',  # Apple clang location
            ]
            for c in candidates:
                if not c or not os.path.exists(c):
                    continue
                try:
                    # First try JSON format (for newer clang versions)
                    probe = subprocess.run(
                        [c, '-fsyntax-only', '-fdiagnostics-format=json', '-x', 'c', '-'],
                        input='int main(){}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                        text=True, timeout=2
                    )
                    # JSON format outputs to stdout
                    stdout = probe.stdout or ''
                    stderr = probe.stderr or ''
                    # Check both stdout and stderr for JSON
                    if ('{' in stdout and 'diagnostics' in stdout) or ('{' in stderr and 'diagnostics' in stderr):
                        return c, True

                    # If JSON flag isn't supported (Apple clang prints "invalid value 'json'")
                    stderr_lower = stderr.lower()
                    if 'invalid value' in stderr_lower or 'unknown argument' in stderr_lower or 'unsupported option' in stderr_lower:
                        probe2 = subprocess.run(
                            [c, '-fsyntax-only', '-x', 'c', '-'],
                            input='int main(){}', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=2
                        )
                        if probe2.returncode == 0 or 'error:' not in (probe2.stderr or '').lower():
                            return c, False
                        continue

                    # If JSON not supported but clang still works, use it anyway (Apple clang)
                    if probe.returncode == 0 or 'error:' not in stderr_lower:
                        return c, False
                except Exception:
                    # If JSON format fails, try without it (for Apple clang)
                    try:
                        probe2 = subprocess.run(
                            [c, '-fsyntax-only', '-x', 'c', '-'],
                            input='int main(){}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            text=True, timeout=2
                        )
                        # If it runs without error, clang is available (just no JSON support)
                        return c, False
                    except Exception:
                        continue
            return None, False

        clang, supports_json = find_clang()
        if not clang:
            raise FileNotFoundError('clang not found')

        cmd = [clang, '-fsyntax-only', '-fno-color-diagnostics']
        if supports_json:
            cmd += ['-fdiagnostics-format=json']
        cmd.append(source_path)

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               check=False, timeout=4)
            
            # When using JSON format, clang outputs to stdout
            if supports_json:
                text = res.stdout.decode('utf-8', errors='replace')
                try:
                    json_data = json.loads(text)
                    if isinstance(json_data, dict) and 'diagnostics' in json_data:
                        return json_data['diagnostics']
                    elif isinstance(json_data, list):
                        return json_data
                except json.JSONDecodeError:
                    # If JSON parsing fails, try stderr
                    text = res.stderr.decode('utf-8', errors='replace')
                    try:
                        json_data = json.loads(text)
                        if isinstance(json_data, dict) and 'diagnostics' in json_data:
                            return json_data['diagnostics']
                    except json.JSONDecodeError:
                        pass
            
            # Parse raw output from stderr
            text = res.stderr.decode('utf-8', errors='replace')
            if not text.strip():
                # If stderr is empty, check stdout for raw errors
                text = res.stdout.decode('utf-8', errors='replace')
            
            return self.parse_raw_diagnostics(text)
        except subprocess.TimeoutExpired:
            return []
        except Exception as e:
            print(f"Error running clang: {e}")
            return []

    def parse_raw_diagnostics(self, text: str) -> List[Dict[str, Any]]:
        """Parse raw clang diagnostic output"""
        diagnostics = []
        if not text or not text.strip():
            return diagnostics
            
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for error or warning patterns
            if 'error:' in line.lower() or 'warning:' in line.lower():
                # Try to parse format: file:line:column: error/warning: message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    try:
                        line_num = int(parts[1]) if parts[1].strip().isdigit() else None
                        level_str = parts[2].strip().lower()
                        level = 'error' if 'error' in level_str else 'warning'
                        message = parts[3].strip()
                        
                        if message:  # Only add if we have a message
                            diagnostics.append({
                                'level': level,
                                'message': message,
                                'location': {'line': line_num} if line_num else {}
                            })
                    except (ValueError, IndexError):
                        # If parsing fails, try simpler pattern
                        if 'error:' in line.lower():
                            msg = line.split('error:', 1)[-1].strip()
                            if msg:
                                diagnostics.append({
                                    'level': 'error',
                                    'message': msg,
                                    'location': {}
                                })
                        elif 'warning:' in line.lower():
                            msg = line.split('warning:', 1)[-1].strip()
                            if msg:
                                diagnostics.append({
                                    'level': 'warning',
                                    'message': msg,
                                    'location': {}
                                })
            # Also check for standalone error messages
            elif 'undeclared' in line.lower() or 'implicit declaration' in line.lower():
                diagnostics.append({
                    'level': 'error',
                    'message': line,
                    'location': {}
                })
            # Check for scanf format warnings (should be treated as errors)
            elif 'format specifies type' in line.lower() and 'scanf' in line.lower():
                diagnostics.append({
                    'level': 'error',
                    'message': line,
                    'location': {}
                })
        
        return diagnostics

    def map_clang_diags(self, diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map clang diagnostics to our format"""
        out = []
        for d in diags:
            loc = d.get('location', {})
            line = loc.get('line') if isinstance(loc, dict) else None
            level = d.get('level', 'error')
            # Treat warnings as errors for scanf format issues
            message = d.get('message', '')
            if 'format specifies type' in message and 'scanf' in message.lower():
                typ = 'Error'
                level = 'error'
            else:
                typ = 'Error' if level == 'error' else 'Warning'
            out.append({
                'type': typ,
                'message': message,
                'line': line
            })
        return out

    def generate_fixes(self, code: str, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate fixes using heuristics and Ollama"""
        fixes = []
        lines = code.splitlines()

        # Heuristic fixes
        if any('printf(' in l for l in lines) and not any('#include <stdio.h>' in l for l in lines):
            fixes.append({
                'description': 'Add #include <stdio.h> at the top to declare printf',
                'confidence': 0.9,
                'edit': {
                    'type': 'insert',
                    'line': 1,
                    'content': '#include <stdio.h>\n'
                }
            })

        # Missing semicolon detection (enhanced)
        for i, l in enumerate(lines):
            stripped = l.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Check for common statements that need semicolons
            needs_semicolon = False
            if stripped.endswith(';') or stripped.endswith('{') or stripped.endswith('}'):
                continue
            
            # Function calls, assignments, returns, declarations
            if (re.match(r'^\s*\w+\s*\([^)]*\)\s*$', stripped) or  # Function call
                re.match(r'^\s*\w+\s*=\s*.*$', stripped) or  # Assignment
                re.match(r'^\s*return\s+.*$', stripped) or  # Return
                re.match(r'^\s*(int|char|float|double|void)\s+\w+.*$', stripped)):  # Declaration
                # But not function definitions
                if '{' not in l and ')' in l:
                    needs_semicolon = True
            
            if needs_semicolon:
                fixes.append({
                    'description': f'Add missing semicolon at end of line {i+1}',
                    'confidence': 0.85,
                    'edit': {
                        'type': 'replace',
                        'line': i + 1,
                        'original': l,
                        'replacement': l.rstrip() + ';'
                    }
                })
                break

        # scanf missing & operator
        for i, l in enumerate(lines):
            # Match scanf with format string but missing & before variable
            # Pattern: scanf("format", variable) where variable is not &variable
            match = re.search(r'scanf\s*\(\s*"[^"]*"\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', l)
            if match:
                var = match.group(1)
                # Check if & is already present
                if f'&{var}' not in l:
                    # Replace scanf("format", var) with scanf("format", &var)
                    fixed_line = re.sub(
                        r'scanf\s*\(\s*("[^"]*")\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
                        r'scanf(\1, &\2)',
                        l
                    )
                    if fixed_line != l:
                        fixes.append({
                            'description': f'Add & before {var} in scanf (scanf requires a pointer)',
                            'confidence': 0.95,
                            'edit': {
                                'type': 'replace',
                                'line': i + 1,
                                'original': l,
                                'replacement': fixed_line
                            }
                        })
                        break

        # Always try to get AI suggestions from Ollama (integrated, not optional)
        if shutil.which('ollama'):
            ai_fixes = self.get_ollama_fixes(code, errors)
            if ai_fixes:
                for ai_fix in ai_fixes:
                    normalized = normalize_fix(ai_fix, code)
                    if normalized:
                        fixes.append(normalized)

        return fixes

    def detect_heuristic_errors(self, code: str) -> List[Dict[str, Any]]:
        """Detect common errors using heuristics"""
        errors = []
        lines = code.splitlines()
        
        # Check for scanf errors
        for i, line in enumerate(lines):
            if re.search(r'scanf\s*\(\s*"[^"]*"\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', line):
                var_match = re.search(r'scanf\s*\(\s*"[^"]*"\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', line)
                if var_match and f'&{var_match.group(1)}' not in line:
                    errors.append({
                        'type': 'Error',
                        'message': f'format specifies type \'int *\' but the argument has type \'int\' (missing & before {var_match.group(1)})',
                        'line': i + 1
                    })
                    break
        
        # Check for missing semicolons (common patterns)
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Check for statements that should end with semicolon
            if stripped and not stripped.startswith('#'):
                # Patterns that typically need semicolons
                patterns_need_semicolon = [
                    r'^\s*(int|char|float|double|void)\s+\w+\s*=.*[^;]$',  # Variable declaration with assignment
                    r'^\s*\w+\s*=\s*.*[^;]$',  # Assignment
                    r'^\s*return\s+.*[^;]$',  # Return statement
                    r'^\s*\w+\s*\([^)]*\)\s*$',  # Function call (but not definition)
                ]
                for pattern in patterns_need_semicolon:
                    if re.match(pattern, stripped) and not stripped.endswith('{') and not stripped.endswith('}'):
                        # Check if it's actually a function definition
                        if '{' in line or ')' in line and '(' in line:
                            # Might be function definition, skip
                            continue
                        errors.append({
                            'type': 'Error',
                            'message': f'Expected \';\' at end of statement (line {i+1})',
                            'line': i + 1
                        })
                        break
        
        return errors

    def get_ollama_error_detection(self, code: str, existing_errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use Ollama to detect errors that clang might miss (like missing semicolons)"""
        if not shutil.which('ollama'):
            return []
        
        errors = []
        error_summary = '\n'.join([f"Line {e.get('line', '?')}: {e.get('message', '')}" for e in existing_errors]) if existing_errors else "None detected yet"
        
        prompt = f"""You are a C compiler error detection assistant. Analyze this C code and identify ALL syntax errors, including:
- Missing semicolons
- Missing includes
- Type mismatches
- Undeclared identifiers
- Any other compilation errors

Code:
```c
{code}
```

Already detected errors:
{error_summary}

Respond with a JSON array of errors in this exact format:
[
  {{
    "type": "Error",
    "message": "detailed error message",
    "line": 3
  }}
]

If no additional errors found, return an empty array: []"""

        try:
            res = subprocess.run(
                ['ollama', 'run', OLLAMA_MODEL, '--prompt', prompt],
                capture_output=True,
                text=True,
                timeout=OLLAMA_TIMEOUT
            )
            if res.returncode == 0:
                output = res.stdout.strip()
                json_match = re.search(r'\[.*\]', output, re.DOTALL)
                if json_match:
                    try:
                        error_data = json.loads(json_match.group())
                        if isinstance(error_data, list):
                            for err in error_data:
                                if isinstance(err, dict):
                                    errors.append(err)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"Ollama error detection failed: {e}")
        
        return errors

    def get_ollama_fixes(self, code: str, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get fix suggestions from Ollama (integrated, always tries to use)"""
        if not shutil.which('ollama'):
            return []
        
        fixes = []
        error_summary = '\n'.join([f"Line {e.get('line', '?')}: {e.get('type', 'Error')}: {e.get('message', '')}" for e in errors])
        
        prompt = f"""You are a C compiler error recovery assistant. Analyze the code and errors, then suggest precise fixes.

Code:
```c
{code}
```

Errors:
{error_summary}

For each error, suggest a fix. Respond with a JSON array of fixes:
[
  {{
    "description": "Brief description of the fix",
    "confidence": 0.9,
    "edit": {{
      "type": "insert" or "replace",
      "line": 2,
      "content": "the fix content"
    }}
  }}
]

If type is "replace", include "original" and "replacement" fields instead of "content"."""

        try:
            res = subprocess.run(
                ['ollama', 'run', OLLAMA_MODEL, '--prompt', prompt],
                capture_output=True,
                text=True,
                timeout=OLLAMA_TIMEOUT
            )
            if res.returncode == 0:
                output = res.stdout.strip()
                json_match = re.search(r'\[.*\]', output, re.DOTALL)
                if json_match:
                    try:
                        fix_data = json.loads(json_match.group())
                        if isinstance(fix_data, list):
                            for f in fix_data:
                                normalized = normalize_fix(f, code)
                                if normalized:
                                    fixes.append(normalized)
                    except json.JSONDecodeError:
                        pass
                else:
                    obj_match = re.search(r'\{[^{}]*\}', output, re.DOTALL)
                    if obj_match:
                        try:
                            fix_obj = json.loads(obj_match.group())
                            normalized = normalize_fix(fix_obj, code)
                            if normalized:
                                fixes.append(normalized)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Ollama fix generation failed: {e}")
        
        return fixes

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(port=8001):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, CompilerHandler)
    print(f"Local compiler server running on http://127.0.0.1:{port}")
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

