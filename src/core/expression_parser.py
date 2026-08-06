#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import math
import json
import re
import sys
import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dataclasses import dataclass, field
from typing import Any, List, Optional, Dict, Tuple, Union

from src.utils.error_codes import ErrorCode
from src.utils.errors import AppError, ValidationError


@dataclass
class NumberNode:
    value: float


@dataclass
class ConstantNode:
    name: str


@dataclass
class VariableNode:
    name: str


@dataclass
class UnaryOpNode:
    op: str
    operand: Any


@dataclass
class BinaryOpNode:
    op: str
    left: Any
    right: Any


@dataclass
class CallNode:
    name: str
    args: List[Any]


@dataclass
class ConditionalNode:
    cond: Any
    true_expr: Any
    false_expr: Any


@dataclass
class ListLiteralNode:
    items: List[Any]


@dataclass
class MatLiteralNode:
    rows: List[ListLiteralNode]


_UNARY_FUNCS = {
    'abs', 'negate', 'sign',
    'sqrt', 'cbrt', 'exp', 'log', 'log2', 'log10',
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
    'sinh', 'cosh', 'tanh',
    'transpose', 'det', 'inv', 'norm', 'sum', 'mean', 'stddev',
    'min', 'max', 'median'
}

_BINARY_FUNCS = {'pow', 'dot'}

_MULTI_ARG_FUNCS = {
    'pow', 'log', 'clamp', 'lerp', 'ifelse',
    'vec', 'mat', 'transpose', 'det', 'inv', 'dot', 'norm',
    'sum', 'mean', 'stddev', 'min', 'max', 'median'
}


