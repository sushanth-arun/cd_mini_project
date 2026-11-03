# Adaptive Error Recovery Compiler
> **5th Semester Compiler Design (CD) Mini Project**

A modern web-based C compiler and analyzer demonstrating the complete 6-phase compiler pipeline alongside intelligent adaptive error recovery and one-click automatic fixes.

---

## 🌟 Compiler Pipeline & Key Implementations

1. **Phase 1: Lexical Analysis (Scanner / Tokenizer)**
   - Regex-based tokenization recognizing keywords, identifiers, numeric literals, string/char literals, operators, delimiters, and preprocessor directives.
   - Lexical error detection (unterminated multi-line comments `/* ...`, unterminated string literals, invalid characters).
   - Generates structured token table with token types, lexemes, line numbers, and column offsets.

2. **Phase 2: Syntax Analysis (Recursive-Descent Parser & AST)**
   - Recursive-descent parser for C translation units (functions, variable declarations, expressions, control flow).
   - Syntactic bracket & parenthesis balance checker (phrase-level & panic-mode error reporting).
   - Generates an Abstract Syntax Tree (AST) visualizing program hierarchy.

3. **Phase 3: Semantic Analysis & Scoped Symbol Table**
   - Scoped Symbol Table tracking identifiers, data types, scope (global/local), memory size in bytes, declaration line, initialization status, and usage reference count.
   - Semantic checks:
     - Use of undeclared identifiers.
     - Identifier redeclaration in the same scope.
     - Type mismatch (e.g. assigning string literals to integer types).
     - Implicit declarations of standard library functions (missing `#include <stdio.h>`).
     - Pointer mismatches in I/O (e.g. `scanf` without address-of operator `&`).
     - Unused variable warnings and constant division-by-zero detection.

4. **Phase 4: Intermediate Code Generation (Three-Address Code / TAC & Quadruples)**
   - Generates standard Three-Address Code (TAC) according to the Aho-Ullman Dragon Book specification.
   - Quadruple representation `(op, arg1, arg2, result)` for statements, expressions, and relational branching (`if_false`, `goto`, labels).

5. **Phase 5: Code Optimization**
   - **Constant Folding**: Evaluates constant arithmetic at compile time (e.g., `2 + 3 * 4` folded to `14`).
   - **Dead Code Elimination (DCE)**: Prunes unreachable instructions occurring after unconditional returns.
   - Side-by-side comparison of unoptimized vs. optimized TAC with percentage IR reduction metrics.

6. **Phase 6: Adaptive Error Recovery & Automated Patching**
   - Autonomous error classification and patch generation with confidence scoring (80% - 98%).
   - One-click "Apply Fix" button that automatically modifies source code in the editor and triggers immediate re-compilation.

7. **Target Output Simulator**
   - Simulates program standard output execution for verified programs.

---

## 🚀 Quick Start (Windows CMD & PowerShell)

### Terminal 1: Backend Server (Port 8001)
```cmd
python local_server.py 8001
```
*(Or double-click `start_backend.bat`)*

Backend runs at: `http://127.0.0.1:8001`

### Terminal 2: Frontend Dev Server (Port 5174)
```cmd
npm run dev
```
*(Or double-click `start_frontend.bat`)*

Open your browser at: `http://localhost:5174`

---

## 💻 Preset Demo Examples for College Review

The UI includes a quick **Test Presets** dropdown with 5 pre-configured scenarios ready for live review presentation:
1. **Missing Semicolon & Header**: Shows header injection and phrase-level semicolon insertion.
2. **Scanf Missing & Operator**: Shows semantic pointer check and automatic address-of `&` fix.
3. **Undeclared Var & Type Mismatch**: Shows Symbol Table lookup, variable scopes, and type compatibility.
4. **Control Flow & 3-Address Code**: Shows TAC and Quadruple generation for `if-else` branching.
5. **Constant Folding & Optimization**: Shows compile-time arithmetic evaluation and dead-code removal.
