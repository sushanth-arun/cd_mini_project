from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import tempfile
import json
import shutil
from typing import List, Dict, Any

app = Flask(__name__)

# Configure CORS for development
allowed_origins = [
    os.environ.get('VITE_BACKEND_URL', ''),
    'http://localhost:5173',
    'http://127.0.0.1:5173'
]
allowed_origins = [o for o in allowed_origins if o]
CORS(app, origins=allowed_origins or '*')

FIX_MEMORY_FILE = "fix_memory.json"  # to store successful recovery patterns


# ---------- Helper: Find and run clang diagnostics ----------
def run_clang_diagnostics(source_path: str) -> Dict[str, Any]:
    def find_clang() -> tuple[str | None, bool]:
        candidates = [
            shutil.which('clang'),
            shutil.which('clang-14'),
            shutil.which('clang-13'),
            '/opt/homebrew/opt/llvm/bin/clang',
            '/usr/local/opt/llvm/bin/clang',
            '/usr/local/bin/clang',
        ]
        for c in candidates:
            if not c or not os.path.exists(c):
                continue
            try:
                probe = subprocess.run(
                    [c, '-fsyntax-only', '-fdiagnostics-format=json', '-x', 'c', '-'],
                    input='int main(){}', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2
                )
                stderr = probe.stderr or ''
                if '{' in stderr and 'diagnostics' in stderr:
                    return c, True
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
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=4)
        text = res.stderr.decode('utf-8', errors='replace')
        if supports_json:
            try:
                return {'diagnostics': json.loads(text).get('diagnostics', [])}
            except Exception:
                pass
        return {'raw': text}
    except subprocess.TimeoutExpired:
        return {'timeout': True}


# ---------- Helper: Simplify clang diagnostics ----------
def map_clang_diags(diags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for d in diags:
        loc = d.get('location', {})
        line = loc.get('line') if isinstance(loc, dict) else None
        level = d.get('level', 'error')
        typ = 'Error' if level == 'error' else 'Warning'
        out.append({'type': typ, 'message': d.get('message', ''), 'line': line})
    return out


# ---------- Heuristic fixes ----------
def generate_fallback_fixes(code: str) -> List[Dict[str, Any]]:
    fixes = []
    lines = code.splitlines()

    # printf undeclared
    if any('printf(' in l for l in lines) and not any('#include <stdio.h>' in l for l in lines):
        fixes.append({'description': 'Add #include <stdio.h>', 'confidence': 0.9,
                      'edit': {'type': 'insert', 'line': 1, 'content': '#include <stdio.h>\n'}})

    # missing semicolon
    for i, l in enumerate(lines):
        if 'printf(' in l and not l.strip().endswith(';'):
            fixes.append({'description': 'Add missing semicolon', 'confidence': 0.9,
                          'edit': {'type': 'replace', 'line': i+1, 'original': l, 'replacement': l+';'}})
            break

    # scanf missing &
    import re
    for i, l in enumerate(lines):
        match = re.search(r'scanf\s*\(\s*"[^"]*"\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', l)
        if match:
            var = match.group(1)
            fixed_line = re.sub(r'scanf\s*\(\s*("[^"]*")\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
                                r'scanf(\1, &\2)', l)
            if fixed_line != l:
                fixes.append({'description': f'Add & before {var} in scanf', 'confidence': 0.9,
                              'edit': {'type': 'replace', 'line': i+1, 'original': l, 'replacement': fixed_line}})
                break

    # double semicolon
    for i, l in enumerate(lines):
        if ';;' in l:
            fixes.append({'description': 'Remove extra semicolon', 'confidence': 0.8,
                          'edit': {'type': 'replace', 'line': i+1, 'original': l, 'replacement': l.replace(";;", ";")}})
            break

    return fixes


# ---------- Adaptive recompilation logic ----------
def adaptive_recompile(code: str, fixes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply confident fixes → recompile → use LLM feedback if still failing."""
    applied_code = code
    for fix in fixes:
        if fix.get('confidence', 0) >= 0.8:
            line = fix['edit']['line']
            lines = applied_code.splitlines()
            if fix['edit']['type'] == 'insert':
                lines.insert(line - 1, fix['edit']['content'])
            elif fix['edit']['type'] == 'replace':
                lines[line - 1] = fix['edit']['replacement']
            applied_code = "\n".join(lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, 'main.c')
        with open(src, 'w') as f:
            f.write(applied_code)
        try:
            result = run_clang_diagnostics(src)
            if 'diagnostics' in result and not result['diagnostics']:
                save_successful_fix("auto_fix", fixes)
                return {'status': 'recovered', 'code': applied_code,
                        'message': 'Code successfully recovered using adaptive fix.'}
            else:
                llm_feedback = _get_ai_suggestion("Residual compiler errors detected.", applied_code)
                return {'status': 'llm_feedback', 'code': applied_code, 'llm': llm_feedback}
        except Exception as e:
            return {'status': 'failed', 'message': str(e)}


# ---------- LLM feedback ----------
def _get_ai_suggestion(error_message: str, code: str) -> str | None:
    """Ask LLM (OpenAI or Ollama) for suggestions."""
    api_key = ""
    if api_key:
        try:
            import openai
            openai.api_key = api_key
            messages = [
                {"role": "system", "content": "You are part of an Adaptive Error Recovery System for a C Compiler. Suggest concise and minimal code corrections."},
                {"role": "user", "content": f"Error:\n{error_message}\n\nCode:\n{code}\n\nSuggest one precise fix and one-line reason."}
            ]
            resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=messages, max_tokens=150)
            return resp.choices[0].message.content.strip()
        except Exception:
            pass

    # fallback to local Ollama
    if shutil.which('ollama'):
        try:
            prompt = f"Error:\n{error_message}\n\nCode:\n{code}\nSuggest one short fix and one-sentence reason."
            res = subprocess.run(['ollama', 'run', 'llama3', prompt], capture_output=True, text=True, timeout=8)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass

    return None


# ---------- Memory persistence for successful recoveries ----------
def save_successful_fix(error_message: str, fix: Dict[str, Any]):
    memory = {}
    if os.path.exists(FIX_MEMORY_FILE):
        with open(FIX_MEMORY_FILE, 'r') as f:
            memory = json.load(f)
    memory[error_message[:80]] = fix
    with open(FIX_MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)


# ---------- Flask Routes ----------
@app.route('/')
def home():
    return jsonify({"message": "Adaptive Error Recovery System with LLM Feedback is running!"})


@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    if not code:
        return jsonify({'error': 'No code provided'}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, 'main.c')
        with open(src, 'w') as f:
            f.write(code)

        try:
            result = run_clang_diagnostics(src)
        except FileNotFoundError:
            fixes = generate_fallback_fixes(code)
            return jsonify({'status': 'error', 'message': 'Clang not found, using heuristics.', 'fixes': fixes})

        if 'raw' in result:
            fixes = generate_fallback_fixes(code)
            return jsonify({'status': 'error', 'message': 'Raw diagnostic output', 'fixes': fixes, 'errors': result['raw']})

        diags = result.get('diagnostics', [])
        mapped = map_clang_diags(diags)
        fixes = generate_fallback_fixes(code)
        adaptive = adaptive_recompile(code, fixes)

        return jsonify({
            'status': 'compiled',
            'errors': mapped,
            'fixes': fixes,
            'adaptive': adaptive
        })


if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__) or '.')
    port = int(os.environ.get('BACKEND_PORT', '8000'))
    app.run(host='127.0.0.1', port=port, debug=True)

