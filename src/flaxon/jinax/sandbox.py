from __future__ import annotations

import ast
import builtins
from typing import Any


class Sandbox:
    """Sandbox implementation for the jinax subsystem."""

    def __init__(self, allowed_modules: list[str] | None = None) -> None:
        self.allowed_modules = allowed_modules or []
        self._restricted_globals = self._create_restricted_globals()
        self._node_handlers = {
            ast.Constant: self._evaluate_constant,
            ast.Name: self._evaluate_name,
            ast.List: self._evaluate_list,
            ast.Tuple: self._evaluate_tuple,
            ast.Set: self._evaluate_set,
            ast.Dict: self._evaluate_dict,
            ast.Subscript: self._evaluate_subscript,
            ast.Attribute: self._evaluate_attribute,
            ast.UnaryOp: self._evaluate_unaryop,
            ast.BinOp: self._evaluate_binop,
            ast.BoolOp: self._evaluate_boolop,
            ast.Compare: self._evaluate_compare,
            ast.Call: self._evaluate_call,
        }

    def _create_restricted_globals(self) -> dict[str, Any]:
        restricted = {}

        safe_builtins = {
            "abs": builtins.abs,
            "all": builtins.all,
            "any": builtins.any,
            "bool": builtins.bool,
            "dict": builtins.dict,
            "enumerate": builtins.enumerate,
            "float": builtins.float,
            "int": builtins.int,
            "len": builtins.len,
            "list": builtins.list,
            "max": builtins.max,
            "min": builtins.min,
            "range": builtins.range,
            "round": builtins.round,
            "str": builtins.str,
            "sum": builtins.sum,
            "tuple": builtins.tuple,
            "zip": builtins.zip,
        }

        restricted.update(safe_builtins)

        restricted.update({
            "__import__": None,
            "eval": None,
            "exec": None,
            "compile": None,
            "open": None,
            "input": None,
            "globals": None,
            "locals": None,
            "vars": None,
            "dir": None,
            "help": None,
        })

        return restricted

    def is_safe_module(self, module_name: str) -> bool:
        """Return whether safe module holds for the current value."""
        return module_name in self.allowed_modules

    def evaluate(self, expr: str, context: dict[str, Any]) -> Any:
        """Perform the evaluate operation for sandbox."""
        try:
            tree = ast.parse(expr, mode="eval")
            return self._evaluate_node(tree.body, context)
        except (ArithmeticError, KeyError, SyntaxError, TypeError, ValueError):
            return None

    def execute(self, code: str, context: dict[str, Any]) -> None:
        """Evaluate safe expression statements without executing Python code.

        The previous implementation delegated to ``exec``, which made this
        class an unsafe execution primitive.  Templates only need expression
        evaluation; statements are intentionally rejected.
        """
        try:
            tree = ast.parse(code, mode="exec")
            for statement in tree.body:
                if not isinstance(statement, ast.Expr):
                    raise ValueError("Only expressions are supported")
                self._evaluate_node(statement.value, context)
        except (ArithmeticError, KeyError, SyntaxError, TypeError, ValueError):
            pass

    def _evaluate_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Dispatch approved AST nodes without allowing arbitrary Python execution."""
        handler = self._node_handlers.get(type(node))
        if handler is None:
            handler = next(
                (
                    callback
                    for node_type, callback in self._node_handlers.items()
                    if isinstance(node, node_type)
                ),
                None,
            )
        if handler is None:
            raise ValueError(f"Unsupported expression: {type(node).__name__}")
        return handler(node, context)

    def _evaluate_constant(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Constant expression."""
        return node.value

    def _evaluate_name(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Name expression."""
        return self._evaluate_node_name(context=context, node=node)

    def _evaluate_list(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved List expression."""
        return [self._evaluate_node(element, context) for element in node.elts]

    def _evaluate_tuple(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Tuple expression."""
        return tuple(self._evaluate_node(element, context) for element in node.elts)

    def _evaluate_set(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Set expression."""
        return {self._evaluate_node(element, context) for element in node.elts}

    def _evaluate_dict(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Dict expression."""
        return {
            self._evaluate_node(key, context): self._evaluate_node(value, context)
            for key, value in zip(node.keys, node.values, strict=True)
        }

    def _evaluate_subscript(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Subscript expression."""
        value = self._evaluate_node(node.value, context)
        index = self._evaluate_node(node.slice, context)
        return value[index]

    def _evaluate_attribute(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Attribute expression."""
        if node.attr.startswith("_"):
            raise ValueError("Private attributes are not allowed")
        value = self._evaluate_node(node.value, context)
        if not isinstance(value, dict):
            raise ValueError("Attribute access is only supported for mappings")
        return value[node.attr]

    def _evaluate_unaryop(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved UnaryOp expression."""
        value = self._evaluate_node(node.operand, context)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise ValueError("Unsupported unary operation")

    def _evaluate_binop(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved BinOp expression."""
        return self._evaluate_node_binop(context=context, node=node)

    def _evaluate_boolop(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved BoolOp expression."""
        values = [self._evaluate_node(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise ValueError("Unsupported boolean operation")

    def _evaluate_compare(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Compare expression."""
        left = self._evaluate_node(node.left, context)
        comparisons = {
            ast.Eq: lambda a, b: a == b,
            ast.NotEq: lambda a, b: a != b,
            ast.Lt: lambda a, b: a < b,
            ast.LtE: lambda a, b: a <= b,
            ast.Gt: lambda a, b: a > b,
            ast.GtE: lambda a, b: a >= b,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
        }
        for operator, comparator_node in zip(node.ops, node.comparators, strict=True):
            right = self._evaluate_node(comparator_node, context)
            for operation, handler in comparisons.items():
                if isinstance(operator, operation):
                    if not handler(left, right):
                        return False
                    break
            else:
                raise ValueError("Unsupported comparison")
            left = right
        return True

    def _evaluate_call(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Evaluate an approved Call expression."""
        return self._evaluate_node_call(context=context, node=node)

    def _evaluate_node_name(self, *, context, node):
        """Handle name behavior for  evaluate node."""
        if node.id.startswith("_"):
            raise ValueError("Private names are not allowed")
        if node.id in context:
            return context[node.id]
        value = self._restricted_globals.get(node.id)
        if value is None:
            raise ValueError(f"Unknown name: {node.id}")
        return value

    def _evaluate_node_binop(self, *, context, node):
        """Handle binop behavior for  evaluate node."""
        left = self._evaluate_node(node.left, context)
        right = self._evaluate_node(node.right, context)
        operations = {
            ast.Add: lambda: left + right,
            ast.Sub: lambda: left - right,
            ast.Mult: lambda: left * right,
            ast.Div: lambda: left / right,
            ast.FloorDiv: lambda: left // right,
            ast.Mod: lambda: left % right,
            ast.Pow: lambda: left**right,
        }
        for operation, handler in operations.items():
            if isinstance(node.op, operation):
                return handler()
        raise ValueError("Unsupported binary operation")

    def _evaluate_node_call(self, *, context, node):
        """Handle call behavior for  evaluate node."""
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only approved functions may be called")
        function = self._evaluate_node(node.func, context)
        if function not in self._restricted_globals.values():
            raise ValueError("Function is not approved")
        return function(
            *(self._evaluate_node(argument, context) for argument in node.args),
            **{
                keyword.arg: self._evaluate_node(keyword.value, context)
                for keyword in node.keywords
                if keyword.arg is not None
            },
        )


class SandboxMiddleware:
    """Sandbox middleware implementation for the jinax subsystem."""

    def __init__(self, app: Any, allowed_modules: list[str] | None = None) -> None:
        self.app = app
        self.sandbox = Sandbox(allowed_modules)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Handle the supplied call using this object's configured behavior."""
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, receive, send)
