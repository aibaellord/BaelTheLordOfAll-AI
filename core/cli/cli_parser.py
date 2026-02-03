#!/usr/bin/env python3
"""
BAEL - Command Line Interface Parser
Comprehensive CLI argument parsing and command handling system.

Features:
- Argument parsing with type validation
- Subcommand support
- Option groups
- Flag handling
- Environment variable integration
- Auto help generation
- Shell completion generation
- Input validation
- Configuration file support
- Interactive prompts
"""

import asyncio
import json
import os
import re
import shlex
import sys
import textwrap
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any, Callable, Dict, Generic, Iterator, List,
    Optional, Sequence, Set, Tuple, Type, TypeVar, Union
)

import logging
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ArgType(Enum):
    """Argument type."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    FILE = "file"
    DIRECTORY = "directory"
    CHOICE = "choice"
    LIST = "list"
    JSON = "json"


class ActionType(Enum):
    """Argument action type."""
    STORE = "store"
    STORE_TRUE = "store_true"
    STORE_FALSE = "store_false"
    APPEND = "append"
    COUNT = "count"
    HELP = "help"
    VERSION = "version"


class CompletionShell(Enum):
    """Shell completion type."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ArgumentDefinition:
    """Argument definition."""
    name: str
    short: Optional[str] = None
    arg_type: ArgType = ArgType.STRING
    action: ActionType = ActionType.STORE
    default: Any = None
    required: bool = False
    help: str = ""
    choices: Optional[List[Any]] = None
    env_var: Optional[str] = None
    metavar: Optional[str] = None
    nargs: Optional[Union[int, str]] = None
    validator: Optional[Callable[[Any], bool]] = None

    @property
    def is_flag(self) -> bool:
        return self.action in (ActionType.STORE_TRUE, ActionType.STORE_FALSE, ActionType.COUNT)

    @property
    def is_positional(self) -> bool:
        return not self.name.startswith('-')


@dataclass
class OptionGroup:
    """Group of related options."""
    name: str
    description: str = ""
    arguments: List[ArgumentDefinition] = field(default_factory=list)
    exclusive: bool = False


@dataclass
class Command:
    """Subcommand definition."""
    name: str
    description: str = ""
    help: str = ""
    arguments: List[ArgumentDefinition] = field(default_factory=list)
    groups: List[OptionGroup] = field(default_factory=list)
    handler: Optional[Callable] = None
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False


@dataclass
class ParseResult:
    """Result of parsing arguments."""
    command: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    positional: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_args: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def get(self, key: str, default: Any = None) -> Any:
        return self.args.get(key, default)


@dataclass
class ParserConfig:
    """Parser configuration."""
    prog: str = "bael"
    description: str = ""
    epilog: str = ""
    version: str = "1.0.0"
    add_help: bool = True
    add_version: bool = True
    allow_abbrev: bool = True
    config_file_arg: Optional[str] = None


# =============================================================================
# VALIDATORS
# =============================================================================

