"""A tiny, safe formula language for computed fields in the entity registry (registry.py).

The same language is implemented in the browser (frontend/src/lib/expr.js) so the staff app shows totals while
typing and the hosted preview computes exactly what the server stores. Both run the cases in
backend/tests/expr_cases.json.

    qty * rate                         arithmetic: + - * / %  and parentheses
    sum(lines.amount)                  sum over a list field
    round(subtotal * gst_rate / 100, 2)
    if(stage == 'lost', 0, value)      comparisons: == != < <= > >=, and / or / not
    max(a, b)  min(a, b)  abs(x)  ceil(x)  floor(x)  count(lines)  coalesce(a, b)  days(to, frm)
Unknown names are 0 (or '' when compared with text). Division by zero gives 0.
"""
import math
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|('(?:[^'\\]|\\.)*')|([A-Za-z_][\w.]*)|(==|!=|<=|>=|[-+*/%(),<>!]))")


def tokenize(src):
    pos, out = 0, []
    src = src.strip()
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Bad formula near: {src[pos:pos + 10]}")
        num, s, name, op = m.groups()
        if num is not None:
            out.append(("num", float(num)))
        elif s is not None:
            out.append(("str", s[1:-1].replace("\\'", "'")))
        elif name is not None:
            if name in ("and", "or", "not"):
                out.append(("op", name))
            elif name in ("true", "false"):
                out.append(("num", 1.0 if name == "true" else 0.0))
            else:
                out.append(("name", name))
        else:
            out.append(("op", op))
        pos = m.end()
        while pos < len(src) and src[pos].isspace():
            pos += 1
    out.append(("end", None))
    return out


PREC = {"or": 1, "and": 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}


class Parser:
    def __init__(self, src):
        self.t = tokenize(src)
        self.i = 0

    def peek(self):
        return self.t[self.i]

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expect(self, v):
        tok = self.take()
        if tok != ("op", v):
            raise ValueError(f"Expected {v}")

    def parse(self):
        node = self.expr(0)
        if self.peek()[0] != "end":
            raise ValueError("Unexpected text at end of formula")
        return node

    def expr(self, minp):
        left = self.unary()
        while True:
            kind, v = self.peek()
            if kind != "op" or v not in PREC or PREC[v] < minp:
                return left
            self.take()
            right = self.expr(PREC[v] + 1)
            left = ("bin", v, left, right)

    def unary(self):
        kind, v = self.peek()
        if kind == "op" and v in ("-", "not", "!"):
            self.take()
            return ("neg" if v == "-" else "not", self.unary())
        if kind == "op" and v == "+":
            self.take()
            return self.unary()
        return self.primary()

    def primary(self):
        kind, v = self.take()
        if kind == "num":
            return ("num", v)
        if kind == "str":
            return ("str", v)
        if kind == "op" and v == "(":
            node = self.expr(0)
            self.expect(")")
            return node
        if kind == "name":
            if self.peek() == ("op", "("):
                self.take()
                args = []
                if self.peek() != ("op", ")"):
                    while True:
                        args.append(self.expr(0))
                        if self.peek() == ("op", ","):
                            self.take()
                            continue
                        break
                self.expect(")")
                return ("call", v, args)
            return ("name", v)
        raise ValueError("Bad formula")


_cache = {}


def compile_expr(src):
    if src not in _cache:
        _cache[src] = Parser(src).parse()
    return _cache[src]


def num(x):
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x) if x.strip() else 0.0
        except ValueError:
            return 0.0
    return 0.0


def truthy(x):
    if isinstance(x, str):
        return x != ""
    if isinstance(x, list):
        return len(x) > 0
    return bool(x)


def round_half_up(x, n=0):
    q = Decimal(1).scaleb(-int(n))
    return float(Decimal(repr(num(x))).quantize(q, rounding=ROUND_HALF_UP))


def resolve(ctx, path):
    parts = path.split(".")
    cur = ctx
    for i, p in enumerate(parts):
        if isinstance(cur, list):
            rest = ".".join(parts[i:])
            return [resolve(item, rest) for item in cur]
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _days(a, b):
    try:
        return (date.fromisoformat(str(a)[:10]) - date.fromisoformat(str(b)[:10])).days
    except ValueError:
        return 0


def _cmp_val(x):
    return x if isinstance(x, str) else num(x)


def ev(node, ctx):
    k = node[0]
    if k == "num":
        return node[1]
    if k == "str":
        return node[1]
    if k == "name":
        v = resolve(ctx, node[1])
        return 0.0 if v is None else v
    if k == "neg":
        return -num(ev(node[1], ctx))
    if k == "not":
        return 0.0 if truthy(ev(node[1], ctx)) else 1.0
    if k == "bin":
        op = node[1]
        if op == "and":
            return 1.0 if truthy(ev(node[2], ctx)) and truthy(ev(node[3], ctx)) else 0.0
        if op == "or":
            return 1.0 if truthy(ev(node[2], ctx)) or truthy(ev(node[3], ctx)) else 0.0
        a, b = ev(node[2], ctx), ev(node[3], ctx)
        if op in ("==", "!="):
            if isinstance(a, str) or isinstance(b, str):
                eq = str(a if a is not None else "") == str(b if b is not None else "")
                if isinstance(a, (int, float)) and not isinstance(a, bool) and a == 0 and b == "":
                    eq = True
            else:
                eq = num(a) == num(b)
            return 1.0 if (eq if op == "==" else not eq) else 0.0
        if op in ("<", "<=", ">", ">="):
            x, y = _cmp_val(a), _cmp_val(b)
            if isinstance(x, str) != isinstance(y, str):
                x, y = str(x), str(y)
            return 1.0 if {"<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[op] else 0.0
        x, y = num(a), num(b)
        if op == "+":
            return x + y
        if op == "-":
            return x - y
        if op == "*":
            return x * y
        if op == "/":
            return x / y if y else 0.0
        if op == "%":
            return math.fmod(x, y) if y else 0.0
    if k == "call":
        fn, args = node[1], node[2]
        if fn == "if":
            return ev(args[1], ctx) if truthy(ev(args[0], ctx)) else (ev(args[2], ctx) if len(args) > 2 else 0.0)
        vals = [ev(a, ctx) for a in args]
        if fn == "sum":
            v = vals[0] if vals else []
            return sum(num(x) for x in v) if isinstance(v, list) else num(v)
        if fn == "count":
            v = vals[0] if vals else []
            return float(len(v)) if isinstance(v, list) else (1.0 if truthy(v) else 0.0)
        if fn == "round":
            return round_half_up(vals[0], vals[1] if len(vals) > 1 else 0)
        if fn == "min":
            return min(num(x) for x in vals)
        if fn == "max":
            return max(num(x) for x in vals)
        if fn == "abs":
            return abs(num(vals[0]))
        if fn == "ceil":
            return float(math.ceil(num(vals[0]) - 1e-9))
        if fn == "floor":
            return float(math.floor(num(vals[0]) + 1e-9))
        if fn == "coalesce":
            for x in vals:
                if truthy(x):
                    return x
            return 0.0
        if fn == "days":
            return float(_days(vals[0], vals[1]))
        raise ValueError(f"Unknown function {fn}")
    raise ValueError("Bad formula")


def evaluate(src, ctx):
    v = ev(compile_expr(src), ctx)
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return v
    return v