class Parser:
    def __init__(self, s: str):
        self.s = s
        self.pos = 0

    def peek(self, offset: int = 0) -> Optional[str]:
        idx = self.pos + offset
        if idx < len(self.s):
            return self.s[idx]
        return None

    def error(self, msg: str, suggestion: str = ""):
        pos = self.pos
        original = self.s
        pointer = "-" * pos + "^"
        display_original = original if original else "(空字符串)"
        error_msg = (
            f"语法错误：{msg}，位置 {pos}\n"
            f"原表达式: {display_original}\n"
            f"          {pointer}\n"
        )
        if suggestion:
            error_msg += f"建议：{suggestion}"
        raise ValidationError(
            ErrorCode.E_VAL_INVALID_ARG,
            error_msg,
            details={
                "position": pos,
                "expression": original,
                "message": msg,
            },
            module="src.core.expression_parser",
        )

    def skip_ws(self):
        while self.pos < len(self.s) and self.s[self.pos] in ' \t\r\n':
            self.pos += 1

    def expect(self, ch: str, msg: str = "", suggestion: str = ""):
        self.skip_ws()
        if self.peek() == ch:
            self.pos += 1
            return True
        expected_msg = msg or f"期望字符 '{ch}'"
        sug = suggestion or f"检查是否缺少 '{ch}'"
        self.error(expected_msg, sug)
        return False

    def match(self, ch: str) -> bool:
        self.skip_ws()
        if self.peek() == ch:
            self.pos += 1
            return True
        return False

    def parse_expr(self):
        return self.parse_ternary()

    def parse_ternary(self):
        cond = self.parse_or()
        self.skip_ws()
        if self.match('?'):
            true_expr = self.parse_expr()
            self.expect(':', "三目运算符缺少 ':'", "检查 a?b:c 格式是否完整")
            false_expr = self.parse_ternary()
            return ConditionalNode(cond, true_expr, false_expr)
        return cond

    def parse_or(self):
        left = self.parse_and()
        while True:
            self.skip_ws()
            if self.peek() == '|' and self.peek(1) == '|':
                self.pos += 2
                right = self.parse_and()
                left = BinaryOpNode('||', left, right)
            else:
                break
        return left

    def parse_and(self):
        left = self.parse_cmp()
        while True:
            self.skip_ws()
            if self.peek() == '&' and self.peek(1) == '&':
                self.pos += 2
                right = self.parse_cmp()
                left = BinaryOpNode('&&', left, right)
            else:
                break
        return left

    def parse_cmp(self):
        left = self.parse_add()
        while True:
            self.skip_ws()
            op = None
            if self.peek() == '<' and self.peek(1) == '=':
                op = '<='
                self.pos += 2
            elif self.peek() == '>' and self.peek(1) == '=':
                op = '>='
                self.pos += 2
            elif self.peek() == '=' and self.peek(1) == '=':
                op = '=='
                self.pos += 2
            elif self.peek() == '!' and self.peek(1) == '=':
                op = '!='
                self.pos += 2
            elif self.peek() == '<':
                op = '<'
                self.pos += 1
            elif self.peek() == '>':
                op = '>'
                self.pos += 1
            else:
                break
            right = self.parse_add()
            left = BinaryOpNode(op, left, right)
        return left

    def parse_add(self):
        left = self.parse_mul()
        while True:
            self.skip_ws()
            ch = self.peek()
            if ch == '+':
                self.pos += 1
                right = self.parse_mul()
                left = BinaryOpNode('+', left, right)
            elif ch == '-':
                self.pos += 1
                right = self.parse_mul()
                left = BinaryOpNode('-', left, right)
            else:
                break
        return left

    def parse_mul(self):
        left = self.parse_unary()
        while True:
            self.skip_ws()
            ch = self.peek()
            if ch == '*':
                self.pos += 1
                right = self.parse_unary()
                left = BinaryOpNode('*', left, right)
            elif ch == '/':
                self.pos += 1
                right = self.parse_unary()
                left = BinaryOpNode('/', left, right)
            elif ch == '%':
                self.pos += 1
                right = self.parse_unary()
                left = BinaryOpNode('%', left, right)
            else:
                break
        return left

    def parse_unary(self):
        self.skip_ws()
        ch = self.peek()
        if ch == '+':
            self.pos += 1
            operand = self.parse_unary()
            return UnaryOpNode('+', operand)
        elif ch == '-':
            self.pos += 1
            operand = self.parse_unary()
            return UnaryOpNode('-', operand)
        return self.parse_pow()

    def parse_pow(self):
        base = self.parse_call()
        self.skip_ws()
        if self.peek() == '^':
            self.pos += 1
            exponent = self.parse_unary()
            return BinaryOpNode('^', base, exponent)
        return base

    def parse_call(self):
        self.skip_ws()
        ch = self.peek()

        if ch == '(':
            self.pos += 1
            expr = self.parse_expr()
            self.expect(')', "括号未闭合", "检查括号/函数参数是否完整")
            return expr

        if ch == '[':
            return self.parse_list()

        if ch is not None and (ch.isdigit() or ch == '.'):
            return self.parse_number()

        if ch is not None and (ch.isalpha() or ch == '_'):
            ident = self.parse_identifier()
            self.skip_ws()
            if self.peek() == '(':
                self.pos += 1
                args = []
                self.skip_ws()
                if self.peek() != ')':
                    args.append(self.parse_expr())
                    while True:
                        self.skip_ws()
                        if self.match(','):
                            args.append(self.parse_expr())
                        else:
                            break
                self.expect(')', f"函数 '{ident}' 的括号未闭合", "检查函数参数是否完整")
                return CallNode(ident, args)
            else:
                if ident == 'pi' or ident == 'e':
                    return ConstantNode(ident)
                return VariableNode(ident)

        if ch is None:
            self.error("表达式意外结束", "检查表达式是否完整")
        else:
            self.error(f"意外的字符 '{ch}'", "检查语法是否正确")

    def parse_list(self):
        self.expect('[', "缺少 '['", "检查向量字面量格式")
        items = []
        self.skip_ws()
        if self.peek() != ']':
            items.append(self.parse_expr())
            while True:
                self.skip_ws()
                if self.match(','):
                    items.append(self.parse_expr())
                else:
                    break
        self.expect(']', "向量字面量缺少 ']'", "检查 [a,b,c] 格式是否完整")
        list_node = ListLiteralNode(items)
        if len(items) > 0 and all(isinstance(it, ListLiteralNode) for it in items):
            cols = len(items[0].items) if items else 0
            for i, row in enumerate(items):
                if not isinstance(row, ListLiteralNode):
                    self.error(f"矩阵第 {i} 行不是向量字面量", "矩阵字面量应为 [[a,b],[c,d]] 格式")
                if len(row.items) != cols:
                    self.error(
                        f"矩阵第 {i} 行有 {len(row.items)} 列，期望 {cols} 列",
                        "矩阵每行的列数必须一致"
                    )
            return MatLiteralNode(items)
        return list_node

    def parse_number(self):
        start = self.pos
        has_dot = False
        has_exp = False

        while self.pos < len(self.s):
            ch = self.s[self.pos]
            if ch.isdigit():
                self.pos += 1
            elif ch == '.' and not has_dot and not has_exp:
                has_dot = True
                self.pos += 1
            elif (ch == 'e' or ch == 'E') and not has_exp:
                has_exp = True
                self.pos += 1
                if self.pos < len(self.s) and (self.s[self.pos] == '+' or self.s[self.pos] == '-'):
                    self.pos += 1
            else:
                break

        num_str = self.s[start:self.pos]
        if num_str == '.' or not num_str:
            self.error("无效的数字格式", "检查数字书写是否正确")
        try:
            value = float(num_str)
        except ValueError:
            self.error(f"无法解析数字 '{num_str}'", "检查数字格式")
        return NumberNode(value)

    def parse_identifier(self) -> str:
        start = self.pos
        while self.pos < len(self.s):
            ch = self.s[self.pos]
            if ch.isalnum() or ch == '_':
                self.pos += 1
            else:
                break
        return self.s[start:self.pos]


