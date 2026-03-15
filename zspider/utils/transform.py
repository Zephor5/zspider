# coding=utf-8
import ast
import re


class UnsafeTransform(Exception):
    pass


class SafeTransformEvaluator(object):
    ALLOWED_GLOBALS = {"doc", "re"}
    ALLOWED_DICT_METHODS = {"get", "update", "pop", "setdefault"}
    ALLOWED_STRING_METHODS = {
        "strip",
        "lstrip",
        "rstrip",
        "replace",
        "lower",
        "upper",
        "split",
    }
    ALLOWED_RE_METHODS = {"search", "match", "sub", "findall", "compile"}
    ALLOWED_PATTERN_METHODS = {"search", "match", "sub", "findall"}
    ALLOWED_NODE_TYPES = (
        ast.Expression,
        ast.BoolOp,
        ast.UnaryOp,
        ast.BinOp,
        ast.Compare,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Dict,
        ast.List,
        ast.Tuple,
        ast.Subscript,
        ast.Attribute,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Eq,
        ast.NotEq,
        ast.In,
        ast.NotIn,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.Add,
    )

    def __init__(self, doc):
        self._ctx = {"doc": doc, "re": re}

    @classmethod
    def execute(cls, expr, doc):
        tree = ast.parse(expr, mode="eval")
        cls._validate(tree)
        return cls(doc)._eval(tree.body)

    @classmethod
    def _validate(cls, tree):
        for node in ast.walk(tree):
            if not isinstance(node, cls.ALLOWED_NODE_TYPES):
                raise UnsafeTransform("unsupported syntax: %s" % type(node).__name__)
            if isinstance(node, ast.Name) and node.id not in cls.ALLOWED_GLOBALS:
                raise UnsafeTransform("unsupported name: %s" % node.id)

    def _eval(self, node):  # noqa: C901
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self._ctx[node.id]
        if isinstance(node, ast.Dict):
            return {
                self._eval(key): self._eval(value)
                for key, value in zip(node.keys, node.values)
            }
        if isinstance(node, ast.List):
            return [self._eval(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval(item) for item in node.elts)
        if isinstance(node, ast.Subscript):
            return self._eval(node.value)[self._eval(node.slice)]
        if isinstance(node, ast.Attribute):
            return self._resolve_attr(self._eval(node.value), node.attr)
        if isinstance(node, ast.Call):
            func = self._eval(node.func)
            args = [self._eval(arg) for arg in node.args]
            kwargs = {kw.arg: self._eval(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        if isinstance(node, ast.BoolOp):
            values = iter(node.values)
            result = self._eval(next(values))
            if isinstance(node.op, ast.And):
                for value in values:
                    if not result:
                        return result
                    result = self._eval(value)
                return result
            for value in values:
                if result:
                    return result
                result = self._eval(value)
            return result
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._eval(node.left) + self._eval(node.right)
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, comparator_node in zip(node.ops, node.comparators):
                right = self._eval(comparator_node)
                if isinstance(op, ast.Eq):
                    matched = left == right
                elif isinstance(op, ast.NotEq):
                    matched = left != right
                elif isinstance(op, ast.In):
                    matched = left in right
                elif isinstance(op, ast.NotIn):
                    matched = left not in right
                elif isinstance(op, ast.Gt):
                    matched = left > right
                elif isinstance(op, ast.GtE):
                    matched = left >= right
                elif isinstance(op, ast.Lt):
                    matched = left < right
                elif isinstance(op, ast.LtE):
                    matched = left <= right
                else:
                    raise UnsafeTransform("unsupported compare op")
                if not matched:
                    return False
                left = right
            return True
        raise UnsafeTransform("unsupported syntax: %s" % type(node).__name__)

    def _resolve_attr(self, value, attr):
        if value is re:
            if attr not in self.ALLOWED_RE_METHODS:
                raise UnsafeTransform("unsupported re method: %s" % attr)
            return getattr(value, attr)
        if isinstance(value, dict):
            if attr not in self.ALLOWED_DICT_METHODS:
                raise UnsafeTransform("unsupported doc method: %s" % attr)
            return getattr(value, attr)
        if isinstance(value, str):
            if attr not in self.ALLOWED_STRING_METHODS:
                raise UnsafeTransform("unsupported string method: %s" % attr)
            return getattr(value, attr)
        if isinstance(value, re.Pattern):
            if attr not in self.ALLOWED_PATTERN_METHODS:
                raise UnsafeTransform("unsupported pattern method: %s" % attr)
            return getattr(value, attr)
        raise UnsafeTransform("unsupported attribute access: %s" % attr)
