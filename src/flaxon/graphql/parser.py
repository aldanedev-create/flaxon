from __future__ import annotations

from typing import Any

from .ast import (
    Argument,
    BooleanValue,
    Directive,
    Document,
    Field,
    FloatValue,
    FragmentDefinition,
    FragmentSpread,
    InlineFragment,
    IntValue,
    ListValue,
    Name,
    ObjectField,
    ObjectValue,
    OperationDefinition,
    SelectionSet,
    StringValue,
    Variable,
)
from .exceptions import GraphQLSyntaxError
from .lexer import Lexer, TokenType


def parse(source: str) -> Document:
    """Helper function to parse a GraphQL source string into a Document AST."""
    return Parser(source).parse()


class Parser:
    def __init__(self, source: str) -> None:
        self.lexer = Lexer(source)
        self.current_token = self.lexer.next_token()

    def parse(self) -> Document:
        definitions = []

        while self.current_token.type != TokenType.EOF:
            definitions.append(self.parse_definition())

        return Document(definitions)

    def parse_definition(self) -> Any:
        if self.current_token.type == TokenType.NAME:
            if self.current_token.value == "query":
                return self.parse_operation_definition("query")
            if self.current_token.value == "mutation":
                return self.parse_operation_definition("mutation")
            if self.current_token.value == "subscription":
                return self.parse_operation_definition("subscription")
            if self.current_token.value == "fragment":
                return self.parse_fragment_definition()

        # Handle shorthand query syntax (e.g. `{ hello }`), or fallback
        if self.current_token.type == TokenType.LEFT_BRACE:
            return self.parse_operation_definition("query")

        raise GraphQLSyntaxError(
            f"Unexpected token: {self.current_token.value}",
            self.current_token.line,
            self.current_token.column,
        )

    def parse_operation_definition(self, operation_type: str) -> OperationDefinition:
        # Only expect/consume the keyword if we are currently at a NAME token
        if self.current_token.type == TokenType.NAME and self.current_token.value == operation_type:
            self.expect_token(TokenType.NAME, operation_type)

        name = None
        if self.current_token.type == TokenType.NAME:
            name = self.parse_name()

        variables = []
        if self.current_token.type == TokenType.LEFT_PAREN:
            self.expect_token(TokenType.LEFT_PAREN)
            variables = self.parse_variable_definitions()
            self.expect_token(TokenType.RIGHT_PAREN)

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        selection_set = self.parse_selection_set()

        return OperationDefinition(
            operation=operation_type,
            name=name,
            variable_definitions=variables,
            directives=directives,
            selection_set=selection_set,
        )

    def parse_variable_definitions(self) -> list[Any]:
        variables = []

        while self.current_token.type != TokenType.RIGHT_PAREN:
            if self.current_token.type == TokenType.DOLLAR:
                variable = self.parse_variable_definition()
                variables.append(variable)

        return variables

    def parse_variable_definition(self) -> Any:
        self.expect_token(TokenType.DOLLAR)
        name = self.parse_name()
        self.expect_token(TokenType.COLON)

        from .ast import VariableDefinition

        type_ = self.parse_type_reference()

        default_value = None
        if self.current_token.type == TokenType.EQUALS:
            self.advance()
            default_value = self.parse_value()

        return VariableDefinition(
            name=name,
            type=type_,
            default_value=default_value,
        )

    def parse_type_reference(self) -> Any:
        from .ast import ListType, NamedType, NonNullType

        if self.current_token.type == TokenType.LEFT_BRACKET:
            self.advance()
            type_ = self.parse_type_reference()
            self.expect_token(TokenType.RIGHT_BRACKET)
            type_ = ListType(type_)
        else:
            name = self.parse_name()
            type_ = NamedType(name)

        if self.current_token.type == TokenType.BANG:
            self.advance()
            type_ = NonNullType(type_)

        return type_

    def parse_selection_set(self) -> SelectionSet:
        self.expect_token(TokenType.LEFT_BRACE)
        selections = []

        while self.current_token.type != TokenType.RIGHT_BRACE:
            selections.append(self.parse_selection())

        self.expect_token(TokenType.RIGHT_BRACE)

        return SelectionSet(selections)

    def parse_selection(self) -> Any:
        if self.current_token.type == TokenType.SPREAD:
            self.advance()
            if self.current_token.type == TokenType.NAME:
                if self.current_token.value == "on":
                    self.advance()
                    return self.parse_inline_fragment()
                return self.parse_fragment_spread()
        elif self.current_token.type == TokenType.NAME:
            return self.parse_field()

        raise GraphQLSyntaxError("Unexpected token", self.current_token.line, self.current_token.column)

    def parse_field(self) -> Field:
        name = self.parse_name()

        alias = None
        if self.current_token.type == TokenType.COLON:
            self.advance()
            alias = name
            name = self.parse_name()

        arguments = []
        if self.current_token.type == TokenType.LEFT_PAREN:
            self.expect_token(TokenType.LEFT_PAREN)
            arguments = self.parse_arguments()
            self.expect_token(TokenType.RIGHT_PAREN)

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        selection_set = None
        if self.current_token.type == TokenType.LEFT_BRACE:
            selection_set = self.parse_selection_set()

        return Field(
            name=name,
            alias=alias,
            arguments=arguments,
            directives=directives,
            selection_set=selection_set,
        )

    def parse_fragment_spread(self) -> FragmentSpread:
        name = self.parse_name()

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        return FragmentSpread(name=name, directives=directives)

    def parse_inline_fragment(self) -> InlineFragment:
        type_condition = None
        if self.current_token.type == TokenType.NAME:
            type_condition = self.parse_name()

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        selection_set = self.parse_selection_set()

        return InlineFragment(
            type_condition=type_condition,
            directives=directives,
            selection_set=selection_set,
        )

    def parse_fragment_definition(self) -> FragmentDefinition:
        self.expect_token(TokenType.NAME, "fragment")
        name = self.parse_name()
        self.expect_token(TokenType.NAME, "on")
        type_condition = self.parse_name()

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        selection_set = self.parse_selection_set()

        return FragmentDefinition(
            name=name,
            type_condition=type_condition,
            directives=directives,
            selection_set=selection_set,
        )

    def parse_arguments(self) -> list[Argument]:
        arguments = []

        while self.current_token.type != TokenType.RIGHT_PAREN:
            name = self.parse_name()
            self.expect_token(TokenType.COLON)
            value = self.parse_value()
            arguments.append(Argument(name, value))

        return arguments

    def parse_directives(self) -> list[Directive]:
        directives = []

        while self.current_token.type == TokenType.AT:
            self.advance()
            name = self.parse_name()
            arguments = []

            if self.current_token.type == TokenType.LEFT_PAREN:
                self.expect_token(TokenType.LEFT_PAREN)
                arguments = self.parse_arguments()
                self.expect_token(TokenType.RIGHT_PAREN)

            directives.append(Directive(name, arguments))

        return directives

    def parse_value(self) -> Any:
        if self.current_token.type == TokenType.INT:
            value = IntValue(self.current_token.value)
            self.advance()
            return value

        if self.current_token.type == TokenType.FLOAT:
            value = FloatValue(self.current_token.value)
            self.advance()
            return value

        if self.current_token.type == TokenType.STRING:
            value = StringValue(self.current_token.value)
            self.advance()
            return value

        if self.current_token.type == TokenType.NAME:
            if self.current_token.value == "true":
                self.advance()
                return BooleanValue(True)
            if self.current_token.value == "false":
                self.advance()
                return BooleanValue(False)
            if self.current_token.value == "null":
                self.advance()
                return None

        if self.current_token.type == TokenType.DOLLAR:
            self.advance()
            name = self.parse_name()
            return Variable(name)

        if self.current_token.type == TokenType.LEFT_BRACKET:
            self.advance()
            values = []
            while self.current_token.type != TokenType.RIGHT_BRACKET:
                values.append(self.parse_value())
            self.expect_token(TokenType.RIGHT_BRACKET)
            return ListValue(values)

        if self.current_token.type == TokenType.LEFT_BRACE:
            self.advance()
            fields = []
            while self.current_token.type != TokenType.RIGHT_BRACE:
                name = self.parse_name()
                self.expect_token(TokenType.COLON)
                value = self.parse_value()
                fields.append(ObjectField(name, value))
            self.expect_token(TokenType.RIGHT_BRACE)
            return ObjectValue(fields)

        raise GraphQLSyntaxError(
            f"Unexpected token: {self.current_token.value}",
            self.current_token.line,
            self.current_token.column,
        )

    def parse_name(self) -> Name:
        token = self.current_token
        self.expect_token(TokenType.NAME)
        return Name(token.value)

    def expect_token(self, expected_type: TokenType, expected_value: str | None = None) -> None:
        if self.current_token.type != expected_type:
            raise GraphQLSyntaxError(
                f"Expected token {expected_type.value}, got {self.current_token.type.value}",
                self.current_token.line,
                self.current_token.column,
            )

        if expected_value is not None and self.current_token.value != expected_value:
            raise GraphQLSyntaxError(
                f"Expected value '{expected_value}', got '{self.current_token.value}'",
                self.current_token.line,
                self.current_token.column,
            )

        self.advance()

    def advance(self) -> None:
        self.current_token = self.lexer.next_token()
