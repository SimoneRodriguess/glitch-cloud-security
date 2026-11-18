"""GPL-3.0+: command-aware extension of the archived GLITCH visitor.

No shell/Ruby command is executed. Source slices are used only for opaque IR
command blocks or literal command fields whose value was lost during lowering.
"""
import os
import re
import shlex

from glitch.analysis.rules import Error
from glitch.analysis.security import SecurityVisitor

DATABASE_COMMANDS = {"mysql", "mysqladmin", "mysqldump", "mysqlcheck"}
COMMAND_FIELDS = {"cmd", "command", "shell", "execute", "only_if", "not_if", "code", "block"}
FIELD_PATTERN = re.compile(r"(?:cmd|command|shell|execute|only_if|not_if|code|block|[A-Za-z_]\w*_(?:cmd|command))$")


def explicit_root_command(text):
    """Recognize a literal root user in a supported executable command prefix.

    Stop at -e/--execute: remaining SQL is not shell syntax and is not parsed.
    Unresolved users are never inferred. Leading env assignments are allowed;
    arbitrary wrappers and runtime option files are outside this rule's scope.
    """
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = []
    try:
        for token in lexer:
            if token in {"-e", "--execute"} or token.startswith("--execute="):
                break
            tokens.append(token)
    except ValueError:
        return False
    # Commands can be chained. Never scan inside a quoted token such as
    # echo "mysql -uroot" or a text field mentioning an executable.
    groups, group = [], []
    for token in tokens:
        if token and all(c in ";&|" for c in token):
            if group: groups.append(group)
            group = []
        else:
            group.append(token)
    if group: groups.append(group)
    for group in groups:
        while group and re.match(r"^[A-Za-z_]\w*=", group[0]):
            group = group[1:]
        if not group or os.path.basename(group[0]) not in DATABASE_COMMANDS:
            continue
        user, i = None, 1
        while i < len(group):
            token = group[i]
            if token in {"-u", "--user"}:
                user = group[i + 1] if i + 1 < len(group) else None
                i += 2
            elif token.startswith("--user="):
                user = token.partition("=")[2]
                i += 1
            elif token.startswith("-u") and len(token) > 2:
                user = token[2:]
                i += 1
            else:
                i += 1
        if user == "root":
            return True
    return False


def _unquote_literal(text):
    text = text.strip()
    if text[:1] in ["'", '"']:
        quote = text[0]
        # Ruby outer literal quotes are removed; internal SQL is not evaluated.
        end = text.rfind(quote)
        return text[1:end] if end > 0 else text[1:]
    return text


def command_lines(element):
    """Return original source lines with literal command evidence.

    Match field roles and explicit Ruby shell-execution wrappers, not arbitrary
    occurrences of 'root' or 'mysql' in free text. Opaque block source recovery
    is lexical and bounded, not complete Ruby or shell semantic analysis.
    """
    name = element.name.rsplit(".", 1)[-1].strip().lower()
    command_context = bool(FIELD_PATTERN.fullmatch(name))
    source = element.code or ""
    lines = source.splitlines()
    found = []
    for offset, line in enumerate(lines):
        stripped = line.strip()
        candidates = []
        # Direct script lines inside an IR code/block attribute.
        if command_context:
            candidates.append(stripped)
        # Literal command-valued assignments/attributes, including values that
        # GLITCH lowers incorrectly to an interpolation's function-call node.
        match = re.match(r"([A-Za-z_]\w*)\s*(?:=>\s*|=\s*|:\s*|\s+)(.*)", stripped)
        if match and FIELD_PATTERN.fullmatch(match[1].lower()):
            candidates.append(_unquote_literal(match[2]))
        # Explicit Ruby system/exec/spawn calls in opaque command-block slices.
        wrapper = re.search(r"\b(?:system|exec|spawn)\s*(?:\(\s*)?(['\"])(.*)", stripped)
        if wrapper and command_context:
            candidates.append(_unquote_literal(wrapper[1] + wrapper[2]))
        shell_literal = re.search(r"%x[\[({](.*)", stripped)
        if shell_literal and command_context:
            candidates.append(shell_literal[1].rstrip("])}"))
        if command_context and stripped.startswith("`"):
            candidates.append(stripped.strip("`"))
        if any(explicit_root_command(candidate) for candidate in candidates):
            found.append(element.line + offset)
    if not source and command_context and isinstance(element.value, str):
        for offset, line in enumerate(element.value.splitlines()):
            if explicit_root_command(line):
                found.append(element.line + offset)
    return sorted(set(found))


class CommandAwareVisitor(SecurityVisitor):
    def _add_command_reports(self, element, file, original):
        for line in command_lines(element):
            if not any(error.code == "sec_def_admin" and error.line == line for error in original):
                error = Error("sec_def_admin", element, file, repr(element))
                error.line = line
                original.append(error)
        return original

    def check_attribute(self, attribute, file):
        return self._add_command_reports(attribute, file, super().check_attribute(attribute, file))

    def check_variable(self, variable, file):
        return self._add_command_reports(variable, file, super().check_variable(variable, file))


class NaiveCommandVisitor(SecurityVisitor):
    """Deliberately weak, frozen substring ablation; not a competing tool."""
    def _add_naive(self, element, file, original):
        text = element.code or str(element.value)
        for offset, line in enumerate(text.splitlines()):
            if "mysql" in line.lower() and "root" in line.lower():
                error = Error("sec_def_admin", element, file, repr(element))
                error.line = element.line + offset
                original.append(error)
        return original

    def check_attribute(self, attribute, file):
        return self._add_naive(attribute, file, super().check_attribute(attribute, file))

    def check_variable(self, variable, file):
        return self._add_naive(variable, file, super().check_variable(variable, file))
