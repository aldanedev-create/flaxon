from __future__ import annotations

from typing import Any

from flaxon._imports import import_attribute

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
    """Parser implementation for the graphql subsystem."""

    def __init__(self, source: str) -> None:
        self.lexer = Lexer(source)
        self.current_token = self.lexer.next_token()

    def parse(self) -> Document:
        """Parse the supplied input into its structured representation."""
        definitions = []

        while self.current_token.type != TokenType.EOF:
            definitions.append(self.parse_definition())

        return Document(definitions)

    def parse_definition(self) -> Any:
        """Parse the definition."""
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
        """Parse the operation definition."""
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
        """Parse the variable definitions."""
        variables = []

        while self.current_token.type != TokenType.RIGHT_PAREN:
            if self.current_token.type == TokenType.DOLLAR:
                variable = self.parse_variable_definition()
                variables.append(variable)

        return variables

    def parse_variable_definition(self) -> Any:
        """Parse the variable definition."""
        self.expect_token(TokenType.DOLLAR)
        name = self.parse_name()
        self.expect_token(TokenType.COLON)

        variable_definition_type = import_attribute("flaxon.graphql.ast", "VariableDefinition")

        type_ = self.parse_type_reference()

        default_value = None
        if self.current_token.type == TokenType.EQUALS:
            self.advance()
            default_value = self.parse_value()

        return variable_definition_type(
            name=name,
            type=type_,
            default_value=default_value,
        )

    def parse_type_reference(self) -> Any:
        """Parse the type reference."""
        list_type_type = import_attribute("flaxon.graphql.ast", "ListType")
        named_type_type = import_attribute("flaxon.graphql.ast", "NamedType")
        non_null_type_type = import_attribute("flaxon.graphql.ast", "NonNullType")

        if self.current_token.type == TokenType.LEFT_BRACKET:
            self.advance()
            type_ = self.parse_type_reference()
            self.expect_token(TokenType.RIGHT_BRACKET)
            type_ = list_type_type(type_)
        else:
            name = self.parse_name()
            type_ = named_type_type(name)

        if self.current_token.type == TokenType.BANG:
            self.advance()
            type_ = non_null_type_type(type_)

        return type_

    def parse_selection_set(self) -> SelectionSet:
        """Parse the selection set."""
        self.expect_token(TokenType.LEFT_BRACE)
        selections = []

        while self.current_token.type != TokenType.RIGHT_BRACE:
            selections.append(self.parse_selection())

        self.expect_token(TokenType.RIGHT_BRACE)

        return SelectionSet(selections)

    def parse_selection(self) -> Any:
        """Parse the selection."""
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
        """Parse the field."""
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
        """Parse the fragment spread."""
        name = self.parse_name()

        directives = []
        if self.current_token.type == TokenType.AT:
            directives = self.parse_directives()

        return FragmentSpread(name=name, directives=directives)

    def parse_inline_fragment(self) -> InlineFragment:
        """Parse the inline fragment."""
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
        """Parse the fragment definition."""
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
        """Parse the arguments."""
        arguments = []

        while self.current_token.type != TokenType.RIGHT_PAREN:
            name = self.parse_name()
            self.expect_token(TokenType.COLON)
            value = self.parse_value()
            arguments.append(Argument(name, value))

        return arguments

    def parse_directives(self) -> list[Directive]:
        """Parse the directives."""
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
        """Parse a scalar, variable, list, or object GraphQL value."""
        scalar = {
            TokenType.INT: IntValue,
            TokenType.FLOAT: FloatValue,
            TokenType.STRING: StringValue,
        }.get(self.current_token.type)
        if scalar is not None:
            value = scalar(self.current_token.value)
            self.advance()
            return value
        if self.current_token.type == TokenType.NAME:
            return self._parse_named_value()
        parser = {
            TokenType.DOLLAR: self._parse_variable_value,
            TokenType.LEFT_BRACKET: self._parse_list_value,
            TokenType.LEFT_BRACE: self._parse_object_value,
        }.get(self.current_token.type)
        if parser is not None:
            return parser()
        return self._unexpected_value()

    def _unexpected_value(self) -> Any:
        raise GraphQLSyntaxError(
            f"Unexpected token: {self.current_token.value}",
            self.current_token.line,
            self.current_token.column,
        )

    def _parse_named_value(self) -> Any:
        values = {"true": BooleanValue(True), "false": BooleanValue(False), "null": None}
        if self.current_token.value not in values:
            self._unexpected_value()
        value = values[self.current_token.value]
        self.advance()
        return value

    def _parse_variable_value(self) -> Variable:
        self.advance()
        return Variable(self.parse_name())

    def _parse_list_value(self) -> ListValue:
        self.advance()
        values = []
        while self.current_token.type != TokenType.RIGHT_BRACKET:
            values.append(self.parse_value())
        self.expect_token(TokenType.RIGHT_BRACKET)
        return ListValue(values)

    def _parse_object_value(self) -> ObjectValue:
        self.advance()
        fields = []
        while self.current_token.type != TokenType.RIGHT_BRACE:
            name = self.parse_name()
            self.expect_token(TokenType.COLON)
            fields.append(ObjectField(name, self.parse_value()))
        self.expect_token(TokenType.RIGHT_BRACE)
        return ObjectValue(fields)

    def parse_name(self) -> Name:
        """Parse the name."""
        token = self.current_token
        self.expect_token(TokenType.NAME)
        return Name(token.value)

    def expect_token(self, expected_type: TokenType, expected_value: str | None = None) -> None:
        """Perform the expect token operation for parser."""
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
        """Perform the advance operation for parser."""
        self.current_token = self.lexer.next_token()
