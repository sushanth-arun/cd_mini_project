"""
Compiler Engine for Adaptive Error Recovery Compiler
5th Semester Compiler Design Mini Project

Phases:
1. Lexical Analysis (Scanner & Tokenizer)
2. Syntax Analysis (Recursive Descent Parser & Abstract Syntax Tree)
3. Semantic Analysis & Scoped Symbol Table
4. Intermediate Code Generation (Three-Address Code / Quadruples)
5. Code Optimization (Constant Folding & Dead Code Elimination)
6. Adaptive Error Recovery & Automated Fix Generation
7. Safe Program Output Simulation
"""

import re
from typing import List, Dict, Any, Optional, Tuple


# ============================================================================
# PHASE 1: LEXICAL ANALYSIS (SCANNER)
# ============================================================================

KEYWORDS = {
    'int', 'float', 'char', 'double', 'void', 'long', 'short', 'signed', 'unsigned',
    'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'default', 'break',
    'continue', 'return', 'struct', 'typedef', 'sizeof', 'static', 'const'
}

OPERATORS = {
    '==', '!=', '<=', '>=', '&&', '||', '++', '--', '+=', '-=', '*=', '/=',
    '+', '-', '*', '/', '%', '=', '<', '>', '!', '&', '|', '^', '~'
}

DELIMITERS = {
    ';', ',', '(', ')', '{', '}', '[', ']', ':', '.'
}

TOKEN_SPECIFICATION = [
    ('PREPROCESSOR', r'#\s*(?:include|define)[^\n]*'),
    ('COMMENT_MULTI', r'/\*[\s\S]*?\*/'),
    ('COMMENT_SINGLE', r'//[^\n]*'),
    ('FLOAT_LITERAL', r'\b\d+\.\d+(?:[eE][+-]?\d+)?\b'),
    ('INT_LITERAL',   r'\b\d+\b'),
    ('STRING_LITERAL', r'"(?:\\.|[^"\\])*"'),
    ('CHAR_LITERAL',   r'\'(?:\\.|[^\'\\])\''),
    ('OPERATOR',       r'==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|\*=|/=|[\+\-\*/%=<>!&\|\^~]'),
    ('DELIMITER',      r'[;,\(\)\{\}\[\]\:\.]'),
    ('IDENTIFIER',     r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('NEWLINE',        r'\n'),
    ('SKIP',           r'[ \t\r]+'),
    ('MISMATCH',       r'.'),
]

TOKEN_REGEX = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPECIFICATION)