def parse_expression(s: str):
    if not isinstance(s, str):
        raise ValidationError(
            ErrorCode.E_VAL_INVALID_ARG,
            "表达式必须是字符串类型",
            module="src.core.expression_parser",
        )
    parser = Parser(s)
    parser.skip_ws()
    if parser.pos >= len(s):
        parser.error("表达式为空", "请输入有效的表达式")
    result = parser.parse_expr()
    parser.skip_ws()
    if parser.pos < len(s):
        parser.error(f"意外的尾随字符 '{s[parser.pos]}'", "检查表达式是否完整")
    return result


def compile_ast_to_graph(engine, ast_node, variables=None):
    variables = variables or {}

    g = engine.Graph()

    def value_to_node(value):
        if isinstance(value, (int, float)):
            n = engine.Number(float(value))
            g.add_node(n)
            return n, 0
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], list):
            rows = len(value)
            cols = len(value[0])
            flat = []
            for row in value:
                if not isinstance(row, list) or len(row) != cols:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"变量矩阵格式错误，第 {len(flat)//cols} 行列数不一致",
                        module="src.core.expression_parser",
                    )
                flat.extend(row)
            nodes = []
            for v in flat:
                nn = engine.Number(float(v))
                g.add_node(nn)
                nodes.append(nn)
            mat = engine.MatCreate(rows, cols)
            mat_idx = g.add_node(mat)
            for i, nn in enumerate(nodes):
                g.connect(g.nodes.index(nn), 0, mat_idx, i)
            return mat, 0
        elif isinstance(value, list):
            nodes = []
            for v in value:
                nn = engine.Number(float(v))
                g.add_node(nn)
                nodes.append(nn)
            vec = engine.VecCreate(len(value))
            vec_idx = g.add_node(vec)
            for i, nn in enumerate(nodes):
                g.connect(g.nodes.index(nn), 0, vec_idx, i)
            return vec, 0
        else:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"不支持的变量值类型: {type(value)}",
                module="src.core.expression_parser",
            )

    def compile_node(node):
        if isinstance(node, NumberNode):
            n = engine.Number(node.value)
            g.add_node(n)
            return n, 0

        elif isinstance(node, ConstantNode):
            if node.name == 'pi':
                n = engine.Number(math.pi)
            elif node.name == 'e':
                n = engine.Number(math.e)
            else:
                raise ValidationError(
                    ErrorCode.E_VAL_INVALID_ARG,
                    f"未知常量: {node.name}",
                    module="src.core.expression_parser",
                )
            g.add_node(n)
            return n, 0

        elif isinstance(node, VariableNode):
            if node.name not in variables:
                raise ValidationError(
                    ErrorCode.E_VAL_INVALID_ARG,
                    f"未定义的变量: {node.name}",
                    details={"variable": node.name},
                    module="src.core.expression_parser",
                )
            return value_to_node(variables[node.name])

        elif isinstance(node, UnaryOpNode):
            operand_node, operand_out = compile_node(node.operand)
            operand_idx = g.nodes.index(operand_node)
            op = node.op

            if op == '-':
                result = engine.Negate()
            elif op == '+':
                return operand_node, operand_out
            elif op == 'abs':
                result = engine.Abs()
            elif op == 'negate':
                result = engine.Negate()
            elif op == 'sqrt':
                result = engine.Sqrt()
            elif op == 'cbrt':
                result = engine.Cbrt()
            elif op == 'exp':
                result = engine.Exp()
            elif op == 'log':
                result = engine.Log(math.e)
            elif op == 'log2':
                result = engine.Log2()
            elif op == 'log10':
                result = engine.Log10()
            elif op == 'sin':
                result = engine.Sin()
            elif op == 'cos':
                result = engine.Cos()
            elif op == 'tan':
                result = engine.Tan()
            elif op == 'asin':
                result = engine.Asin()
            elif op == 'acos':
                result = engine.Acos()
            elif op == 'atan':
                result = engine.Atan()
            elif op == 'sinh':
                result = engine.Sinh()
            elif op == 'cosh':
                result = engine.Cosh()
            elif op == 'tanh':
                result = engine.Tanh()
            elif op == 'sign':
                zero = engine.Number(0.0)
                g.add_node(zero)
                zero_idx = g.nodes.index(zero)
                cmp_gt = None
                cmp_lt = None
                if_node = engine.If()
                if_idx = g.add_node(if_node)
                one = engine.Number(1.0)
                g.add_node(one)
                one_idx = g.nodes.index(one)
                neg_one = engine.Number(-1.0)
                g.add_node(neg_one)
                neg_one_idx = g.nodes.index(neg_one)
                sub_gt = engine.Sub()
                g.add_node(sub_gt)
                sub_gt_idx = g.nodes.index(sub_gt)
                g.connect(operand_idx, operand_out, sub_gt_idx, 0)
                g.connect(zero_idx, 0, sub_gt_idx, 1)
                cmp_gt = engine.GreaterThan() if hasattr(engine, 'GreaterThan') else None
                if cmp_gt is None:
                    cmp_gt = engine._cppyy.gbl.nodecalc.GreaterThan() if hasattr(engine._cppyy.gbl.nodecalc, 'GreaterThan') else None
                return if_node, 0
            elif op == 'transpose':
                result = engine.MatTranspose()
            elif op == 'det':
                result = engine.MatDet()
            elif op == 'inv':
                result = engine.MatInverse()
            elif op == 'norm':
                result = engine.VecNorm()
            elif op == 'sum':
                result = engine.VecSum()
            elif op in ('mean', 'stddev', 'min', 'max', 'median'):
                class_map = {
                    'mean': engine.Mean,
                    'stddev': engine.StdDev,
                    'min': engine.Min,
                    'max': engine.Max,
                    'median': engine.Median,
                }
                result = class_map[op]()
            else:
                raise ValidationError(
                    ErrorCode.E_VAL_INVALID_ARG,
                    f"未知的一元运算符/函数: {op}",
                    module="src.core.expression_parser",
                )
            result_idx = g.add_node(result)
            g.connect(operand_idx, operand_out, result_idx, 0)
            return result, 0

        elif isinstance(node, BinaryOpNode):
            left_node, left_out = compile_node(node.left)
            right_node, right_out = compile_node(node.right)
            left_idx = g.nodes.index(left_node)
            right_idx = g.nodes.index(right_node)
            op = node.op

            op_map = {
                '+': engine.Add,
                '-': engine.Sub,
                '*': engine.Mul,
                '/': engine.Div,
                '%': engine.Mod,
                '^': engine.Pow,
                'dot': engine.VecDot,
            }
            cmp_map = {
                '<': None,
                '<=': None,
                '>': None,
                '>=': None,
                '==': None,
                '!=': None,
            }

            if op in op_map:
                result = op_map[op]()
                result_idx = g.add_node(result)
                g.connect(left_idx, left_out, result_idx, 0)
                g.connect(right_idx, right_out, result_idx, 1)
                return result, 0

            elif op in cmp_map or op in ('&&', '||'):
                one = engine.Number(1.0)
                zero = engine.Number(0.0)
                g.add_node(one)
                g.add_node(zero)
                one_idx = g.nodes.index(one)
                zero_idx = g.nodes.index(zero)

                if op == '<':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(left_idx, left_out, sub_idx, 0)
                    g.connect(right_idx, right_out, sub_idx, 1)
                    result = engine.LessThanZero() if hasattr(engine, 'LessThanZero') else None
                    if result is None:
                        cond = engine.If()
                        cond_idx = g.add_node(cond)
                        g.connect(sub_idx, 0, cond_idx, 0)
                        g.connect(one_idx, 0, cond_idx, 1)
                        g.connect(zero_idx, 0, cond_idx, 2)
                        return cond, 0
                elif op == '>':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(right_idx, right_out, sub_idx, 0)
                    g.connect(left_idx, left_out, sub_idx, 1)
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(sub_idx, 0, cond_idx, 0)
                    g.connect(one_idx, 0, cond_idx, 1)
                    g.connect(zero_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '<=':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(left_idx, left_out, sub_idx, 0)
                    g.connect(right_idx, right_out, sub_idx, 1)
                    neg = engine.Negate()
                    neg_idx = g.add_node(neg)
                    g.connect(sub_idx, 0, neg_idx, 0)
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(neg_idx, 0, cond_idx, 0)
                    g.connect(zero_idx, 0, cond_idx, 1)
                    g.connect(one_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '>=':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(right_idx, right_out, sub_idx, 0)
                    g.connect(left_idx, left_out, sub_idx, 1)
                    neg = engine.Negate()
                    neg_idx = g.add_node(neg)
                    g.connect(sub_idx, 0, neg_idx, 0)
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(neg_idx, 0, cond_idx, 0)
                    g.connect(zero_idx, 0, cond_idx, 1)
                    g.connect(one_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '==':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(left_idx, left_out, sub_idx, 0)
                    g.connect(right_idx, right_out, sub_idx, 1)
                    abs_node = engine.Abs()
                    abs_idx = g.add_node(abs_node)
                    g.connect(sub_idx, 0, abs_idx, 0)
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(abs_idx, 0, cond_idx, 0)
                    g.connect(zero_idx, 0, cond_idx, 1)
                    g.connect(one_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '!=':
                    sub = engine.Sub()
                    sub_idx = g.add_node(sub)
                    g.connect(left_idx, left_out, sub_idx, 0)
                    g.connect(right_idx, right_out, sub_idx, 1)
                    abs_node = engine.Abs()
                    abs_idx = g.add_node(abs_node)
                    g.connect(sub_idx, 0, abs_idx, 0)
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(abs_idx, 0, cond_idx, 0)
                    g.connect(one_idx, 0, cond_idx, 1)
                    g.connect(zero_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '&&':
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(left_idx, left_out, cond_idx, 0)
                    g.connect(right_idx, right_out, cond_idx, 1)
                    g.connect(zero_idx, 0, cond_idx, 2)
                    return cond, 0
                elif op == '||':
                    cond = engine.If()
                    cond_idx = g.add_node(cond)
                    g.connect(left_idx, left_out, cond_idx, 0)
                    g.connect(left_idx, left_out, cond_idx, 1)
                    g.connect(right_idx, right_out, cond_idx, 2)
                    return cond, 0
                return one, 0

            else:
                raise ValidationError(
                    ErrorCode.E_VAL_INVALID_ARG,
                    f"未知的二元运算符: {op}",
                    module="src.core.expression_parser",
                )

        elif isinstance(node, CallNode):
            compiled_args = [compile_node(a) for a in node.args]
            name = node.name

            if name == 'pow':
                if len(compiled_args) != 2:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"pow 需要 2 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.Pow()
                result_idx = g.add_node(result)
                g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                g.connect(g.nodes.index(compiled_args[1][0]), compiled_args[1][1], result_idx, 1)
                return result, 0

            elif name == 'log':
                if len(compiled_args) == 1:
                    result = engine.Log(math.e)
                    result_idx = g.add_node(result)
                    g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                    return result, 0
                elif len(compiled_args) == 2:
                    base_node, base_out = compiled_args[0]
                    base_idx = g.nodes.index(base_node)
                    if isinstance(node.args[0], NumberNode):
                        base_val = node.args[0].value
                        result = engine.Log(base_val)
                    else:
                        ln_x = engine.Log(math.e)
                        ln_x_idx = g.add_node(ln_x)
                        g.connect(g.nodes.index(compiled_args[1][0]), compiled_args[1][1], ln_x_idx, 0)
                        ln_b = engine.Log(math.e)
                        ln_b_idx = g.add_node(ln_b)
                        g.connect(base_idx, base_out, ln_b_idx, 0)
                        div = engine.Div()
                        div_idx = g.add_node(div)
                        g.connect(ln_x_idx, 0, div_idx, 0)
                        g.connect(ln_b_idx, 0, div_idx, 1)
                        return div, 0
                    result_idx = g.add_node(result)
                    g.connect(g.nodes.index(compiled_args[1][0]), compiled_args[1][1], result_idx, 0)
                    return result, 0
                else:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"log 需要 1 或 2 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )

            elif name == 'clamp':
                if len(compiled_args) != 3:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"clamp 需要 3 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.Clamp()
                result_idx = g.add_node(result)
                for i, (arg_node, arg_out) in enumerate(compiled_args):
                    g.connect(g.nodes.index(arg_node), arg_out, result_idx, i)
                return result, 0

            elif name == 'lerp':
                if len(compiled_args) != 3:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"lerp 需要 3 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.Lerp()
                result_idx = g.add_node(result)
                for i, (arg_node, arg_out) in enumerate(compiled_args):
                    g.connect(g.nodes.index(arg_node), arg_out, result_idx, i)
                return result, 0

            elif name == 'ifelse':
                if len(compiled_args) != 3:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"ifelse 需要 3 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.If()
                result_idx = g.add_node(result)
                for i, (arg_node, arg_out) in enumerate(compiled_args):
                    g.connect(g.nodes.index(arg_node), arg_out, result_idx, i)
                return result, 0

            elif name == 'vec':
                if len(compiled_args) < 1:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"vec 至少需要 1 个参数",
                        module="src.core.expression_parser",
                    )
                result = engine.VecCreate(len(compiled_args))
                result_idx = g.add_node(result)
                for i, (arg_node, arg_out) in enumerate(compiled_args):
                    g.connect(g.nodes.index(arg_node), arg_out, result_idx, i)
                return result, 0

            elif name == 'mat':
                if len(compiled_args) < 3:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"mat 参数格式: mat(rows, cols, e0, e1, ...)",
                        module="src.core.expression_parser",
                    )
                rows_val = node.args[0]
                cols_val = node.args[1]
                if not isinstance(rows_val, NumberNode) or not isinstance(cols_val, NumberNode):
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"mat 的 rows 和 cols 必须是数字字面量",
                        module="src.core.expression_parser",
                    )
                rows = int(rows_val.value)
                cols = int(cols_val.value)
                expected_elems = rows * cols
                actual_elems = len(compiled_args) - 2
                if actual_elems != expected_elems:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"mat 需要 {expected_elems} 个元素，实际 {actual_elems}",
                        module="src.core.expression_parser",
                    )
                result = engine.MatCreate(rows, cols)
                result_idx = g.add_node(result)
                for i in range(expected_elems):
                    arg_node, arg_out = compiled_args[2 + i]
                    g.connect(g.nodes.index(arg_node), arg_out, result_idx, i)
                return result, 0

            elif name in ('transpose', 'det', 'inv'):
                if len(compiled_args) != 1:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"{name} 需要 1 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                class_map = {
                    'transpose': engine.MatTranspose,
                    'det': engine.MatDet,
                    'inv': engine.MatInverse,
                }
                result = class_map[name]()
                result_idx = g.add_node(result)
                g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                return result, 0

            elif name == 'dot':
                if len(compiled_args) != 2:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"dot 需要 2 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.VecDot()
                result_idx = g.add_node(result)
                g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                g.connect(g.nodes.index(compiled_args[1][0]), compiled_args[1][1], result_idx, 1)
                return result, 0

            elif name == 'norm':
                if len(compiled_args) != 1:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"norm 需要 1 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                result = engine.VecNorm()
                result_idx = g.add_node(result)
                g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                return result, 0

            elif name in ('sum', 'mean', 'stddev', 'min', 'max', 'median'):
                if len(compiled_args) != 1:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"{name} 需要 1 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                class_map = {
                    'sum': engine.VecSum if name == 'sum' else engine.Sum,
                    'mean': engine.Mean,
                    'stddev': engine.StdDev,
                    'min': engine.Min,
                    'max': engine.Max,
                    'median': engine.Median,
                }
                result = class_map[name]()
                result_idx = g.add_node(result)
                g.connect(g.nodes.index(compiled_args[0][0]), compiled_args[0][1], result_idx, 0)
                return result, 0

            elif name in ('abs', 'negate', 'sign', 'sqrt', 'cbrt', 'exp',
                         'log2', 'log10', 'sin', 'cos', 'tan', 'asin', 'acos',
                         'atan', 'sinh', 'cosh', 'tanh'):
                if len(compiled_args) != 1:
                    raise ValidationError(
                        ErrorCode.E_VAL_INVALID_ARG,
                        f"{name} 需要 1 个参数，实际 {len(compiled_args)}",
                        module="src.core.expression_parser",
                    )
                fake_unary = UnaryOpNode(name, node.args[0])
                return compile_node(fake_unary)

            else:
                raise ValidationError(
                    ErrorCode.E_VAL_INVALID_ARG,
                    f"未知函数: {name}",
                    details={"function": name},
                    module="src.core.expression_parser",
                )

        elif isinstance(node, ConditionalNode):
            cond_node, cond_out = compile_node(node.cond)
            true_node, true_out = compile_node(node.true_expr)
            false_node, false_out = compile_node(node.false_expr)
            cond_idx = g.nodes.index(cond_node)
            true_idx = g.nodes.index(true_node)
            false_idx = g.nodes.index(false_node)
            result = engine.If()
            result_idx = g.add_node(result)
            g.connect(cond_idx, cond_out, result_idx, 0)
            g.connect(true_idx, true_out, result_idx, 1)
            g.connect(false_idx, false_out, result_idx, 2)
            return result, 0

        elif isinstance(node, ListLiteralNode):
            compiled_items = [compile_node(it) for it in node.items]
            result = engine.VecCreate(len(compiled_items))
            result_idx = g.add_node(result)
            for i, (item_node, item_out) in enumerate(compiled_items):
                g.connect(g.nodes.index(item_node), item_out, result_idx, i)
            return result, 0

        elif isinstance(node, MatLiteralNode):
            rows = len(node.rows)
            cols = len(node.rows[0].items) if rows > 0 else 0
            flat = []
            for row in node.rows:
                for item in row.items:
                    flat.append(compile_node(item))
            result = engine.MatCreate(rows, cols)
            result_idx = g.add_node(result)
            for i, (elem_node, elem_out) in enumerate(flat):
                g.connect(g.nodes.index(elem_node), elem_out, result_idx, i)
            return result, 0

        else:
            raise ValidationError(
                ErrorCode.E_VAL_INVALID_ARG,
                f"未知的 AST 节点类型: {type(node)}",
                module="src.core.expression_parser",
            )

    output_node, output_port = compile_node(ast_node)
    return g, output_node


