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

import sys, os, json, re, traceback
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path: sys.path.insert(0, _PROJECT_ROOT)

from src.services.ai_agent import BaseTool
from src.utils.logger import get_logger
logger = get_logger(__name__)

_EXPRESSION_MAX_LEN = 5000
_GRAPH_JSON_MAX_LEN = 50 * 1024  # 50KB

class MathCalculatorTool(BaseTool):
    """
    节点化数学计算器（C++ 高性能后端 + Python 备用后端）

    以节点图方式执行数学计算，支持：
    - 数学表达式字符串求值（支持算术/三角/幂根/向量/矩阵/统计/比较/逻辑/三元条件）
    - JSON 节点图描述构建和执行（44 种节点自由组合）
    - 所有结果含中间步骤数和节点图信息，可审计
    """
    category = "math"

    @classmethod
    def execute(cls,
                mode: str = "evaluate",
                expression: str = "",
                graph_json: str = "",
                variables: str = "{}") -> str:
        """
        参数:
            mode: "evaluate" (表达式求值,默认) 或 "build_graph" (节点图JSON描述)
            expression: mode=evaluate 时必填,数学表达式字符串
            graph_json: mode=build_graph 时必填,节点图JSON描述
                      {"nodes":[{"id":"n1","type":"Number","params":{"value":3.14}},...],
                       "edges":[{"from":"n1","out":0,"to":"n2","in":0},...]}
            variables: 变量表 JSON (mode=evaluate 时生效),如 {"x":3,"y":[1,2,3]}
        返回:
            人类可读 + AI 可解析的结果字符串,统一格式 code/message/data
        """
        try:
            # 解析变量 JSON
            try:
                var_map = json.loads(variables) if variables else {}
            except Exception as e:
                return _fmt_err("E_VALIDATION_PARSE_ERROR",
                                f"variables 不是合法 JSON: {e}")
            # 输入长度限制
            if mode == "evaluate":
                if len(expression) > _EXPRESSION_MAX_LEN:
                    return _fmt_err("E_VALIDATION_TOO_LARGE",
                                    f"expression 长度 {len(expression)} 超过上限 {_EXPRESSION_MAX_LEN}",
                                    "请拆分表达式多次调用")
            elif mode == "build_graph":
                if len(graph_json) > _GRAPH_JSON_MAX_LEN:
                    return _fmt_err("E_VALIDATION_TOO_LARGE",
                                    f"graph_json 长度 {len(graph_json)} 超过上限 {_GRAPH_JSON_MAX_LEN}",
                                    "请简化节点图或分多次")
            else:
                return _fmt_err("E_VALIDATION_INVALID_ARG",
                                f"未知 mode: {mode}, 只支持 evaluate / build_graph",
                                '请使用 mode="evaluate" 或 mode="build_graph"')

            if mode == "evaluate":
                return _do_evaluate(expression, var_map)
            else:
                return _do_build_graph(graph_json, var_map)
        except Exception as e:
            # 捕获一切异常,不抛裸异常给 AI
            from src.utils.errors import AppError
            if isinstance(e, AppError):
                code = str(getattr(e, 'code', e.code if hasattr(e,'code') else 'E_VALIDATION_MATH_ERROR'))
                msg = str(e)
                sug = e.get_suggestion() if hasattr(e, 'get_suggestion') else ''
                return _fmt_str(code, msg, suggestion=sug)
            tb = traceback.format_exc()
            logger.error(f"MathCalculatorTool 未预期异常: {e}\n{tb}")
            return _fmt_err("E_VALIDATION_MATH_ERROR",
                            f"计算失败: {e}",
                            "请检查表达式/节点图语法,或使用更小的用例")


def _fmt_str(code, message, data=None, suggestion=""):
    lines = [f"code: {code}", f"message: {message}"]
    if suggestion:
        lines.append(f"suggestion: {suggestion}")
    if data is not None:
        lines.append("data: " + json.dumps(data, ensure_ascii=False))
    return "\n".join(lines)