def tokenize(code: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Lexical Analyzer: Converts raw C source code into a token stream.
    Also detects lexical errors (unterminated strings, invalid chars).
    """
    tokens = []
    lexical_errors = []
    line_num = 1
    line_start = 0

    # Pre-check for unterminated multi-line comment
    if '/*' in code:
        open_idx = 0
        while True:
            open_pos = code.find('/*', open_idx)
            if open_pos == -1:
                break
            close_pos = code.find('*/', open_pos + 2)
            if close_pos == -1:
                line = code[:open_pos].count('\n') + 1
                lexical_errors.append({
                    'type': 'Lexical Error',
                    'message': 'Unterminated multi-line comment (missing */)',
                    'line': line,
                    'severity': 'error'
                })
                break
            open_idx = close_pos + 2

    # Pre-check for unterminated string literals
    for i, line_text in enumerate(code.splitlines(), start=1):
        clean_text = re.sub(r'//.*$', '', line_text)
        # Count non-escaped quotes
        quotes = re.findall(r'(?<!\\)"', clean_text)
        if len(quotes) % 2 != 0:
            lexical_errors.append({
                'type': 'Lexical Error',
                'message': f'Unterminated string literal on line {i}',
                'line': i,
                'severity': 'error'
            })

    for mo in re.finditer(TOKEN_REGEX, code):
        kind = mo.lastgroup
        value = mo.group()
        col = mo.start() - line_start + 1

        if kind == 'NEWLINE':
            line_start = mo.end()
            line_num += 1
            continue
        elif kind == 'SKIP' or kind == 'COMMENT_SINGLE' or kind == 'COMMENT_MULTI':
            if '\n' in value:
                line_num += value.count('\n')
                line_start = mo.end() - (len(value) - value.rfind('\n') - 1)
            continue
        elif kind == 'IDENTIFIER':
            if value in KEYWORDS:
                kind = 'KEYWORD'
        elif kind == 'MISMATCH':
            lexical_errors.append({
                'type': 'Lexical Error',
                'message': f"Unexpected or unrecognized character '{value}'",
                'line': line_num,
                'severity': 'error'
            })
            continue

        tokens.append({
            'type': kind,
            'value': value,
            'line': line_num,
            'col': col
        })

    return tokens, lexical_errors


# ============================================================================
# PHASE 2 & 3: SYNTAX & SEMANTIC ANALYSIS + SYMBOL TABLE + AST
# ============================================================================

TYPE_SIZES = {
    'int': 4,
    'float': 4,
    'double': 8,
    'char': 1,
    'void': 0,
    'short': 2,
    'long': 8
}

STANDARD_LIB_FUNCS = {
    'printf': {'ret': 'int', 'header': '<stdio.h>'},
    'scanf': {'ret': 'int', 'header': '<stdio.h>'},
    'puts': {'ret': 'int', 'header': '<stdio.h>'},
    'gets': {'ret': 'char*', 'header': '<stdio.h>'},
    'malloc': {'ret': 'void*', 'header': '<stdlib.h>'},
    'free': {'ret': 'void', 'header': '<stdlib.h>'},
    'exit': {'ret': 'void', 'header': '<stdlib.h>'},
    'strlen': {'ret': 'int', 'header': '<string.h>'},
    'strcpy': {'ret': 'char*', 'header': '<string.h>'},
    'sqrt': {'ret': 'double', 'header': '<math.h>'},
    'pow': {'ret': 'double', 'header': '<math.h>'}
}


class SymbolTable:
    """Scoped Symbol Table for tracking identifiers, types, scopes, and usages."""
    def __init__(self):
        self.symbols: List[Dict[str, Any]] = []

    def add(self, name: str, data_type: str, scope: str, line: int,
            is_function: bool = False, initialized: bool = False) -> Dict[str, Any]:
        size = TYPE_SIZES.get(data_type.replace('*', '').strip(), 4)
        sym = {
            'name': name,
            'type': data_type,
            'scope': scope,
            'line': line,
            'size': size,
            'initialized': initialized,
            'is_function': is_function,
            'references': 0
        }
        self.symbols.append(sym)
        return sym

    def lookup(self, name: str, scope: str = None) -> Optional[Dict[str, Any]]:
        # Match local scope first, then global
        if scope:
            for s in reversed(self.symbols):
                if s['name'] == name and s['scope'] == scope:
                    return s
        for s in reversed(self.symbols):
            if s['name'] == name:
                return s
        return None

    def mark_used(self, name: str, scope: str = None):
        sym = self.lookup(name, scope)
        if sym:
            sym['references'] += 1

    def mark_initialized(self, name: str, scope: str = None):
        sym = self.lookup(name, scope)
        if sym:
            sym['initialized'] = True

    def to_list(self) -> List[Dict[str, Any]]:
        return self.symbols


class CParserAndAnalyzer:
    """
    Parses C source code, performs Syntax & Semantic Analysis,
    populates the Symbol Table, and generates the Abstract Syntax Tree (AST).
    """
    def __init__(self, code: str, tokens: List[Dict[str, Any]]):
        self.code = code
        self.tokens = tokens
        self.pos = 0
        self.errors: List[Dict[str, Any]] = []
        self.symbol_table = SymbolTable()
        self.current_scope = 'global'
        self.includes: List[str] = []
        self.ast_nodes: List[Dict[str, Any]] = []

    def current_token(self) -> Optional[Dict[str, Any]]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset: int = 1) -> Optional[Dict[str, Any]]:
        idx = self.pos + offset
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def advance(self) -> Optional[Dict[str, Any]]:
        tok = self.current_token()
        self.pos += 1
        return tok

    def match(self, tok_type: str, value: str = None) -> bool:
        tok = self.current_token()
        if not tok:
            return False
        if tok['type'] == tok_type:
            if value is None or tok['value'] == value:
                self.advance()
                return True
        return False

    def expect(self, tok_type: str, value: str = None, error_msg: str = None) -> Optional[Dict[str, Any]]:
        tok = self.current_token()
        if not tok:
            line = self.tokens[-1]['line'] if self.tokens else 1
            self.errors.append({
                'type': 'Syntax Error',
                'message': error_msg or f"Expected '{value or tok_type}' before end of input",
                'line': line,
                'severity': 'error'
            })
            return None
        if tok['type'] == tok_type and (value is None or tok['value'] == value):
            return self.advance()
        self.errors.append({
            'type': 'Syntax Error',
            'message': error_msg or f"Expected '{value or tok_type}' but found '{tok['value']}'",
            'line': tok['line'],
            'severity': 'error'
        })
        return None

    def analyze(self) -> Dict[str, Any]:
        """Runs syntax parsing and semantic checks across the entire token stream."""
        # 1. Collect preprocessor directives and bracket balance
        self.check_bracket_balance()
        self.extract_preprocessor_includes()

        # 2. Parse top-level declarations and functions
        program_ast = {
            'type': 'Program',
            'name': 'TranslationUnit',
            'children': []
        }

        while self.pos < len(self.tokens):
            tok = self.current_token()
            if not tok:
                break

            if tok['type'] == 'PREPROCESSOR':
                self.advance()
                continue

            # Look for function or global declaration
            decl_ast = self.parse_top_level_declaration()
            if decl_ast:
                program_ast['children'].append(decl_ast)
            else:
                self.advance()

        # 3. Post-parse semantic verifications
        self.check_unused_variables()

        return {
            'ast': program_ast,
            'symbol_table': self.symbol_table.to_list(),
            'errors': self.errors,
            'includes': self.includes
        }

    def check_bracket_balance(self):
        """Phrase-level syntax check for unbalanced parentheses, brackets, and braces."""
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        for tok in self.tokens:
            val = tok['value']
            if val in '({[':
                stack.append((val, tok['line']))
            elif val in ')}]':
                expected = pairs[val]
                if not stack:
                    self.errors.append({
                        'type': 'Syntax Error',
                        'message': f"Unmatched closing '{val}' with no matching '{expected}'",
                        'line': tok['line'],
                        'severity': 'error'
                    })
                else:
                    last_open, open_line = stack.pop()
                    if last_open != expected:
                        self.errors.append({
                            'type': 'Syntax Error',
                            'message': f"Mismatched bracket: opened with '{last_open}' (line {open_line}) but closed with '{val}'",
                            'line': tok['line'],
                            'severity': 'error'
                        })
        while stack:
            unclosed, open_line = stack.pop()
            closing = { '(': ')', '{': '}', '[': ']' }[unclosed]
            self.errors.append({
                'type': 'Syntax Error',
                'message': f"Unclosed '{unclosed}' from line {open_line} (missing '{closing}')",
                'line': open_line,
                'severity': 'error'
            })

    def extract_preprocessor_includes(self):
        for tok in self.tokens:
            if tok['type'] == 'PREPROCESSOR':
                val = tok['value']
                match = re.search(r'#\s*include\s*[<"]([^>"]+)[>"]', val)
                if match:
                    self.includes.append(f"<{match.group(1)}>")

    def parse_top_level_declaration(self) -> Optional[Dict[str, Any]]:
        tok = self.current_token()
        if not tok:
            return None

        # Check for type specifier
        if tok['type'] == 'KEYWORD' and tok['value'] in TYPE_SIZES:
            type_name = tok['value']
            self.advance()

            # Optional pointer
            if self.match('OPERATOR', '*'):
                type_name += '*'

            ident_tok = self.current_token()
            if not ident_tok or ident_tok['type'] != 'IDENTIFIER':
                return None

            ident_name = ident_tok['value']
            decl_line = ident_tok['line']
            self.advance()

            # Check if function or variable
            next_tok = self.current_token()
            if next_tok and next_tok['value'] == '(':
                # Function declaration / definition
                return self.parse_function_definition(type_name, ident_name, decl_line)
            else:
                # Global variable declaration
                return self.parse_variable_declaration(type_name, ident_name, decl_line, is_global=True)

        return None

    def parse_function_definition(self, ret_type: str, func_name: str, line: int) -> Dict[str, Any]:
        self.expect('DELIMITER', '(', "Expected '(' after function name")
        params = self.parse_parameter_list()
        self.expect('DELIMITER', ')', "Expected ')' after parameter list")

        # Record function in symbol table
        self.symbol_table.add(func_name, f"func()->{ret_type}", 'global', line, is_function=True, initialized=True)

        func_ast = {
            'type': 'FunctionDeclaration',
            'return_type': ret_type,
            'name': func_name,
            'parameters': params,
            'line': line,
            'children': []
        }

        # Check for body or prototype
        curr = self.current_token()
        if curr and curr['value'] == '{':
            old_scope = self.current_scope
            self.current_scope = func_name
            body_ast = self.parse_compound_statement()
            func_ast['body'] = body_ast
            func_ast['children'].append(body_ast)
            self.current_scope = old_scope

            # Semantic check: non-void function must have return statement
            if ret_type != 'void' and func_name != 'main':
                has_return = any(node.get('type') == 'ReturnStatement' for node in body_ast.get('children', []))
                if not has_return:
                    self.errors.append({
                        'type': 'Semantic Warning',
                        'message': f"Non-void function '{func_name}' does not contain an explicit return statement",
                        'line': line,
                        'severity': 'warning'
                    })
        elif curr and curr['value'] == ';':
            self.advance()
            func_ast['type'] = 'FunctionPrototype'

        return func_ast

    def parse_parameter_list(self) -> List[Dict[str, Any]]:
        params = []
        while self.current_token() and self.current_token()['value'] != ')':
            tok = self.current_token()
            if tok['type'] == 'KEYWORD' and tok['value'] in TYPE_SIZES:
                p_type = tok['value']
                self.advance()
                ident = self.current_token()
                if ident and ident['type'] == 'IDENTIFIER':
                    params.append({'type': p_type, 'name': ident['value'], 'line': ident['line']})
                    self.symbol_table.add(ident['value'], p_type, self.current_scope, ident['line'], initialized=True)
                    self.advance()
            if self.current_token() and self.current_token()['value'] == ',':
                self.advance()
            else:
                break
        return params

    def parse_compound_statement(self) -> Dict[str, Any]:
        """Parses a block `{ ... }`."""
        self.expect('DELIMITER', '{')
        block_ast = {
            'type': 'CompoundStatement',
            'scope': self.current_scope,
            'children': []
        }

        while self.pos < len(self.tokens):
            curr = self.current_token()
            if not curr:
                break
            if curr['value'] == '}':
                self.advance()
                break

            stmt_ast = self.parse_statement()
            if stmt_ast:
                block_ast['children'].append(stmt_ast)
            else:
                self.advance()

        return block_ast

    def parse_statement(self) -> Optional[Dict[str, Any]]:
        curr = self.current_token()
        if not curr:
            return None

        # 1. Local variable declaration: int x = 10;
        if curr['type'] == 'KEYWORD' and curr['value'] in TYPE_SIZES:
            type_name = curr['value']
            self.advance()
            if self.match('OPERATOR', '*'):
                type_name += '*'
            ident = self.current_token()
            if ident and ident['type'] == 'IDENTIFIER':
                ident_name = ident['value']
                line = ident['line']
                self.advance()
                return self.parse_variable_declaration(type_name, ident_name, line, is_global=False)

        # 2. Return statement: return 0;
        if curr['type'] == 'KEYWORD' and curr['value'] == 'return':
            ret_line = curr['line']
            self.advance()
            expr_ast = None
            if self.current_token() and self.current_token()['value'] != ';':
                expr_ast = self.parse_expression()
            self.expect_semicolon(ret_line, "Missing ';' after return statement")
            return {
                'type': 'ReturnStatement',
                'line': ret_line,
                'expression': expr_ast
            }

        # 3. If Statement: if (...) { ... } else { ... }
        if curr['type'] == 'KEYWORD' and curr['value'] == 'if':
            if_line = curr['line']
            self.advance()
            self.expect('DELIMITER', '(', "Expected '(' after 'if'")
            cond_expr = self.parse_expression()
            self.expect('DELIMITER', ')', "Expected ')' after if condition")
            then_block = self.parse_statement_or_block()
            else_block = None
            if self.current_token() and self.current_token()['value'] == 'else':
                self.advance()
                else_block = self.parse_statement_or_block()
            return {
                'type': 'IfStatement',
                'line': if_line,
                'condition': cond_expr,
                'then_branch': then_block,
                'else_branch': else_block
            }

        # 4. While loop: while (...) { ... }
        if curr['type'] == 'KEYWORD' and curr['value'] == 'while':
            while_line = curr['line']
            self.advance()
            self.expect('DELIMITER', '(', "Expected '(' after 'while'")
            cond_expr = self.parse_expression()
            self.expect('DELIMITER', ')', "Expected ')' after while condition")
            body = self.parse_statement_or_block()
            return {
                'type': 'WhileStatement',
                'line': while_line,
                'condition': cond_expr,
                'body': body
            }

        # 5. Identifier starting statement: assignment or function call
        if curr['type'] == 'IDENTIFIER':
            ident_name = curr['value']
            ident_line = curr['line']
            self.advance()

            # Check if function call: printf(...)
            if self.current_token() and self.current_token()['value'] == '(':
                call_ast = self.parse_function_call(ident_name, ident_line)
                self.expect_semicolon(ident_line, f"Missing ';' after function call '{ident_name}'")
                return call_ast

            # Assignment: x = 10 + 2;
            if self.current_token() and self.current_token()['value'] in ('=', '+=', '-=', '*=', '/='):
                op = self.current_token()['value']
                self.advance()

                # Semantic check: is variable declared?
                sym = self.symbol_table.lookup(ident_name, self.current_scope)
                if not sym:
                    self.errors.append({
                        'type': 'Semantic Error',
                        'message': f"Use of undeclared identifier '{ident_name}'",
                        'line': ident_line,
                        'severity': 'error'
                    })
                else:
                    self.symbol_table.mark_initialized(ident_name, self.current_scope)
                    self.symbol_table.mark_used(ident_name, self.current_scope)

                rhs_expr = self.parse_expression()
                self.expect_semicolon(ident_line, f"Missing ';' after assignment to '{ident_name}'")

                # Semantic type check
                if sym and rhs_expr and rhs_expr.get('type') == 'StringLiteral' and sym['type'] in ('int', 'float', 'double'):
                    self.errors.append({
                        'type': 'Semantic Error',
                        'message': f"Type mismatch: cannot assign string literal to variable '{ident_name}' of type '{sym['type']}'",
                        'line': ident_line,
                        'severity': 'error'
                    })

                return {
                    'type': 'AssignmentStatement',
                    'target': ident_name,
                    'operator': op,
                    'value': rhs_expr,
                    'line': ident_line
                }

        # Fallback expression statement
        expr = self.parse_expression()
        if expr:
            self.expect_semicolon(expr.get('line', 1), "Missing ';' after expression")
            return expr

        return None

    def parse_statement_or_block(self) -> Dict[str, Any]:
        if self.current_token() and self.current_token()['value'] == '{':
            return self.parse_compound_statement()
        stmt = self.parse_statement()
        return stmt or {'type': 'EmptyStatement'}

    def parse_variable_declaration(self, type_name: str, ident_name: str, line: int, is_global: bool) -> Dict[str, Any]:
        scope = 'global' if is_global else self.current_scope

        # Semantic check: redeclaration in same scope
        existing = self.symbol_table.lookup(ident_name, scope)
        if existing and existing['scope'] == scope:
            self.errors.append({
                'type': 'Semantic Error',
                'message': f"Redeclaration of variable '{ident_name}' in the same scope (previously declared at line {existing['line']})",
                'line': line,
                'severity': 'error'
            })

        initialized = False
        init_expr = None
        if self.current_token() and self.current_token()['value'] == '=':
            self.advance()
            initialized = True
            init_expr = self.parse_expression()

            # Semantic type check
            if init_expr and init_expr.get('type') == 'StringLiteral' and type_name in ('int', 'float', 'double'):
                self.errors.append({
                    'type': 'Semantic Error',
                    'message': f"Type mismatch: cannot initialize variable '{ident_name}' of type '{type_name}' with string literal",
                    'line': line,
                    'severity': 'error'
                })

        self.symbol_table.add(ident_name, type_name, scope, line, initialized=initialized)
        self.expect_semicolon(line, f"Missing ';' after declaration of '{ident_name}'")

        return {
            'type': 'VariableDeclaration',
            'data_type': type_name,
            'name': ident_name,
            'initialized': initialized,
            'initial_value': init_expr,
            'line': line
        }

    def parse_function_call(self, func_name: str, line: int) -> Dict[str, Any]:
        self.expect('DELIMITER', '(')
        args = []

        # Check standard library header requirements
        if func_name in STANDARD_LIB_FUNCS:
            req_header = STANDARD_LIB_FUNCS[func_name]['header']
            if req_header not in self.includes:
                self.errors.append({
                    'type': 'Semantic Warning',
                    'message': f"Implicit declaration of library function '{func_name}' (missing #include {req_header})",
                    'line': line,
                    'severity': 'warning'
                })

        while self.current_token() and self.current_token()['value'] != ')':
            arg_expr = self.parse_expression()
            if arg_expr:
                args.append(arg_expr)
            if self.current_token() and self.current_token()['value'] == ',':
                self.advance()
            else:
                break

        self.expect('DELIMITER', ')', f"Expected ')' to close argument list of '{func_name}'")

        # Semantic check: scanf requires & (pointer) for scalar arguments
        if func_name == 'scanf' and len(args) >= 2:
            for idx, arg in enumerate(args[1:], start=2):
                if arg.get('type') == 'Identifier':
                    var_name = arg.get('value')
                    self.errors.append({
                        'type': 'Semantic Error',
                        'message': f"format specifies pointer argument in scanf, but '{var_name}' was passed by value (missing '&')",
                        'line': line,
                        'severity': 'error'
                    })

        return {
            'type': 'FunctionCall',
            'function_name': func_name,
            'arguments': args,
            'line': line
        }

    def parse_expression(self) -> Optional[Dict[str, Any]]:
        return self.parse_relational_expression()

    def parse_relational_expression(self) -> Optional[Dict[str, Any]]:
        expr = self.parse_additive_expression()
        while self.current_token() and self.current_token()['value'] in ('<', '>', '<=', '>=', '==', '!='):
            op = self.current_token()['value']
            line = self.current_token()['line']
            self.advance()
            right = self.parse_additive_expression()
            expr = {
                'type': 'BinaryExpression',
                'operator': op,
                'left': expr,
                'right': right,
                'line': line
            }
        return expr

    def parse_additive_expression(self) -> Optional[Dict[str, Any]]:
        expr = self.parse_multiplicative_expression()
        while self.current_token() and self.current_token()['value'] in ('+', '-'):
            op = self.current_token()['value']
            line = self.current_token()['line']
            self.advance()
            right = self.parse_multiplicative_expression()
            expr = {
                'type': 'BinaryExpression',
                'operator': op,
                'left': expr,
                'right': right,
                'line': line
            }
        return expr

    def parse_multiplicative_expression(self) -> Optional[Dict[str, Any]]:
        expr = self.parse_unary_expression()
        while self.current_token() and self.current_token()['value'] in ('*', '/', '%'):
            op = self.current_token()['value']
            line = self.current_token()['line']
            self.advance()
            right = self.parse_unary_expression()

            # Semantic check: constant division by zero
            if op in ('/', '%') and right and right.get('type') == 'NumericLiteral' and right.get('value') == '0':
                self.errors.append({
                    'type': 'Semantic Error',
                    'message': 'Division by zero detected at compile-time',
                    'line': line,
                    'severity': 'error'
                })

            expr = {
                'type': 'BinaryExpression',
                'operator': op,
                'left': expr,
                'right': right,
                'line': line
            }
        return expr

    def parse_unary_expression(self) -> Optional[Dict[str, Any]]:
        curr = self.current_token()
        if not curr:
            return None

        # Address-of operator (&x)
        if curr['value'] == '&':
            line = curr['line']
            self.advance()
            sub = self.parse_primary_expression()
            return {'type': 'UnaryExpression', 'operator': '&', 'operand': sub, 'line': line}

        # Pointer dereference (*p) or unary plus/minus
        if curr['value'] in ('-', '+', '!', '*'):
            op = curr['value']
            line = curr['line']
            self.advance()
            sub = self.parse_primary_expression()
            return {'type': 'UnaryExpression', 'operator': op, 'operand': sub, 'line': line}

        return self.parse_primary_expression()

    def parse_primary_expression(self) -> Optional[Dict[str, Any]]:
        curr = self.current_token()
        if not curr:
            return None

        # Parenthesized expression: (expr)
        if curr['value'] == '(':
            self.advance()
            inner = self.parse_expression()
            self.expect('DELIMITER', ')', "Expected ')' to close expression")
            return inner

        # String literal
        if curr['type'] == 'STRING_LITERAL':
            val = curr['value']
            line = curr['line']
            self.advance()
            return {'type': 'StringLiteral', 'value': val, 'line': line}

        # Numeric literal
        if curr['type'] in ('INT_LITERAL', 'FLOAT_LITERAL'):
            val = curr['value']
            line = curr['line']
            self.advance()
            return {'type': 'NumericLiteral', 'value': val, 'line': line}

        # Identifier or Function Call
        if curr['type'] == 'IDENTIFIER':
            ident_name = curr['value']
            line = curr['line']
            self.advance()

            # Check for function call
            if self.current_token() and self.current_token()['value'] == '(':
                return self.parse_function_call(ident_name, line)

            # Check if identifier was declared
            sym = self.symbol_table.lookup(ident_name, self.current_scope)
            if not sym and ident_name not in STANDARD_LIB_FUNCS:
                self.errors.append({
                    'type': 'Semantic Error',
                    'message': f"Use of undeclared identifier '{ident_name}'",
                    'line': line,
                    'severity': 'error'
                })
            else:
                self.symbol_table.mark_used(ident_name, self.current_scope)
                if sym and not sym.get('initialized', False):
                    self.errors.append({
                        'type': 'Semantic Warning',
                        'message': f"Variable '{ident_name}' may be used uninitialized",
                        'line': line,
                        'severity': 'warning'
                    })

            return {'type': 'Identifier', 'value': ident_name, 'line': line}

        return None

    def expect_semicolon(self, line: int, message: str = "Missing ';' at end of statement"):
        curr = self.current_token()
        if curr and curr['value'] == ';':
            self.advance()
            return True
        self.errors.append({
            'type': 'Syntax Error',
            'message': message,
            'line': line,
            'severity': 'error'
        })
        return False

    def check_unused_variables(self):
        """Generates semantic warnings for declared variables that were never used."""
        for sym in self.symbol_table.to_list():
            if not sym.get('is_function') and sym.get('references', 0) == 0 and sym['scope'] != 'global':
                self.errors.append({
                    'type': 'Semantic Warning',
                    'message': f"Unused variable '{sym['name']}' declared at line {sym['line']}",
                    'line': sym['line'],
                    'severity': 'warning'
                })


# ============================================================================
# PHASE 4: INTERMEDIATE CODE GENERATION (THREE-ADDRESS CODE / QUADRUPLES)
# ============================================================================

class TACGenerator:
    """
    Generates Three-Address Code (TAC) and Quadruples from the parsed AST.
    Standard Dragon Book format: result = arg1 op arg2
    """
    def __init__(self):
        self.temp_count = 0
        self.label_count = 0
        self.instructions: List[str] = []
        self.quadruples: List[Dict[str, str]] = []

    def new_temp(self) -> str:
        t = f"t{self.temp_count}"
        self.temp_count += 1
        return t

    def new_label(self) -> str:
        lbl = f"L{self.label_count}"
        self.label_count += 1
        return lbl

    def emit(self, op: str, arg1: str, arg2: str, result: str, human_str: str = ""):
        self.quadruples.append({
            'op': op,
            'arg1': arg1,
            'arg2': arg2,
            'result': result
        })
        if human_str:
            self.instructions.append(human_str)
        elif op == '=':
            self.instructions.append(f"{result} = {arg1}")
        elif op in ('+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>='):
            self.instructions.append(f"{result} = {arg1} {op} {arg2}")
        elif op == 'label':
            self.instructions.append(f"{result}:")
        elif op == 'goto':
            self.instructions.append(f"goto {result}")
        elif op == 'if_false':
            self.instructions.append(f"if_false {arg1} goto {result}")
        elif op == 'param':
            self.instructions.append(f"param {arg1}")
        elif op == 'call':
            self.instructions.append(f"{result} = call {arg1}, {arg2}" if result else f"call {arg1}, {arg2}")
        elif op == 'return':
            self.instructions.append(f"return {arg1}" if arg1 else "return")
        else:
            self.instructions.append(f"{result} = {op} {arg1} {arg2}".strip())

    def generate(self, ast: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, str]]]:
        if not ast:
            return [], []
        self.traverse_node(ast)
        return self.instructions, self.quadruples

    def traverse_node(self, node: Any) -> Optional[str]:
        if not isinstance(node, dict):
            return str(node)

        node_type = node.get('type')

        if node_type == 'Program':
            for child in node.get('children', []):
                self.traverse_node(child)
            return None

        elif node_type == 'FunctionDeclaration':
            func_name = node.get('name')
            self.instructions.append(f"\n; --- Function {func_name} ---")
            self.emit('func_start', func_name, '', '')
            if node.get('body'):
                self.traverse_node(node['body'])
            self.emit('func_end', func_name, '', '')
            return None

        elif node_type == 'CompoundStatement':
            for child in node.get('children', []):
                self.traverse_node(child)
            return None

        elif node_type == 'VariableDeclaration':
            var_name = node.get('name')
            if node.get('initialized') and node.get('initial_value'):
                val_res = self.traverse_node(node['initial_value'])
                if val_res:
                    self.emit('=', val_res, '', var_name)
            return None

        elif node_type == 'AssignmentStatement':
            target = node.get('target')
            val_res = self.traverse_node(node.get('value'))
            op = node.get('operator', '=')
            if op == '=':
                self.emit('=', val_res, '', target)
            else:
                bin_op = op.replace('=', '')
                t = self.new_temp()
                self.emit(bin_op, target, val_res, t)
                self.emit('=', t, '', target)
            return target

        elif node_type == 'BinaryExpression':
            left_res = self.traverse_node(node.get('left'))
            right_res = self.traverse_node(node.get('right'))
            op = node.get('operator')
            t = self.new_temp()
            self.emit(op, str(left_res), str(right_res), t)
            return t

        elif node_type == 'UnaryExpression':
            sub_res = self.traverse_node(node.get('operand'))
            op = node.get('operator')
            t = self.new_temp()
            self.emit(op, str(sub_res), '', t, f"{t} = {op}{sub_res}")
            return t

        elif node_type == 'NumericLiteral':
            return str(node.get('value'))

        elif node_type == 'StringLiteral':
            return str(node.get('value'))

        elif node_type == 'Identifier':
            return str(node.get('value'))

        elif node_type == 'FunctionCall':
            func_name = node.get('function_name')
            args = node.get('arguments', [])
            arg_temps = []
            for arg in args:
                res = self.traverse_node(arg)
                arg_temps.append(str(res))
            for arg_t in arg_temps:
                self.emit('param', arg_t, '', '')
            t = self.new_temp() if func_name not in ('printf', 'puts') else ''
            self.emit('call', func_name, str(len(arg_temps)), t)
            return t

        elif node_type == 'ReturnStatement':
            expr_res = ''
            if node.get('expression'):
                expr_res = self.traverse_node(node['expression'])
            self.emit('return', str(expr_res), '', '')
            return None

        elif node_type == 'IfStatement':
            cond_res = self.traverse_node(node.get('condition'))
            lbl_else = self.new_label()
            lbl_end = self.new_label()

            self.emit('if_false', str(cond_res), '', lbl_else)
            self.traverse_node(node.get('then_branch'))

            if node.get('else_branch'):
                self.emit('goto', '', '', lbl_end)
                self.emit('label', '', '', lbl_else)
                self.traverse_node(node.get('else_branch'))
                self.emit('label', '', '', lbl_end)
            else:
                self.emit('label', '', '', lbl_else)
            return None

        elif node_type == 'WhileStatement':
            lbl_start = self.new_label()
            lbl_exit = self.new_label()

            self.emit('label', '', '', lbl_start)
            cond_res = self.traverse_node(node.get('condition'))
            self.emit('if_false', str(cond_res), '', lbl_exit)
            self.traverse_node(node.get('body'))
            self.emit('goto', '', '', lbl_start)
            self.emit('label', '', '', lbl_exit)
            return None

        return None


# ============================================================================
# PHASE 5: CODE OPTIMIZATION (CONSTANT FOLDING & DEAD CODE ELIMINATION)
# ============================================================================

def optimize_tac(instructions: List[str], quadruples: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Comprehensive Multi-Pass Machine-Independent Code Optimizer:
    1. Constant Folding: evaluates compile-time constant arithmetic.
    2. Constant & Copy Propagation: propagates known constant values and copies.
    3. Strength Reduction: replaces high-cost operations (e.g. x * 2 -> x + x, x * 4 -> x << 2, x / 2 -> x >> 1, x % 2 -> x & 1).
    4. Algebraic Transformations: applies mathematical identities (x + 0 -> x, x * 1 -> x, x * 0 -> 0, x - x -> 0, etc.).
    5. Common Subexpression Elimination (CSE): reuses previously evaluated subexpressions.
    6. Dead Code Elimination (DCE): prunes unreachable code after unconditional returns and dead temporary variable stores.
    """
    import math

    optimized_quads = []
    constants: Dict[str, int] = {}
    copy_map: Dict[str, str] = {}
    available_exprs: Dict[Tuple[str, str, str], str] = {}
    logs: List[str] = []
    categories = {
        'constant_folding': 0,
        'algebraic_transformations': 0,
        'strength_reduction': 0,
        'common_subexpressions': 0,
        'dead_code_elimination': 0,
        'copy_propagation': 0
    }

    # Pass 1: Dead Code Elimination (Unreachable instructions following unconditional jumps)
    reachable_quads = []
    unreachable = False
    for q in quadruples:
        op = q['op']
        arg1 = q['arg1']
        arg2 = q['arg2']
        res = q['result']

        if unreachable:
            if op in ('label', 'func_start', 'func_end'):
                unreachable = False
            else:
                logs.append(f"Dead Code Elimination: removed unreachable instruction '{op} {arg1} {arg2}'.")
                categories['dead_code_elimination'] += 1
                continue

        reachable_quads.append(q)
        if op in ('return', 'goto'):
            unreachable = True

    # Pass 2: Main Optimization Pipeline
    for q in reachable_quads:
        op = q['op']
        arg1 = q['arg1']
        arg2 = q['arg2']
        res = q['result']

        if op in ('label', 'func_start', 'func_end', 'goto', 'if_false', 'param', 'call', 'return'):
            if op in ('label', 'call', 'func_start'):
                available_exprs.clear()

            if arg1 in copy_map:
                arg1 = copy_map[arg1]
            if arg1 in constants:
                arg1 = str(constants[arg1])
            optimized_quads.append({'op': op, 'arg1': arg1, 'arg2': arg2, 'result': res})
            continue

        # Check Copy / Constant Propagation on arguments
        orig_arg1, orig_arg2 = arg1, arg2
        if arg1 in copy_map:
            arg1 = copy_map[arg1]
            logs.append(f"Copy Propagation: substituted '{orig_arg1}' with copy '{arg1}'")
            categories['copy_propagation'] += 1
        if arg1 in constants:
            arg1 = str(constants[arg1])
            logs.append(f"Constant Propagation: replaced '{orig_arg1}' with known constant '{arg1}'")
            categories['copy_propagation'] += 1

        if arg2 in copy_map:
            arg2 = copy_map[arg2]
            logs.append(f"Copy Propagation: substituted '{orig_arg2}' with copy '{arg2}'")
            categories['copy_propagation'] += 1
        if arg2 in constants:
            arg2 = str(constants[arg2])
            logs.append(f"Constant Propagation: replaced '{orig_arg2}' with known constant '{arg2}'")
            categories['copy_propagation'] += 1

        is_const1 = arg1.lstrip('-').isdigit() if arg1 else False
        is_const2 = arg2.lstrip('-').isdigit() if arg2 else False
        val1 = int(arg1) if is_const1 else None
        val2 = int(arg2) if is_const2 else None

        # ----------------------------------------------------
        # 1. CONSTANT FOLDING
        # ----------------------------------------------------
        if op in ('+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=') and is_const1 and is_const2:
            folded_val = None
            try:
                if op == '+': folded_val = val1 + val2
                elif op == '-': folded_val = val1 - val2
                elif op == '*': folded_val = val1 * val2
                elif op == '/' and val2 != 0: folded_val = val1 // val2
                elif op == '%' and val2 != 0: folded_val = val1 % val2
                elif op == '==': folded_val = 1 if val1 == val2 else 0
                elif op == '!=': folded_val = 1 if val1 != val2 else 0
                elif op == '<': folded_val = 1 if val1 < val2 else 0
                elif op == '>': folded_val = 1 if val1 > val2 else 0
                elif op == '<=': folded_val = 1 if val1 <= val2 else 0
                elif op == '>=': folded_val = 1 if val1 >= val2 else 0
            except Exception:
                pass

            if folded_val is not None:
                constants[res] = folded_val
                logs.append(f"Constant Folding: folded compile-time arithmetic '{val1} {op} {val2}' -> {folded_val}")
                categories['constant_folding'] += 1
                optimized_quads.append({
                    'op': '=',
                    'arg1': str(folded_val),
                    'arg2': '',
                    'result': res
                })
                continue

        # ----------------------------------------------------
        # 2. STRENGTH REDUCTION
        # (Replacing high-cycle operations with cheap equivalents)
        # e.g. x * 2 -> x + x, x * 4 -> x << 2, x / 2 -> x >> 1, x % 2 -> x & 1
        # ----------------------------------------------------
        strength_reduced = False
        if op == '*':
            # Multiplied by 2: replace with addition x + x (lower ALU cycle latency)
            if arg2 == '2':
                logs.append(f"Strength Reduction: replaced expensive multiplication '{arg1} * 2' with addition '{arg1} + {arg1}'")
                categories['strength_reduction'] += 1
                optimized_quads.append({
                    'op': '+',
                    'arg1': arg1,
                    'arg2': arg1,
                    'result': res
                })
                strength_reduced = True
            elif arg1 == '2':
                logs.append(f"Strength Reduction: replaced expensive multiplication '2 * {arg2}' with addition '{arg2} + {arg2}'")
                categories['strength_reduction'] += 1
                optimized_quads.append({
                    'op': '+',
                    'arg1': arg2,
                    'arg2': arg2,
                    'result': res
                })
                strength_reduced = True
            elif is_const2 and val2 and val2 > 2 and (val2 & (val2 - 1)) == 0:
                shift = int(math.log2(val2))
                logs.append(f"Strength Reduction: replaced multiplication '{arg1} * {val2}' with bitwise left-shift '{arg1} << {shift}'")
                categories['strength_reduction'] += 1
                optimized_quads.append({
                    'op': '<<',
                    'arg1': arg1,
                    'arg2': str(shift),
                    'result': res
                })
                strength_reduced = True

        elif op == '/':
            if is_const2 and val2 and val2 > 0 and (val2 & (val2 - 1)) == 0:
                shift = int(math.log2(val2))
                logs.append(f"Strength Reduction: replaced division '{arg1} / {val2}' with bitwise right-shift '{arg1} >> {shift}'")
                categories['strength_reduction'] += 1
                optimized_quads.append({
                    'op': '>>',
                    'arg1': arg1,
                    'arg2': str(shift),
                    'result': res
                })
                strength_reduced = True

        elif op == '%':
            if is_const2 and val2 and val2 > 0 and (val2 & (val2 - 1)) == 0:
                mask = val2 - 1
                logs.append(f"Strength Reduction: replaced modulo '{arg1} % {val2}' with bitwise mask '{arg1} & {mask}'")
                categories['strength_reduction'] += 1
                optimized_quads.append({
                    'op': '&',
                    'arg1': arg1,
                    'arg2': str(mask),
                    'result': res
                })
                strength_reduced = True

        if strength_reduced:
            continue

        # ----------------------------------------------------
        # 3. ALGEBRAIC TRANSFORMATIONS & IDENTITIES
        # (x + 0 -> x, x * 1 -> x, x * 0 -> 0, x - x -> 0, etc.)
        # ----------------------------------------------------
        algebraic_applied = False
        if op == '+':
            if arg2 == '0':
                logs.append(f"Algebraic Transformation: '{arg1} + 0' simplified to '{arg1}' (Additive Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg1, 'arg2': '', 'result': res})
                copy_map[res] = arg1
                algebraic_applied = True
            elif arg1 == '0':
                logs.append(f"Algebraic Transformation: '0 + {arg2}' simplified to '{arg2}' (Additive Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg2, 'arg2': '', 'result': res})
                copy_map[res] = arg2
                algebraic_applied = True

        elif op == '-':
            if arg2 == '0':
                logs.append(f"Algebraic Transformation: '{arg1} - 0' simplified to '{arg1}' (Additive Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg1, 'arg2': '', 'result': res})
                copy_map[res] = arg1
                algebraic_applied = True
            elif arg1 == arg2:
                logs.append(f"Algebraic Transformation: '{arg1} - {arg1}' simplified to 0 (Self-subtraction)")
                categories['algebraic_transformations'] += 1
                constants[res] = 0
                optimized_quads.append({'op': '=', 'arg1': '0', 'arg2': '', 'result': res})
                algebraic_applied = True

        elif op == '*':
            if arg2 == '1':
                logs.append(f"Algebraic Transformation: '{arg1} * 1' simplified to '{arg1}' (Multiplicative Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg1, 'arg2': '', 'result': res})
                copy_map[res] = arg1
                algebraic_applied = True
            elif arg1 == '1':
                logs.append(f"Algebraic Transformation: '1 * {arg2}' simplified to '{arg2}' (Multiplicative Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg2, 'arg2': '', 'result': res})
                copy_map[res] = arg2
                algebraic_applied = True
            elif arg2 == '0' or arg1 == '0':
                logs.append(f"Algebraic Transformation: multiplication by zero simplified to 0 (Zero Annihilator)")
                categories['algebraic_transformations'] += 1
                constants[res] = 0
                optimized_quads.append({'op': '=', 'arg1': '0', 'arg2': '', 'result': res})
                algebraic_applied = True

        elif op == '/':
            if arg2 == '1':
                logs.append(f"Algebraic Transformation: '{arg1} / 1' simplified to '{arg1}' (Division Identity)")
                categories['algebraic_transformations'] += 1
                optimized_quads.append({'op': '=', 'arg1': arg1, 'arg2': '', 'result': res})
                copy_map[res] = arg1
                algebraic_applied = True
            elif arg1 == '0':
                logs.append(f"Algebraic Transformation: '0 / {arg2}' simplified to 0")
                categories['algebraic_transformations'] += 1
                constants[res] = 0
                optimized_quads.append({'op': '=', 'arg1': '0', 'arg2': '', 'result': res})
                algebraic_applied = True
            elif arg1 == arg2:
                logs.append(f"Algebraic Transformation: '{arg1} / {arg1}' simplified to 1 (Self-division)")
                categories['algebraic_transformations'] += 1
                constants[res] = 1
                optimized_quads.append({'op': '=', 'arg1': '1', 'arg2': '', 'result': res})
                algebraic_applied = True

        if algebraic_applied:
            continue

        # ----------------------------------------------------
        # 4. COMMON SUBEXPRESSION ELIMINATION (CSE)
        # ----------------------------------------------------
        if op in ('+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>='):
            expr_key = (op, arg1, arg2)
            comm_key = (op, arg2, arg1) if op in ('+', '*', '==', '!=') else None

            if expr_key in available_exprs:
                prev_temp = available_exprs[expr_key]
                logs.append(f"Common Subexpression Elimination (CSE): reused computation '{prev_temp}' for '{arg1} {op} {arg2}'")
                categories['common_subexpressions'] += 1
                optimized_quads.append({'op': '=', 'arg1': prev_temp, 'arg2': '', 'result': res})
                copy_map[res] = prev_temp
                continue
            elif comm_key and comm_key in available_exprs:
                prev_temp = available_exprs[comm_key]
                logs.append(f"Common Subexpression Elimination (CSE): reused commutative computation '{prev_temp}' for '{arg1} {op} {arg2}'")
                categories['common_subexpressions'] += 1
                optimized_quads.append({'op': '=', 'arg1': prev_temp, 'arg2': '', 'result': res})
                copy_map[res] = prev_temp
                continue
            else:
                available_exprs[expr_key] = res

        # Assignment recording
        if op == '=':
            if is_const1:
                constants[res] = val1
            else:
                copy_map[res] = arg1

        optimized_quads.append({'op': op, 'arg1': arg1, 'arg2': arg2, 'result': res})

    # Pass 3: Dead Store Elimination (Prune dead temporary variables)
    used_vars = set()
    for q in optimized_quads:
        if q['arg1']: used_vars.add(q['arg1'])
        if q['arg2']: used_vars.add(q['arg2'])
        if q['op'] in ('param', 'return') and q['arg1']:
            used_vars.add(q['arg1'])

    final_quads = []
    for q in optimized_quads:
        # If an assignment to a temp variable t0, t1... is never read anywhere
        if q['op'] == '=' and q['result'].startswith('t') and q['result'] not in used_vars:
            logs.append(f"Dead Code Elimination: pruned dead temporary assignment '{q['result']} = {q['arg1']}'")
            categories['dead_code_elimination'] += 1
            continue
        final_quads.append(q)

    # Re-generate clean human-readable instructions
    optimized_instructions = []
    for q in final_quads:
        op = q['op']
        arg1 = q['arg1']
        arg2 = q['arg2']
        res = q['result']

        if op == '=':
            optimized_instructions.append(f"{res} = {arg1}")
        elif op in ('+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '<<', '>>', '&', '|', '^'):
            optimized_instructions.append(f"{res} = {arg1} {op} {arg2}")
        elif op == 'label':
            optimized_instructions.append(f"{res}:")
        elif op == 'goto':
            optimized_instructions.append(f"goto {res}")
        elif op == 'if_false':
            optimized_instructions.append(f"if_false {arg1} goto {res}")
        elif op == 'param':
            optimized_instructions.append(f"param {arg1}")
        elif op == 'call':
            optimized_instructions.append(f"{res} = call {arg1}, {arg2}" if res else f"call {arg1}, {arg2}")
        elif op == 'return':
            optimized_instructions.append(f"return {arg1}" if arg1 else "return")
        elif op == 'func_start':
            optimized_instructions.append(f"\n; --- Function {arg1} (Optimized) ---")
        elif op != 'func_end':
            optimized_instructions.append(f"{res} = {op} {arg1} {arg2}".strip())

    reduction_pct = 0.0
    if len(quadruples) > 0:
        reduction_pct = round(((len(quadruples) - len(final_quads)) / len(quadruples)) * 100, 1)

    return {
        'optimized_instructions': optimized_instructions,
        'optimized_quadruples': final_quads,
        'logs': logs,
        'categories': categories,
        'reduction_pct': max(0.0, reduction_pct)
    }


# ============================================================================
# PHASE 6: ADAPTIVE ERROR RECOVERY & AUTOMATED FIX ENGINE
# ============================================================================

def generate_adaptive_fixes(code: str, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligent Adaptive Error Recovery:
    Analyzes compiler errors and generates exact line-by-line patch objects
    that can be applied with a single click.
    """
    fixes = []
    lines = code.splitlines()

    # 1. Missing #include <stdio.h>
    has_printf_scanf = any(re.search(r'\b(printf|scanf|puts|gets)\b', l) for l in lines)
    has_stdio = any('#include' in l and 'stdio.h' in l for l in lines)
    if has_printf_scanf and not has_stdio:
        fixes.append({
            'description': 'Add #include <stdio.h> to provide declarations for standard I/O functions (printf, scanf)',
            'confidence': 0.98,
            'category': 'Header Inclusion Recovery',
            'edit': {
                'type': 'insert',
                'line': 1,
                'content': '#include <stdio.h>\n'
            }
        })

    # 2. Missing & in scanf: scanf("%d", x) -> scanf("%d", &x)
    for i, line in enumerate(lines, start=1):
        m = re.search(r'scanf\s*\(\s*("[^"]*")\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)', line)
        if m:
            fmt, var = m.group(1), m.group(2)
            if not f'&{var}' in line:
                fixed_line = re.sub(
                    r'scanf\s*\(\s*("[^"]*")\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)',
                    rf'scanf(\1, &\2)',
                    line
                )
                fixes.append({
                    'description': f"Add address-of operator '&' before '{var}' in scanf call on line {i}",
                    'confidence': 0.95,
                    'category': 'Pointer Recovery',
                    'edit': {
                        'type': 'replace',
                        'line': i,
                        'original': line,
                        'replacement': fixed_line
                    }
                })

    # 3. Missing Semicolon on statements
    for err in errors:
        msg = err.get('message', '')
        if 'Missing \';\'' in msg or 'Expected \';\'' in msg:
            line_idx = err.get('line')
            if line_idx and 1 <= line_idx <= len(lines):
                orig = lines[line_idx - 1]
                stripped = orig.rstrip()
                if not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}'):
                    fixes.append({
                        'description': f"Insert missing semicolon ';' at the end of line {line_idx}",
                        'confidence': 0.92,
                        'category': 'Phrase-Level Recovery',
                        'edit': {
                            'type': 'replace',
                            'line': line_idx,
                            'original': orig,
                            'replacement': stripped + ';'
                        }
                    })

    # 4. Unmatched closing brace or unclosed opening brace
    brace_open_count = code.count('{')
    brace_close_count = code.count('}')
    if brace_open_count > brace_close_count:
        diff = brace_open_count - brace_close_count
        fixes.append({
            'description': f"Add {diff} missing closing brace '}}' at the end of the file",
            'confidence': 0.90,
            'category': 'Panic-Mode Recovery',
            'edit': {
                'type': 'insert',
                'line': len(lines) + 1,
                'content': '\n' + ('}\n' * diff)
            }
        })

    # 5. Undeclared variable recovery suggestion (e.g. x = 10; without int x;)
    for err in errors:
        m = re.search(r"Use of undeclared identifier '([a-zA-Z_][a-zA-Z0-9_]*)'", err.get('message', ''))
        if m:
            var_name = m.group(1)
            line_no = err.get('line', 1)
            # Find the enclosing function body or insert inside main
            fixes.append({
                'description': f"Declare missing variable 'int {var_name};' before usage on line {line_no}",
                'confidence': 0.82,
                'category': 'Declaration Recovery',
                'edit': {
                    'type': 'insert',
                    'line': line_no,
                    'content': f"    int {var_name} = 0;\n"
                }
            })

    # Deduplicate fixes by description
    seen = set()
    unique_fixes = []
    for f in fixes:
        if f['description'] not in seen:
            seen.add(f['description'])
            unique_fixes.append(f)

    return unique_fixes


# ============================================================================
# PHASE 7: TARGET EXECUTION SIMULATOR
# ============================================================================

def simulate_execution(ast: Dict[str, Any], code: str) -> Optional[str]:
    """
    Simulates standard C runtime execution for basic programs
    (interprets printf statements and basic variable substitutions).
    """
    try:
        output_lines = []
        # Find printfs
        for m in re.finditer(r'printf\s*\(\s*"([^"\\]*(?:\\.[^"\\]*)*)"(?:\s*,\s*([^)]+))?\s*\)\s*;', code):
            fmt = m.group(1)
            args_str = m.group(2)
            # Process escape sequences
            fmt_clean = fmt.replace('\\n', '\n').replace('\\t', '\t')

            if args_str:
                args = [a.strip() for a in args_str.split(',')]
                # Simple integer replacement
                out_str = fmt_clean
                for a in args:
                    # check if a was assigned in code
                    val_match = re.search(rf'\b{re.escape(a)}\s*=\s*(-?\d+)', code)
                    if val_match:
                        out_str = re.sub(r'%d|%i', val_match.group(1), out_str, count=1)
                output_lines.append(out_str)
            else:
                output_lines.append(fmt_clean)

        if output_lines:
            return "".join(output_lines)
        return "Program executed successfully with return code 0 (no stdout output produced)."
    except Exception as e:
        return f"Execution simulation error: {str(e)}"


# ============================================================================
# MASTER COMPILER PIPELINE
# ============================================================================

def run_full_compiler_pipeline(code: str) -> Dict[str, Any]:
    """
    Executes all phases of the compiler:
    1. Lexical Analysis
    2. Syntax & Semantic Analysis
    3. Symbol Table Generation
    4. AST Generation
    5. Intermediate Code Generation (TAC)
    6. Code Optimization
    7. Adaptive Recovery & Fixes
    8. Program Execution Simulation
    """
    # 1. Lexer
    tokens, lex_errors = tokenize(code)

    # 2 & 3. Parser, AST, Semantic, Symbol Table
    analyzer = CParserAndAnalyzer(code, tokens)
    analysis_res = analyzer.analyze()

    all_errors = lex_errors + analysis_res['errors']

    # Filter into actual errors vs warnings
    error_list = [e for e in all_errors if e.get('severity') == 'error']
    warning_list = [e for e in all_errors if e.get('severity') == 'warning']

    # 4. Intermediate Code Generation (TAC)
    tac_gen = TACGenerator()
    tac_instructions, tac_quadruples = tac_gen.generate(analysis_res['ast'])

    # 5. Code Optimization
    opt_res = optimize_tac(tac_instructions, tac_quadruples)

    # 6. Adaptive Fixes
    fixes = generate_adaptive_fixes(code, all_errors)

    # 7. Execution simulation if no fatal syntax errors
    execution_output = None
    if len(error_list) == 0:
        execution_output = simulate_execution(analysis_res['ast'], code)

    status = 'success' if len(error_list) == 0 else 'error'
    msg = 'Compilation successful!' if status == 'success' else f'Compilation failed with {len(error_list)} error(s)'

    return {
        'status': status,
        'message': msg,
        'tokens': tokens,
        'ast': analysis_res['ast'],
        'symbol_table': analysis_res['symbol_table'],
        'errors': all_errors,
        'error_count': len(error_list),
        'warning_count': len(warning_list),
        'tac': {
            'instructions': tac_instructions,
            'quadruples': tac_quadruples
        },
        'optimization': {
            'optimized_instructions': opt_res['optimized_instructions'],
            'optimized_quadruples': opt_res['optimized_quadruples'],
            'logs': opt_res['logs'],
            'reduction_pct': opt_res['reduction_pct'],
            'categories': opt_res.get('categories', {})
        },
        'fixes': fixes,
        'execution_output': execution_output
    }

