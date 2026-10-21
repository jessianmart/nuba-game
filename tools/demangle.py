"""Minimal Itanium C++ ABI demangler for CyberConnect symbol style.

Handles the constructs actually used by libultimateninjastorm.so: nested names,
substitutions (S_, S0_, St...), pointer/reference/const types, builtin types and
function parameter lists. Anything it cannot resolve is returned unchanged.
"""

import re
import sys

QUAL = {"r": " &", "V": " volatile", "K": " const", "R": " &&"}
BUILTIN = {
    "v": "void", "w": "wchar_t", "b": "bool", "c": "char", "a": "signed char",
    "h": "unsigned char", "s": "short", "t": "unsigned short", "i": "int",
    "j": "unsigned int", "l": "long", "m": "unsigned long", "x": "long long",
    "y": "unsigned long long", "n": "__int128", "o": "unsigned __int128",
    "f": "float", "d": "double", "e": "long double", "g": "__float128",
    "z": "...", "Di": "char32_t", "Ds": "char16_t", "Du": "char8_t",
}
STD = {"St": "std", "Sa": "std::allocator", "Sb": "std::basic_string",
       "Ss": "std::string", "Si": "std::istream", "So": "std::ostream",
       "Sd": "std::iostream", "Sm": "std::map", "Sv": "std::vector"}


class Ctx:
    def __init__(self, s):
        self.s = s
        self.i = 0
        self.subs = []

    def eof(self):
        return self.i >= len(self.s)

    def peek(self, n=1):
        return self.s[self.i:self.i + n]

    def take(self, n=1):
        v = self.s[self.i:self.i + n]
        self.i += n
        return v

    def expect(self, ch):
        if self.peek() == ch:
            self.i += 1
            return True
        return False

    def fail(self):
        raise ValueError("demangle")


def number(ctx):
    j = ctx.i
    while j < len(ctx.s) and ctx.s[j].isdigit():
        j += 1
    if j == ctx.i:
        ctx.fail()
    return int(ctx.s[ctx.i:j]), j


def qualifiers(ctx):
    acc = []
    while ctx.peek(1) and ctx.peek(1)[0] in QUAL:
        acc.append(QUAL[ctx.take(1)])
    return "".join(acc)


def source_name(ctx):
    n, j = number(ctx)
    ctx.i = j
    return ctx.take(n)


def template_args(ctx):
    if ctx.peek(1) != "I":
        return ""
    ctx.take(1)
    args = []
    while not ctx.eof() and ctx.peek(1) != "E":
        args.append(parse_type(ctx))
    ctx.expect("E")
    return "<" + ", ".join(args) + ">"


def parse_name(ctx):
    """Returns (qualified-prefix, unqualified-tail, trailing-cv)."""
    q = qualifiers(ctx)
    if ctx.peek(1) == "N":
        ctx.take(1)
        comps = []
        while not ctx.eof() and ctx.peek(1) != "E":
            q2 = qualifiers(ctx)
            if ctx.peek(1) == "S":
                ctx.take(1)
                comp = substitution(ctx)
            else:
                comp = source_name(ctx)
            if ctx.peek(1) == "I":
                comp += template_args(ctx)
            full = "::" + q2 + comp if comps else q2 + comp
            comps.append(comp)
            ctx.subs.append("".join(comps) and "::".join(comps))
            del full
        ctx.expect("E")
        tail = comps[-1] if comps else ""
        prefix = "::".join(comps[:-1])
        cv = ""
    elif ctx.peek(1) == "S":
        ctx.take(1)
        tail = substitution(ctx)
        prefix = ""
        cv = ""
    elif ctx.peek(1) == "Z":
        ctx.fail()
    else:
        tail = source_name(ctx)
        prefix = ""
        cv = ""
    return prefix, tail, cv


def substitution(ctx):
    tag = ctx.take(1)
    if tag == "_":
        idx = 0
    elif tag.isdigit():
        n = int(tag)
        if ctx.peek(1) == "_":
            ctx.take(1)
        idx = n + 1
        if n == 0 and ctx.s[ctx.i - 1] == "_":
            idx = 0
        # S0_ -> index 1, S0_0 -> index 2 ...
        idx = n
    else:
        ctx.fail()
    if idx >= len(ctx.subs):
        ctx.fail()
    return ctx.subs[-1 - idx] if False else ctx.subs[idx]


def parse_type(ctx):
    c = ctx.peek(1)
    if c in BUILTIN:
        ctx.take(1)
        return BUILTIN[c]
    if c == "P":
        ctx.take(1)
        return parse_type(ctx) + "*"
    if c == "R":
        ctx.take(1)
        return parse_type(ctx) + "&"
    if c == "O":
        ctx.take(1)
        return parse_type(ctx) + "&&"
    if c == "K":
        ctx.take(1)
        return parse_type(ctx) + " const"
    if c == "V":
        ctx.take(1)
        return parse_type(ctx) + " volatile"
    if c == "C":
        ctx.take(1)
        return parse_type(ctx) + " complex"
    if c == "D":
        ctx.take(1)
        d = ctx.take(1)
        inner = parse_type(ctx)
        ctx.expect("E")
        return inner + ("[]" if d == "A" else "[__bound]")
    if c == "T":
        ctx.take(1)
        q = qualifiers(ctx)
        inner = parse_type(ctx)
        ctx.expect("E")
        return inner + q
    if c == "F":
        ctx.fail()
    if c in "NS":
        ctx.i -= 0
        if c == "S" and ctx.peek(2) in STD:
            key = ctx.take(2)
            return STD[key]
        prefix, tail, cv = parse_name(ctx)
        if ctx.peek(1) == "I":
            tail += template_args(ctx)
        return prefix + "::" + tail if prefix else tail
    if c.isdigit():
        ctx.i -= 0
        _, tail, _ = parse_name(ctx)
        if ctx.peek(1) == "I":
            tail += template_args(ctx)
        return tail
    ctx.fail()


def demangle(sym):
    if not sym.startswith("_Z"):
        return sym
    ctx = Ctx(sym[2:])
    try:
        prefix, tail, cv = parse_name(ctx)
        if ctx.peek(1) == "E":
            ctx.take(1)
            name = (prefix + "::" + tail) if prefix else tail
            return tail + cv + (("::" + prefix) if prefix else "")
        args = []
        while not ctx.eof() and ctx.peek(1) != "E":
            before = ctx.i
            args.append(parse_type(ctx))
            if ctx.i == before:
                break
        name = (prefix + "::" + tail) if prefix else tail
        if cv:
            name = tail + cv + (("::" + prefix) if prefix else "")
        return name + "(" + ", ".join(args) + ")"
    except (ValueError, IndexError):
        return sym


if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if line:
            print(demangle(line))