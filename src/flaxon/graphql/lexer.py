from __future__ import annotations

from enum import Enum

from .exceptions import GraphQLSyntaxError


class TokenType(Enum):
    EOF = "EOF"
    NAME = "NAME"
    INT = "INT"
    FLOAT = "FLOAT"
    STRING = "STRING"
    COMMENT = "COMMENT"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    LEFT_BRACKET = "["
    RIGHT_BRACKET = "]"
    COLON = ":"
    EQUALS = "="
    BANG = "!"
    DOLLAR = "$"
    AT = "@"
    SPREAD = "..."
    PIPE = "|"
    AMPERSAND = "&"


class Token:
    def __init__(self, type: TokenType, value: str, line: int, column: int) -> None:
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return f"Token({self.type.value}, {self.value!r}, {self.line}, {self.column})"


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self._peek_cache = None

    def next_token(self) -> Token:
        self._skip_whitespace()

        if self.position >= len(self.source):
            return Token(TokenType.EOF, "", self.line, self.column)

        char = self.source[self.position]

        if char == "(":
            return self._make_token(TokenType.LEFT_PAREN, "(")
        if char == ")":
            return self._make_token(TokenType.RIGHT_PAREN, ")")
        if char == "{":
            return self._make_token(TokenType.LEFT_BRACE, "{")
        if char == "}":
            return self._make_token(TokenType.RIGHT_BRACE, "}")
        if char == "[":
            return self._make_token(TokenType.LEFT_BRACKET, "[")
        if char == "]":
            return self._make_token(TokenType.RIGHT_BRACKET, "]")
        if char == ":":
            return self._make_token(TokenType.COLON, ":")
        if char == "=":
            return self._make_token(TokenType.EQUALS, "=")
        if char == "!":
            return self._make_token(TokenType.BANG, "!")
        if char == "$":
            return self._make_token(TokenType.DOLLAR, "$")
        if char == "@":
            return self._make_token(TokenType.AT, "@")
        if char == "|":
            return self._make_token(TokenType.PIPE, "|")
        if char == "&":
            return self._make_token(TokenType.AMPERSAND, "&")

        if char == ".":
            if self._peek() == "." and self._peek(2) == ".":
                self.position += 3
                self.column += 3
                return Token(TokenType.SPREAD, "...", self.line, self.column - 3)
            raise GraphQLSyntaxError(f"Unexpected character: {char}", self.line, self.column)

        if char == '"':
            return self._read_string()

        if char == "#":
            return self._read_comment()

        if char.isdigit() or char == "-":
            return self._read_number()

        if char.isalpha() or char == "_":
            return self._read_name()

        raise GraphQLSyntaxError(f"Unexpected character: {char}", self.line, self.column)

    def _peek(self, offset: int = 1) -> str:
        pos = self.position + offset
        if pos >= len(self.source):
            return ""
        return self.source[pos]

    def _make_token(self, type: TokenType, value: str) -> Token:
        self.position += len(value)
        self.column += len(value)
        return Token(type, value, self.line, self.column - len(value))

    def _skip_whitespace(self) -> None:
        while self.position < len(self.source):
            char = self.source[self.position]
            if char == " " or char == "\t" or char == ",":
                self.position += 1
                self.column += 1
            elif char == "\n":
                self.position += 1
                self.line += 1
                self.column = 1
            else:
                break

    def _read_string(self) -> Token:
        start_line = self.line
        start_column = self.column
        self.position += 1
        self.column += 1
        value = ""

        while self.position < len(self.source):
            char = self.source[self.position]

            if char == '"':
                self.position += 1
                self.column += 1
                return Token(TokenType.STRING, value, start_line, start_column)

            if char == "\\":
                self.position += 1
                self.column += 1
                if self.position >= len(self.source):
                    break

                char = self.source[self.position]
                if char == '"':
                    value += '"'
                elif char == "\\":
                    value += "\\"
                elif char == "/":
                    value += "/"
                elif char == "b":
                    value += "\b"
                elif char == "f":
                    value += "\f"
                elif char == "n":
                    value += "\n"
                elif char == "r":
                    value += "\r"
                elif char == "t":
                    value += "\t"
                elif char == "u":
                    self.position += 1
                    self.column += 1
                    unicode_hex = self.source[self.position : self.position + 4]
                    try:
                        value += chr(int(unicode_hex, 16))
                        self.position += 3
                        self.column += 3
                    except ValueError:
                        raise GraphQLSyntaxError(
                            f"Invalid unicode escape: \\u{unicode_hex}", self.line, self.column
                        )
                else:
                    value += char
            else:
                value += char

            self.position += 1
            self.column += 1

        raise GraphQLSyntaxError("Unterminated string", start_line, start_column)

    def _read_comment(self) -> Token:
        start_line = self.line
        start_column = self.column
        value = ""

        while self.position < len(self.source):
            char = self.source[self.position]
            if char == "\n":
                break
            value += char
            self.position += 1
            self.column += 1

        return Token(TokenType.COMMENT, value, start_line, start_column)

    def _read_number(self) -> Token:
        start_line = self.line
        start_column = self.column
        value = ""

        if self.source[self.position] == "-":
            value += "-"
            self.position += 1
            self.column += 1

        while self.position < len(self.source) and self.source[self.position].isdigit():
            value += self.source[self.position]
            self.position += 1
            self.column += 1

        if self.position < len(self.source) and self.source[self.position] == ".":
            value += "."
            self.position += 1
            self.column += 1

            while self.position < len(self.source) and self.source[self.position].isdigit():
                value += self.source[self.position]
                self.position += 1
                self.column += 1

            return Token(TokenType.FLOAT, value, start_line, start_column)

        return Token(TokenType.INT, value, start_line, start_column)

    def _read_name(self) -> Token:
        start_line = self.line
        start_column = self.column
        value = ""

        while self.position < len(self.source):
            char = self.source[self.position]
            if char.isalnum() or char == "_":
                value += char
                self.position += 1
                self.column += 1
            else:
                break

        return Token(TokenType.NAME, value, start_line, start_column)