def _fmt_err(code, message, suggestion=""):
    return _fmt_str(code, message, suggestion=suggestion)

def _value_to_str(v):
    """把节点输出值转换为字符串(标量/向量/矩阵)"""
    import numbers
    if isinstance(v, numbers.Number):
        # 科学计数法避免极小数/极大数
        if abs(float(v)) < 1e-10: return "0"
        return f"{float(v):.10g}"
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return "[]"
    if isinstance(v, (list, tuple)):
        first = v[0]
        if isinstance(first, (list, tuple)):  # 矩阵
            rows = []
            for r in v:
                rows.append("[" + ", ".join(_value_to_str(x) for x in r) + "]")
            return "[" + ", ".join(rows) + "]"
        else:  # 向量
            return "[" + ", ".join(_value_to_str(x) for x in v) + "]"
    return str(v)

def _output_port_value(port):
    """根据 backend 把输出端口取值出来(兼容 cppyy python proxy)"""
    # 先判断 type: PortType 枚举或字符串
    t = getattr(port, 'type', None)
    type_name = str(t)  # cppyy 枚举打印字符串或 int
    if isinstance(t, str):
        tag = t
    else:
        tag = type_name.split('.')[-1] if '.' in type_name else type_name
    if tag in ('SCALAR', 'scalar', '0'):
        return float(port.s)
    if tag in ('VECTOR', 'vector', '1'):
        return [float(x) for x in port.v]
    if tag in ('MATRIX', 'matrix', '2'):
        m = port.m
        return [[float(x) for x in row] for row in m]
    # 兜底: 先试 s (最常见)
    try: return float(port.s)
    except Exception: pass
    return None

def _do_evaluate(expression, variables):
    if not expression or not expression.strip():
        return _fmt_err("E_VALIDATION_PARSE_ERROR", "expression 为空", "请输入数学表达式")
    from src.core.expression_parser import evaluate_expression
    from src.utils.errors import AppError, ValidationError
    try:
        result = evaluate_expression(expression, variables)
        value = result.get("value")
        steps = result.get("steps")
        graph_nodes = result.get("graph_nodes")
        payload = {
            "value": value,
            "value_str": _value_to_str(value),
            "steps": steps,
            "graph_nodes": graph_nodes,
        }
        return _fmt_str("OK",
                        f"表达式求值完成: {expression} = {_value_to_str(value)}",
                        data=payload)
    except (AppError, ValidationError) as e:
        return _fmt_err(str(getattr(e, 'code', 'E_VALIDATION_PARSE_ERROR')),
                        str(e),
                        e.get_suggestion() if hasattr(e, 'get_suggestion') else '')


