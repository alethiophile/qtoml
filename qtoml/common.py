#!python3

from typing import Container, List, Pattern

class ParseState:
    """A parser state. Holds the entire input string, advances through it as
    requested. Also tracks line and column for error reporting.

    """
    def __init__(self, string: str, line: int = 1, col: int = 0) -> None:
        self._string = string
        self._index = 0
        self.line = line
        self.col = col
        self.start_inds: List[int] = []

    def at_string(self, s: str) -> bool:
        return self._string[self._index:self._index + len(s)] == s

    def at_re(self, re: Pattern) -> bool:
        return bool(re.match(self._string, pos=self._index))

    def at_end(self) -> bool:
        return self._index >= len(self._string)

    def len(self) -> int:
        return len(self._string) - self._index

    def get(self, n: int) -> str:
        return self._string[self._index:self._index + n]

    def advance_through_class(self, cls: Container[str]) -> str:
        i = self._index
        while True:
            if i < len(self._string) and self._string[i] in cls:
                i += 1
            else:
                break
        return self.advance(i - self._index)

    def advance_until(self, s: str) -> str:
        i = self._string.find(s, self._index)
        if i == -1:
            i = len(self._string)
        else:
            i += len(s)
        return self.advance(i - self._index)

    def advance(self, n: int) -> str:
        d = self._string[self._index:self._index + n]
        lc = d.count('\n')
        cc = len(d.rpartition("\n")[2])
        self.line += lc
        if lc > 0:
            self.col = cc
        else:
            self.col += cc
        self._index += n
        return d

    def backtrack(self, n: int) -> None:
        if self._index <= n:
            self._index = 0
            self.line = 1
            self.col = 0
            return
        d = self._string[self._index - n:self._index]
        lc = d.count('\n')
        self.line -= lc
        self._index -= n
        ls = self._string.rfind('\n', 0, self._index) + 1
        self.col = self._index - ls

    def capture_string(self) -> None:
        self.start_inds.append(self._index)

    def string_val(self) -> str:
        if len(self.start_inds) == 0:
            raise RuntimeError("tried string_val without captured index")
        i = self.start_inds.pop()
        rv = self._string[i:self._index]
        return rv

    def __repr__(self) -> str:
        return ("ParseState({}, line={}, col={})".
                format(repr(self._string), self.line, self.col))

class TOMLDecodeError(Exception):
    def __init__(self, msg: str, parse: ParseState) -> None:
        super().__init__("{} (line {}, column {})".
                         format(msg, parse.line, parse.col))

class TOMLEncodeError(Exception):
    pass