def evaluate_expression(expression: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    variables = variables or {}
    try:
        from src.core.node_engine import NodeEngine, execute_graph
        engine = NodeEngine()

        ast = parse_expression(expression)
        graph, output_node = compile_ast_to_graph(engine, ast, variables)

        graph_nodes_count = len(graph.nodes)

        execute_graph(graph)

        port = output_node.outputs[0]
        port_type = port.type
        if str(port_type) == "PortType.SCALAR" or int(port_type) == 0:
            value = port.s
        elif str(port_type) == "PortType.VECTOR" or int(port_type) == 1:
            value = list(port.v)
        elif str(port_type) == "PortType.MATRIX" or int(port_type) == 2:
            value = [list(row) for row in port.m]
        else:
            value = port.s

        return {
            "value": value,
            "steps": graph_nodes_count,
            "graph_nodes": graph_nodes_count,
        }

    except AppError:
        raise
    except Exception as e:
        raise AppError(
            ErrorCode.E_VALIDATION_MATH_ERROR,
            f"表达式计算错误: {str(e)}",
            details={"expression": expression},
            cause=e,
            module="src.core.expression_parser",
        ) from e


if __name__ == "__main__":
    print("Running AST parse tests...")

    def test_parse(expr, desc=""):
        try:
            result = parse_expression(expr)
            print(f"  PASS: {desc or expr}")
            return result, True
        except AppError as e:
            print(f"  UNEXPECTED ERROR for {desc or expr}: {e.message}")
            return None, False

    def test_parse_fail(expr, desc=""):
        try:
            result = parse_expression(expr)
            print(f"  FAIL (expected error): {desc or expr}")
            return None, False
        except AppError as e:
            print(f"  PASS (correctly raised): {desc or expr}")
            return None, True

    all_passed = True

    r, ok = test_parse("sin(pi/2) + sqrt(16)", "sin(pi/2) + sqrt(16)")
    all_passed = all_passed and ok

    r, ok = test_parse("(1+2)*(3-4)/5", "(1+2)*(3-4)/5")
    all_passed = all_passed and ok

    r, ok = test_parse("[[1,2],[3,4]]", "2x2 matrix literal")
    if ok and isinstance(r, MatLiteralNode):
        print(f"    -> MatLiteralNode with {len(r.rows)} rows, "
              f"{len(r.rows[0].items) if r.rows else 0} cols")
    elif ok:
        print(f"    -> WARNING: expected MatLiteralNode, got {type(r).__name__}")

    r, ok = test_parse_fail("sin(pi", "sin(pi (unclosed paren)")
    all_passed = all_passed and ok

    r, ok = test_parse_fail("1 + ) 2", "1 + ) 2 (unexpected paren)")
    all_passed = all_passed and ok

    r, ok = test_parse_fail("", "empty expression")
    all_passed = all_passed and ok

    print()
    r, ok = test_parse("1 + 2 * 3", "precedence: 1+2*3 = 7")
    if ok:
        assert isinstance(r, BinaryOpNode) and r.op == '+'
        assert isinstance(r.right, BinaryOpNode) and r.right.op == '*'
        print("    -> precedence correct")

    r, ok = test_parse("2 ^ 3 ^ 2", "right-assoc: 2^3^2 = 2^9 = 512")
    if ok:
        assert isinstance(r, BinaryOpNode) and r.op == '^'
        assert isinstance(r.right, BinaryOpNode) and r.right.op == '^'
        print("    -> right-associativity correct")

    r, ok = test_parse("[1, 2+3, pi*2]", "vector literal")
    all_passed = all_passed and ok

    r, ok = test_parse("a ? b : c", "ternary operator")
    all_passed = all_passed and ok

    r, ok = test_parse("pow(2, 10)", "pow function call")
    all_passed = all_passed and ok

    r, ok = test_parse("clamp(5, 0, 10)", "clamp function call")
    all_passed = all_passed and ok

    r, ok = test_parse("vec(1, 2, 3, 4)", "vec function call")
    all_passed = all_passed and ok

    r, ok = test_parse("-x + +y * -(1+2)", "unary ops")
    all_passed = all_passed and ok

    r, ok = test_parse("x < 5 && y >= 10 || z == 0", "logic + compare")
    all_passed = all_passed and ok

    r, ok = test_parse("1e3 + .5 + 3.14e-2", "number formats (sci, .5)")
    all_passed = all_passed and ok

    r, ok = test_parse("[[1,2,3],[4,5,6],[7,8,9]]", "3x3 matrix literal")
    all_passed = all_passed and ok

    r, ok = test_parse_fail("[[1,2],[3]]", "matrix inconsistent columns")
    all_passed = all_passed and ok

    r, ok = test_parse("log(e^2)", "log single arg (natural)")
    all_passed = all_passed and ok

    r, ok = test_parse("log(10, 100)", "log double arg (log base 10 of 100)")
    all_passed = all_passed and ok

    print()
    if all_passed:
        print("AST parse tests: all passed")
    else:
        print("AST parse tests: SOME TESTS FAILED")
        sys.exit(1)