def _do_build_graph(graph_json_str, variables):
    if not graph_json_str or not graph_json_str.strip():
        return _fmt_err("E_VALIDATION_PARSE_ERROR", "graph_json 为空",
                        "请提供 JSON 节点图描述")
    try:
        desc = json.loads(graph_json_str)
    except Exception as e:
        return _fmt_err("E_VALIDATION_PARSE_ERROR", f"graph_json 不是合法 JSON: {e}")

    nodes_desc = desc.get("nodes") or []
    edges_desc = desc.get("edges") or []
    if not nodes_desc:
        return _fmt_err("E_VALIDATION_INVALID_ARG", "nodes 为空", "至少添加 1 个节点")

    from src.core.node_engine import NodeEngine, make_graph, execute_graph
    from src.utils.errors import AppError
    eng = NodeEngine()
    node_idx_by_id = {}
    g = eng.Graph()

    # Step1: 实例化节点
    # 支持的节点参数映射: Number(value) / Variable(可设 value) / VecCreate(n) / MatCreate(rows,cols)
    for nd in nodes_desc:
        nid = nd.get("id")
        ntype = nd.get("type")
        params = nd.get("params") or {}
        if not ntype:
            return _fmt_err("E_VALIDATION_INVALID_ARG",
                            f"节点 {nid}: 缺少 type 字段")
        if not hasattr(eng, ntype):
            return _fmt_err("E_VALIDATION_INVALID_ARG",
                            f"未知节点类型: {ntype}, 可用: {', '.join(eng.node_classes[:20])}...")
        cls = getattr(eng, ntype)
        # 根据类型构造
        try:
            if ntype == "Number":
                node = cls(float(params.get("value", 0.0)))
            elif ntype == "Variable":
                node = cls()
                # 可设置输入默认值
                if "value" in params:
                    try: node.inputs[0].s = float(params["value"])
                    except Exception: pass
            elif ntype == "VecCreate":
                n = int(params.get("n", len(params.get("values", []))))
                node = cls(n)
                vals = params.get("values", [])
                for i, v in enumerate(vals):
                    if i < n: node.inputs[i].s = float(v)
            elif ntype == "MatCreate":
                rows = int(params.get("rows", 2))
                cols = int(params.get("cols", 2))
                node = cls(rows, cols)
                vals = params.get("values", [])
                for i, v in enumerate(vals):
                    if i < rows * cols: node.inputs[i].s = float(v)
            elif ntype == "Log":
                # Log(base, x) 双参数或 Log(x) 单参数
                node = cls()
            else:
                node = cls()
            # 通用: 直接设 inputs[i].s / inputs[i].v / inputs[i].m
            if "inputs" in params:
                for idx, val in enumerate(params["inputs"]):
                    if idx < len(node.inputs):
                        if isinstance(val, (int, float)):
                            node.inputs[idx].s = float(val)
                        elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], (list, tuple)):
                            node.inputs[idx].m = [[float(x) for x in r] for r in val]
                        elif isinstance(val, list):
                            node.inputs[idx].v = [float(x) for x in val]
        except Exception as e:
            return _fmt_err("E_VALIDATION_INVALID_ARG",
                            f"实例化节点 {nid}({ntype}) 失败: {e}",
                            "检查 params 是否匹配节点构造函数")
        idx = g.add_node(node)
        if nid is not None:
            node_idx_by_id[str(nid)] = idx

    # Step2: 连边
    for e in edges_desc:
        frm = e.get("from"); out = e.get("out", 0)
        to = e.get("to"); inp = e.get("in", 0)
        if frm not in node_idx_by_id:
            return _fmt_err("E_VALIDATION_INVALID_ARG", f"边 from={frm} 节点不存在")
        if to not in node_idx_by_id:
            return _fmt_err("E_VALIDATION_INVALID_ARG", f"边 to={to} 节点不存在")
        g.connect(node_idx_by_id[frm], int(out), node_idx_by_id[to], int(inp))

    # Step3: 执行
    try:
        execute_graph(g)
    except AppError as e:
        return _fmt_err(str(getattr(e, 'code', 'E_VALIDATION_MATH_ERROR')),
                        str(e),
                        e.get_suggestion() if hasattr(e, 'get_suggestion') else '')

    # Step4: 汇总所有 outputs[0].value 到 dict by id
    results = {}
    for nid, idx in node_idx_by_id.items():
        node = g.nodes[idx]
        outs = []
        for p in node.outputs:
            outs.append(_output_port_value(p))
        results[nid] = outs if len(outs) != 1 else outs[0]

    payload = {
        "backend": getattr(eng, 'backend', 'unknown'),
        "nodes_count": len(g.nodes),
        "edges_count": len(edges_desc),
        "outputs_by_id": results,
    }
    last_nid = nodes_desc[-1].get("id")
    last_val = results.get(last_nid)
    return _fmt_str("OK",
                    f"节点图执行完成(最后节点 {last_nid}): output = {_value_to_str(last_val)}",
                    data=payload)