class Validator(ABC):
    """Abstract validator."""

    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate value. Returns (is_valid, error_message)."""
        pass


class RangeValidator(Validator):
    """Numeric range validator."""

    def __init__(
        self,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        try:
            num = float(value)

            if self.min_val is not None and num < self.min_val:
                return False, f"Value must be >= {self.min_val}"

            if self.max_val is not None and num > self.max_val:
                return False, f"Value must be <= {self.max_val}"

            return True, None
        except (ValueError, TypeError):
            return False, "Value must be a number"


class RegexValidator(Validator):
    """Regex pattern validator."""

    def __init__(self, pattern: str, message: str = "Invalid format"):
        self.pattern = re.compile(pattern)
        self.message = message

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        if self.pattern.match(str(value)):
            return True, None
        return False, self.message


class FileValidator(Validator):
    """File existence validator."""

    def __init__(self, must_exist: bool = True):
        self.must_exist = must_exist

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        path = str(value)

        if self.must_exist and not os.path.isfile(path):
            return False, f"File not found: {path}"

        return True, None


class DirectoryValidator(Validator):
    """Directory existence validator."""

    def __init__(self, must_exist: bool = True):
        self.must_exist = must_exist

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        path = str(value)

        if self.must_exist and not os.path.isdir(path):
            return False, f"Directory not found: {path}"

        return True, None


class LengthValidator(Validator):
    """String length validator."""

    def __init__(
        self,
        min_len: Optional[int] = None,
        max_len: Optional[int] = None
    ):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        length = len(str(value))

        if self.min_len is not None and length < self.min_len:
            return False, f"Value must be at least {self.min_len} characters"

        if self.max_len is not None and length > self.max_len:
            return False, f"Value must be at most {self.max_len} characters"

        return True, None


# =============================================================================
# TYPE CONVERTERS
# =============================================================================

class TypeConverter:
    """Type conversion utilities."""

    @staticmethod
    def convert(value: str, arg_type: ArgType) -> Any:
        """Convert string value to specified type."""
        if arg_type == ArgType.STRING:
            return value

        elif arg_type == ArgType.INTEGER:
            return int(value)

        elif arg_type == ArgType.FLOAT:
            return float(value)

        elif arg_type == ArgType.BOOLEAN:
            return value.lower() in ('true', 'yes', '1', 'on')

        elif arg_type == ArgType.FILE:
            return os.path.abspath(value)

        elif arg_type == ArgType.DIRECTORY:
            return os.path.abspath(value)

        elif arg_type == ArgType.JSON:
            return json.loads(value)

        elif arg_type == ArgType.LIST:
            return value.split(',')

        return value


# =============================================================================
# HELP FORMATTER
# =============================================================================

class HelpFormatter:
    """Format help text."""

    def __init__(self, width: int = 80, indent: int = 2):
        self.width = width
        self.indent = indent

    def format_usage(
        self,
        prog: str,
        arguments: List[ArgumentDefinition],
        commands: Optional[Dict[str, Command]] = None
    ) -> str:
        """Format usage line."""
        parts = [f"Usage: {prog}"]

        # Options
        flags = []
        options = []
        positionals = []

        for arg in arguments:
            if arg.is_positional:
                if arg.required:
                    positionals.append(arg.name.upper())
                else:
                    positionals.append(f"[{arg.name.upper()}]")
            elif arg.is_flag:
                flags.append(f"[{arg.name}]")
            else:
                if arg.required:
                    options.append(f"{arg.name} {arg.metavar or arg.name.upper()}")
                else:
                    options.append(f"[{arg.name} {arg.metavar or arg.name.upper()}]")

        if flags:
            parts.append(" ".join(flags[:3]))
            if len(flags) > 3:
                parts.append("...")

        for opt in options[:3]:
            parts.append(opt)

        if len(options) > 3:
            parts.append("...")

        if commands:
            parts.append("{command}")

        for pos in positionals:
            parts.append(pos)

        return " ".join(parts)

    def format_argument(self, arg: ArgumentDefinition) -> str:
        """Format single argument help."""
        names = []

        if arg.short:
            names.append(arg.short)
        if arg.name:
            names.append(arg.name)

        name_str = ", ".join(names)

        if not arg.is_flag and not arg.is_positional:
            name_str += f" {arg.metavar or arg.name.lstrip('-').upper()}"

        help_text = arg.help

        if arg.choices:
            help_text += f" (choices: {', '.join(str(c) for c in arg.choices)})"

        if arg.default is not None:
            help_text += f" [default: {arg.default}]"

        if arg.env_var:
            help_text += f" [env: {arg.env_var}]"

        return self._format_entry(name_str, help_text)

    def format_command(self, cmd: Command) -> str:
        """Format command help."""
        name = cmd.name
        if cmd.aliases:
            name += f" ({', '.join(cmd.aliases)})"

        return self._format_entry(name, cmd.description)

    def _format_entry(
        self,
        name: str,
        description: str,
        name_width: int = 24
    ) -> str:
        """Format a name-description entry."""
        indent = " " * self.indent

        if len(name) >= name_width:
            lines = [f"{indent}{name}"]
            wrapped = textwrap.wrap(description, self.width - name_width - self.indent)
            for line in wrapped:
                lines.append(f"{' ' * name_width}{line}")
            return '\n'.join(lines)
        else:
            padding = " " * (name_width - len(name))
            wrapped = textwrap.wrap(description, self.width - name_width - self.indent)

            if wrapped:
                lines = [f"{indent}{name}{padding}{wrapped[0]}"]
                for line in wrapped[1:]:
                    lines.append(f"{' ' * name_width}{line}")
                return '\n'.join(lines)
            else:
                return f"{indent}{name}"

    def format_group(self, group: OptionGroup) -> str:
        """Format option group."""
        lines = [f"\n{group.name}:"]

        if group.description:
            lines.append(f"  {group.description}")

        for arg in group.arguments:
            lines.append(self.format_argument(arg))

        return '\n'.join(lines)


# =============================================================================
# COMPLETION GENERATOR
# =============================================================================

class CompletionGenerator:
    """Generate shell completions."""

    def __init__(
        self,
        prog: str,
        arguments: List[ArgumentDefinition],
        commands: Optional[Dict[str, Command]] = None
    ):
        self.prog = prog
        self.arguments = arguments
        self.commands = commands or {}

    def generate(self, shell: CompletionShell) -> str:
        """Generate completion script for shell."""
        if shell == CompletionShell.BASH:
            return self._generate_bash()
        elif shell == CompletionShell.ZSH:
            return self._generate_zsh()
        elif shell == CompletionShell.FISH:
            return self._generate_fish()
        else:
            return ""

    def _generate_bash(self) -> str:
        """Generate bash completion."""
        options = []
        commands = list(self.commands.keys())

        for arg in self.arguments:
            if arg.name.startswith('-'):
                options.append(arg.name)
            if arg.short:
                options.append(arg.short)

        return f'''
# Bash completion for {self.prog}
_{self.prog}_completions()
{{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local options="{' '.join(options)}"
    local commands="{' '.join(commands)}"

    if [[ ${{cur}} == -* ]]; then
        COMPREPLY=( $(compgen -W "${{options}}" -- "${{cur}}") )
    else
        COMPREPLY=( $(compgen -W "${{commands}}" -- "${{cur}}") )
    fi
}}
complete -F _{self.prog}_completions {self.prog}
'''

    def _generate_zsh(self) -> str:
        """Generate zsh completion."""
        lines = [
            f"#compdef {self.prog}",
            "",
            "_arguments \\"
        ]

        for arg in self.arguments:
            if arg.name.startswith('-'):
                line = f"  '{arg.name}[{arg.help}]'"
                if arg.short:
                    line = f"  '({arg.short} {arg.name})'{arg.short}'[{arg.help}]'"
                lines.append(line + " \\")

        if self.commands:
            lines.append("  '1:command:->cmds' \\")

        lines.append("  '*::arg:->args'")
        lines.append("")
        lines.append(f"# Source: {self.prog} completion")

        return '\n'.join(lines)

    def _generate_fish(self) -> str:
        """Generate fish completion."""
        lines = [f"# Fish completion for {self.prog}"]

        for arg in self.arguments:
            if arg.name.startswith('--'):
                lines.append(
                    f"complete -c {self.prog} -l {arg.name[2:]} "
                    f"-d '{arg.help}'"
                )
            if arg.short and arg.short.startswith('-'):
                lines.append(
                    f"complete -c {self.prog} -s {arg.short[1:]} "
                    f"-d '{arg.help}'"
                )

        for name, cmd in self.commands.items():
            lines.append(
                f"complete -c {self.prog} -n '__fish_use_subcommand' "
                f"-a '{name}' -d '{cmd.description}'"
            )

        return '\n'.join(lines)


# =============================================================================
# CLI PARSER
# =============================================================================

class CLIParser:
    """
    Comprehensive CLI Parser for BAEL.

    Provides argument parsing, subcommands, and help generation.
    """

    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.arguments: List[ArgumentDefinition] = []
        self.groups: List[OptionGroup] = []
        self.commands: Dict[str, Command] = {}
        self.formatter = HelpFormatter()
        self._validators: Dict[str, List[Validator]] = defaultdict(list)
        self._parsed: Optional[ParseResult] = None

        if self.config.add_help:
            self.add_argument(
                "--help", "-h",
                action=ActionType.HELP,
                help="Show this help message and exit"
            )

        if self.config.add_version:
            self.add_argument(
                "--version", "-V",
                action=ActionType.VERSION,
                help="Show program version and exit"
            )

    # -------------------------------------------------------------------------
    # ARGUMENT DEFINITION
    # -------------------------------------------------------------------------

    def add_argument(
        self,
        name: str,
        short: Optional[str] = None,
        arg_type: ArgType = ArgType.STRING,
        action: ActionType = ActionType.STORE,
        default: Any = None,
        required: bool = False,
        help: str = "",
        choices: Optional[List[Any]] = None,
        env_var: Optional[str] = None,
        metavar: Optional[str] = None,
        nargs: Optional[Union[int, str]] = None,
        validator: Optional[Callable[[Any], bool]] = None
    ) -> "CLIParser":
        """Add an argument."""
        arg = ArgumentDefinition(
            name=name,
            short=short,
            arg_type=arg_type,
            action=action,
            default=default,
            required=required,
            help=help,
            choices=choices,
            env_var=env_var,
            metavar=metavar,
            nargs=nargs,
            validator=validator
        )

        self.arguments.append(arg)
        return self

    def add_group(
        self,
        name: str,
        description: str = "",
        exclusive: bool = False
    ) -> OptionGroup:
        """Add an option group."""
        group = OptionGroup(
            name=name,
            description=description,
            exclusive=exclusive
        )
        self.groups.append(group)
        return group

    def add_command(
        self,
        name: str,
        description: str = "",
        help: str = "",
        aliases: Optional[List[str]] = None,
        hidden: bool = False
    ) -> Command:
        """Add a subcommand."""
        cmd = Command(
            name=name,
            description=description,
            help=help,
            aliases=aliases or [],
            hidden=hidden
        )

        self.commands[name] = cmd

        for alias in cmd.aliases:
            self.commands[alias] = cmd

        return cmd

    def add_validator(self, arg_name: str, validator: Validator) -> "CLIParser":
        """Add a validator for an argument."""
        self._validators[arg_name].append(validator)
        return self

    # -------------------------------------------------------------------------
    # PARSING
    # -------------------------------------------------------------------------

    def parse(self, args: Optional[List[str]] = None) -> ParseResult:
        """Parse arguments."""
        if args is None:
            args = sys.argv[1:]

        result = ParseResult(raw_args=list(args))

        # Apply defaults
        for arg in self.arguments:
            if arg.default is not None:
                result.args[arg.name.lstrip('-')] = arg.default

        # Load environment variables
        self._load_env_vars(result)

        # Parse arguments
        self._parse_args(args, result)

        # Validate
        self._validate(result)

        self._parsed = result
        return result

    def _parse_args(
        self,
        args: List[str],
        result: ParseResult
    ) -> None:
        """Parse argument list."""
        i = 0
        positional_idx = 0
        positional_args = [a for a in self.arguments if a.is_positional]

        while i < len(args):
            arg = args[i]

            # Check for help
            if arg in ('-h', '--help'):
                self.print_help()
                sys.exit(0)

            # Check for version
            if arg in ('-V', '--version'):
                print(f"{self.config.prog} {self.config.version}")
                sys.exit(0)

            # Check for subcommand
            if not arg.startswith('-') and arg in self.commands:
                result.command = arg
                # Parse remaining args with subcommand parser
                cmd = self.commands[arg]
                remaining = args[i + 1:]
                self._parse_command_args(cmd, remaining, result)
                break

            # Option argument
            if arg.startswith('--'):
                i = self._parse_long_option(args, i, result)
            elif arg.startswith('-'):
                i = self._parse_short_option(args, i, result)
            else:
                # Positional
                if positional_idx < len(positional_args):
                    pa = positional_args[positional_idx]
                    value = self._convert_value(arg, pa.arg_type)
                    result.args[pa.name] = value
                    positional_idx += 1
                else:
                    result.positional.append(arg)
                i += 1

    def _parse_long_option(
        self,
        args: List[str],
        i: int,
        result: ParseResult
    ) -> int:
        """Parse long option (--option)."""
        arg = args[i]

        # Handle --option=value
        if '=' in arg:
            name, value = arg.split('=', 1)
        else:
            name = arg
            value = None

        # Find matching argument
        arg_def = self._find_argument(name)

        if arg_def is None:
            if self.config.allow_abbrev:
                arg_def = self._find_abbreviated(name)

            if arg_def is None:
                result.errors.append(f"Unknown option: {name}")
                return i + 1

        # Process argument
        return self._process_argument(args, i, arg_def, value, result)

    def _parse_short_option(
        self,
        args: List[str],
        i: int,
        result: ParseResult
    ) -> int:
        """Parse short option (-o)."""
        arg = args[i]
        name = arg

        arg_def = self._find_argument(name)

        if arg_def is None:
            # Try bundled options (-abc)
            if len(arg) > 2:
                for char in arg[1:]:
                    short_arg = f"-{char}"
                    ad = self._find_argument(short_arg)
                    if ad and ad.is_flag:
                        self._set_flag(ad, result)
                    else:
                        result.errors.append(f"Unknown option: {short_arg}")
                return i + 1

            result.errors.append(f"Unknown option: {name}")
            return i + 1

        return self._process_argument(args, i, arg_def, None, result)

    def _process_argument(
        self,
        args: List[str],
        i: int,
        arg_def: ArgumentDefinition,
        value: Optional[str],
        result: ParseResult
    ) -> int:
        """Process a matched argument."""
        key = arg_def.name.lstrip('-')

        if arg_def.action == ActionType.STORE_TRUE:
            result.args[key] = True
            return i + 1

        elif arg_def.action == ActionType.STORE_FALSE:
            result.args[key] = False
            return i + 1

        elif arg_def.action == ActionType.COUNT:
            result.args[key] = result.args.get(key, 0) + 1
            return i + 1

        elif arg_def.action == ActionType.APPEND:
            if value is None and i + 1 < len(args):
                value = args[i + 1]
                i += 1

            if value is not None:
                converted = self._convert_value(value, arg_def.arg_type)
                if key not in result.args:
                    result.args[key] = []
                result.args[key].append(converted)

            return i + 1

        else:  # STORE
            if value is None and i + 1 < len(args):
                value = args[i + 1]
                i += 1

            if value is not None:
                converted = self._convert_value(value, arg_def.arg_type)

                # Validate choices
                if arg_def.choices and converted not in arg_def.choices:
                    result.errors.append(
                        f"Invalid choice '{converted}' for {arg_def.name}. "
                        f"Choose from: {', '.join(str(c) for c in arg_def.choices)}"
                    )
                else:
                    result.args[key] = converted

            return i + 1

    def _parse_command_args(
        self,
        cmd: Command,
        args: List[str],
        result: ParseResult
    ) -> None:
        """Parse subcommand arguments."""
        i = 0

        while i < len(args):
            arg = args[i]

            if arg.startswith('-'):
                # Find in command arguments
                arg_def = None
                for a in cmd.arguments:
                    if a.name == arg or a.short == arg:
                        arg_def = a
                        break

                if arg_def is None:
                    # Check global arguments
                    arg_def = self._find_argument(arg)

                if arg_def:
                    i = self._process_argument(args, i, arg_def, None, result)
                else:
                    result.errors.append(f"Unknown option for {cmd.name}: {arg}")
                    i += 1
            else:
                result.positional.append(arg)
                i += 1

    def _find_argument(self, name: str) -> Optional[ArgumentDefinition]:
        """Find argument by name or short form."""
        for arg in self.arguments:
            if arg.name == name or arg.short == name:
                return arg
        return None

    def _find_abbreviated(self, name: str) -> Optional[ArgumentDefinition]:
        """Find argument by abbreviation."""
        matches = []

        for arg in self.arguments:
            if arg.name.startswith(name):
                matches.append(arg)

        if len(matches) == 1:
            return matches[0]

        return None

    def _set_flag(self, arg_def: ArgumentDefinition, result: ParseResult) -> None:
        """Set a flag value."""
        key = arg_def.name.lstrip('-')

        if arg_def.action == ActionType.STORE_TRUE:
            result.args[key] = True
        elif arg_def.action == ActionType.STORE_FALSE:
            result.args[key] = False
        elif arg_def.action == ActionType.COUNT:
            result.args[key] = result.args.get(key, 0) + 1

    def _convert_value(self, value: str, arg_type: ArgType) -> Any:
        """Convert value to appropriate type."""
        try:
            return TypeConverter.convert(value, arg_type)
        except (ValueError, json.JSONDecodeError):
            return value

    def _load_env_vars(self, result: ParseResult) -> None:
        """Load values from environment variables."""
        for arg in self.arguments:
            if arg.env_var:
                env_value = os.environ.get(arg.env_var)
                if env_value is not None:
                    key = arg.name.lstrip('-')
                    result.args[key] = self._convert_value(env_value, arg.arg_type)

    def _validate(self, result: ParseResult) -> None:
        """Validate parsed arguments."""
        # Check required arguments
        for arg in self.arguments:
            if arg.required and not arg.is_positional:
                key = arg.name.lstrip('-')
                if key not in result.args or result.args[key] is None:
                    result.errors.append(f"Required argument missing: {arg.name}")

        # Run validators
        for arg_name, validators in self._validators.items():
            if arg_name in result.args:
                value = result.args[arg_name]
                for validator in validators:
                    is_valid, error = validator.validate(value)
                    if not is_valid:
                        result.errors.append(f"{arg_name}: {error}")

        # Check exclusive groups
        for group in self.groups:
            if group.exclusive:
                found = []
                for arg in group.arguments:
                    key = arg.name.lstrip('-')
                    if key in result.args and result.args[key] is not None:
                        found.append(arg.name)

                if len(found) > 1:
                    result.errors.append(
                        f"Arguments are mutually exclusive: {', '.join(found)}"
                    )

    # -------------------------------------------------------------------------
    # HELP
    # -------------------------------------------------------------------------

    def print_help(self) -> None:
        """Print help message."""
        print(self.format_help())

    def format_help(self) -> str:
        """Format help message."""
        lines = []

        # Usage
        usage = self.formatter.format_usage(
            self.config.prog,
            self.arguments,
            self.commands if self.commands else None
        )
        lines.append(usage)
        lines.append("")

        # Description
        if self.config.description:
            lines.append(self.config.description)
            lines.append("")

        # Positional arguments
        positional = [a for a in self.arguments if a.is_positional]
        if positional:
            lines.append("Positional arguments:")
            for arg in positional:
                lines.append(self.formatter.format_argument(arg))
            lines.append("")

        # Options
        options = [a for a in self.arguments if not a.is_positional]
        if options:
            lines.append("Options:")
            for arg in options:
                lines.append(self.formatter.format_argument(arg))
            lines.append("")

        # Option groups
        for group in self.groups:
            lines.append(self.formatter.format_group(group))

        # Commands
        if self.commands:
            visible_commands = {
                k: v for k, v in self.commands.items()
                if not v.hidden and k == v.name
            }

            if visible_commands:
                lines.append("Commands:")
                for name, cmd in sorted(visible_commands.items()):
                    lines.append(self.formatter.format_command(cmd))
                lines.append("")

        # Epilog
        if self.config.epilog:
            lines.append(self.config.epilog)

        return '\n'.join(lines)

    # -------------------------------------------------------------------------
    # COMPLETIONS
    # -------------------------------------------------------------------------

    def generate_completion(self, shell: CompletionShell) -> str:
        """Generate shell completion script."""
        generator = CompletionGenerator(
            self.config.prog,
            self.arguments,
            self.commands
        )
        return generator.generate(shell)

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    async def run(self, args: Optional[List[str]] = None) -> int:
        """Parse arguments and run command handler."""
        result = self.parse(args)

        if not result.is_valid:
            for error in result.errors:
                print(f"Error: {error}", file=sys.stderr)
            print(f"Try '{self.config.prog} --help' for more information.")
            return 1

        if result.command and result.command in self.commands:
            cmd = self.commands[result.command]
            if cmd.handler:
                if asyncio.iscoroutinefunction(cmd.handler):
                    return await cmd.handler(result)
                else:
                    return cmd.handler(result)

        return 0

    def get_result(self) -> Optional[ParseResult]:
        """Get last parse result."""
        return self._parsed


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    """Demonstrate the CLI Parser."""
    print("=" * 70)
    print("BAEL - CLI PARSER DEMO")
    print("Comprehensive Command Line Interface System")
    print("=" * 70)
    print()

    # 1. Basic Parser
    print("1. BASIC PARSER:")
    print("-" * 40)

    parser = CLIParser(ParserConfig(
        prog="bael",
        description="BAEL - The Lord of All AI Agents",
        version="1.0.0"
    ))

    parser.add_argument("--verbose", "-v", action=ActionType.STORE_TRUE, help="Enable verbose output")
    parser.add_argument("--config", "-c", arg_type=ArgType.FILE, help="Configuration file")
    parser.add_argument("--output", "-o", default="output.txt", help="Output file")
    parser.add_argument("--format", "-f", choices=["json", "yaml", "xml"], default="json", help="Output format")
    parser.add_argument("--workers", "-w", arg_type=ArgType.INTEGER, default=4, help="Number of workers")

    print(f"   Parser created with prog: {parser.config.prog}")
    print(f"   Arguments defined: {len(parser.arguments)}")
    print()

    # 2. Parse Arguments
    print("2. PARSE ARGUMENTS:")
    print("-" * 40)

    test_args = ["--verbose", "--format", "yaml", "-w", "8", "--output", "result.txt"]
    result = parser.parse(test_args)

    print(f"   Input: {test_args}")
    print(f"   Parsed args: {result.args}")
    print(f"   Is valid: {result.is_valid}")
    print()

    # 3. Subcommands
    print("3. SUBCOMMANDS:")
    print("-" * 40)

    parser2 = CLIParser(ParserConfig(prog="bael", description="BAEL CLI"))

    # Add commands
    init_cmd = parser2.add_command("init", description="Initialize BAEL project")
    init_cmd.arguments.append(ArgumentDefinition(
        name="--template", short="-t",
        help="Project template to use"
    ))

    run_cmd = parser2.add_command("run", description="Run BAEL agent", aliases=["start"])
    run_cmd.arguments.append(ArgumentDefinition(
        name="--agent", short="-a",
        required=True,
        help="Agent to run"
    ))

    deploy_cmd = parser2.add_command("deploy", description="Deploy to cloud")

    print(f"   Commands: {list(parser2.commands.keys())}")

    result2 = parser2.parse(["run", "-a", "orchestrator"])
    print(f"   Input: ['run', '-a', 'orchestrator']")
    print(f"   Command: {result2.command}")
    print(f"   Args: {result2.args}")
    print()

    # 4. Option Groups
    print("4. OPTION GROUPS:")
    print("-" * 40)

    parser3 = CLIParser(ParserConfig(prog="bael"))

    output_group = parser3.add_group("Output options", "Control output behavior")
    output_group.arguments.append(ArgumentDefinition(
        name="--quiet", "-q",
        action=ActionType.STORE_TRUE,
        help="Suppress output"
    ))
    output_group.arguments.append(ArgumentDefinition(
        name="--verbose", "-v",
        action=ActionType.COUNT,
        help="Increase verbosity"
    ))

    print(f"   Created group: {output_group.name}")
    print(f"   Arguments in group: {len(output_group.arguments)}")
    print()

    # 5. Validators
    print("5. VALIDATORS:")
    print("-" * 40)

    parser4 = CLIParser(ParserConfig(prog="bael"))
    parser4.add_argument("--port", "-p", arg_type=ArgType.INTEGER, help="Port number")
    parser4.add_validator("port", RangeValidator(1, 65535))

    # Valid port
    result4a = parser4.parse(["--port", "8080"])
    print(f"   Port 8080: valid={result4a.is_valid}")

    # Invalid port
    result4b = parser4.parse(["--port", "70000"])
    print(f"   Port 70000: valid={result4b.is_valid}, errors={result4b.errors}")
    print()

    # 6. Type Conversion
    print("6. TYPE CONVERSION:")
    print("-" * 40)

    parser5 = CLIParser(ParserConfig(prog="bael"))
    parser5.add_argument("--count", arg_type=ArgType.INTEGER, help="Count")
    parser5.add_argument("--ratio", arg_type=ArgType.FLOAT, help="Ratio")
    parser5.add_argument("--enabled", arg_type=ArgType.BOOLEAN, help="Enabled")
    parser5.add_argument("--tags", arg_type=ArgType.LIST, help="Tags")
    parser5.add_argument("--data", arg_type=ArgType.JSON, help="JSON data")

    result5 = parser5.parse([
        "--count", "42",
        "--ratio", "3.14",
        "--enabled", "true",
        "--tags", "ai,ml,nlp",
        "--data", '{"key": "value"}'
    ])

    print(f"   count: {result5.args.get('count')} (type: {type(result5.args.get('count')).__name__})")
    print(f"   ratio: {result5.args.get('ratio')} (type: {type(result5.args.get('ratio')).__name__})")
    print(f"   enabled: {result5.args.get('enabled')} (type: {type(result5.args.get('enabled')).__name__})")
    print(f"   tags: {result5.args.get('tags')} (type: {type(result5.args.get('tags')).__name__})")
    print(f"   data: {result5.args.get('data')} (type: {type(result5.args.get('data')).__name__})")
    print()

    # 7. Environment Variables
    print("7. ENVIRONMENT VARIABLES:")
    print("-" * 40)

    os.environ["BAEL_DEBUG"] = "true"

    parser6 = CLIParser(ParserConfig(prog="bael"))
    parser6.add_argument("--debug", arg_type=ArgType.BOOLEAN, env_var="BAEL_DEBUG", help="Debug mode")

    result6 = parser6.parse([])
    print(f"   BAEL_DEBUG env var: {os.environ.get('BAEL_DEBUG')}")
    print(f"   --debug value: {result6.args.get('debug')}")

    del os.environ["BAEL_DEBUG"]
    print()

    # 8. Help Generation
    print("8. HELP GENERATION:")
    print("-" * 40)

    help_text = parser.format_help()
    lines = help_text.split('\n')[:15]
    print('\n'.join(lines))
    print("...")
    print()

    # 9. Shell Completion
    print("9. SHELL COMPLETION:")
    print("-" * 40)

    bash_completion = parser.generate_completion(CompletionShell.BASH)
    print(f"   Bash completion ({len(bash_completion)} chars):")
    print(f"   {bash_completion[:200]}...")
    print()

    # 10. Append Action
    print("10. APPEND ACTION:")
    print("-" * 40)

    parser7 = CLIParser(ParserConfig(prog="bael"))
    parser7.add_argument("--include", "-i", action=ActionType.APPEND, help="Include path")

    result7 = parser7.parse(["-i", "path1", "-i", "path2", "-i", "path3"])
    print(f"   Input: ['-i', 'path1', '-i', 'path2', '-i', 'path3']")
    print(f"   include: {result7.args.get('include')}")
    print()

    # 11. Count Action
    print("11. COUNT ACTION:")
    print("-" * 40)

    parser8 = CLIParser(ParserConfig(prog="bael"))
    parser8.add_argument("--verbose", "-v", action=ActionType.COUNT, default=0, help="Verbosity")

    result8 = parser8.parse(["-v", "-v", "-v"])
    print(f"   Input: ['-v', '-v', '-v']")
    print(f"   verbose: {result8.args.get('verbose')}")
    print()

    # 12. Positional Arguments
    print("12. POSITIONAL ARGUMENTS:")
    print("-" * 40)

    parser9 = CLIParser(ParserConfig(prog="bael"))
    parser9.add_argument("source", help="Source file")
    parser9.add_argument("destination", help="Destination file")
    parser9.add_argument("--force", "-f", action=ActionType.STORE_TRUE, help="Force overwrite")

    result9 = parser9.parse(["input.txt", "output.txt", "--force"])
    print(f"   Input: ['input.txt', 'output.txt', '--force']")
    print(f"   source: {result9.args.get('source')}")
    print(f"   destination: {result9.args.get('destination')}")
    print(f"   force: {result9.args.get('force')}")
    print()

    # 13. Error Handling
    print("13. ERROR HANDLING:")
    print("-" * 40)

    parser10 = CLIParser(ParserConfig(prog="bael"))
    parser10.add_argument("--required", required=True, help="Required argument")

    result10 = parser10.parse([])
    print(f"   Input: []")
    print(f"   Is valid: {result10.is_valid}")
    print(f"   Errors: {result10.errors}")
    print()

    print("=" * 70)
    print("DEMO COMPLETE - CLI Parser Ready")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo())
