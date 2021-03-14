#! /usr/bin/env python

# This is how you know it's gonna be good
import ast
import code
import inspect
import sys

try:
    import readline  # makes arrow keys work
except ImportError:
    pass

import textwrap
from typing import *


FrameVarsT = Dict[str, Any]
FrameT = Any
ExpressionFill = str
StatementFill = str
StatementsFill = List[str]
ValueT = Any
CodeFillSingleT = Union[ExpressionFill, StatementFill]
CodeFillT = Union[ExpressionFill, StatementFill, StatementsFill]


__all__ = [
    'set_placeholder',
    'Placeholder',
    'ExpressionPlaceholder',
    'StatementPlaceholder',
    'MultilinePlaceholder',
]


default_session: Dict[Tuple[str, str], 'PlaceholderSession'] = {}
default_rewrite_ctx: Dict[str, 'RewriteContext'] = {}


def _find_all(s: str, sub: str, start: int = 0):
    res = []
    idx = start
    while True:
        idx = s.find(sub, idx)
        if idx == -1:
            return res
        else:
            res.append(idx)
        idx += 1


def inject_vars(frame: FrameT, updates: FrameVarsT) -> None:
    for k, v in updates.items():
        frame.f_locals[k] = v


def get_frame_vars(frame):
    return {**frame.f_globals, **frame.f_locals}


class ValidInterpreter(code.InteractiveConsole):
    def showtraceback(self):
        raise


class PlaceholderSession:
    _placeholder_msg: str

    def __init__(self):
        self.fills: Dict[str, CodeFillT] = {}

    def get_fill(
            self,
            key: 'PlaceholderAccessor',
            frame_vars: FrameVarsT,
    ) -> CodeFillT:
        if key.via == 'anonymous':
            return self.interact('<anonymous>', frame_vars)
        if key.name not in self.fills:
            self.fills[key.name] = self.interact(key.name, frame_vars)
        return self.fills[key.name]

    def interact(self, key: Optional[str], frame_vars: FrameVarsT) -> CodeFillT:
        lines = self.run_interpreter(
            banner=self._placeholder_msg.format(key=key),
            local=frame_vars
        )
        return self.parse_session(lines)

    @classmethod
    def run_interpreter(cls, banner: str, local: FrameVarsT) -> List[str]:
        read_fn, read_lines = cls.mkread()
        code.interact(
            banner=banner,
            readfunc=read_fn,
            local=local,
        )
        return read_lines

    @staticmethod
    def mkread() -> Tuple[Callable[[str], str], List[str]]:
        raise NotImplementedError('stub!')

    @staticmethod
    def evaluate_fill(
        expression: CodeFillT,
        frame_vars: FrameVarsT
    ) -> Tuple[ValueT, FrameVarsT]:
        raise NotImplementedError('stub!')

    def parse_session(self, lines: List[str]) -> CodeFillT:
        raise NotImplementedError('stub!')


class SinglePlaceholderSession(PlaceholderSession):
    @staticmethod
    def mkread() -> Tuple[Callable[[str], str], List[str]]:
        lines = []
        def readfunc(prompt: str) -> str:
            line = input(prompt)
            lines.append(line)
            return line
        return readfunc, lines

    @staticmethod
    def evaluate_fill(
        expression: CodeFillSingleT,
        frame_vars: FrameVarsT
    ) -> Tuple[ValueT, FrameVarsT]:
        raise NotImplementedError('stub!')

    def parse_session(self, lines: List[str]) -> CodeFillSingleT:
        raise NotImplementedError('stub!')


class ExpressionPlaceholderSession(SinglePlaceholderSession):
    _placeholder_msg = textwrap.dedent('''
        Entering ExpressionPlaceholder session.
        When you have an expression that works, press ctrl+D to end the session 
        and replace the placeholder with the last line you typed.
        Alternatively, call exit() to abort.
        
        # TODO: fill variable "{key}"
    ''')

    @staticmethod
    def evaluate_fill(
        expression: CodeFillSingleT,
        frame_vars: FrameVarsT
    ) -> Tuple[ValueT, FrameVarsT]:
        value = eval(expression, frame_vars)
        return value, frame_vars

    def parse_session(self, lines):
        if not lines:
            raise ValueError('No lines entered; placeholder fill aborted')
        expr = lines[-1]
        if ast.parse(expr).body[0].__class__.__name__ != 'Expr':
            raise ValueError(
                'Your statement was not an expression, it won\'t work for '
                'PlaceholderExpression. Try PlaceholderStatement.'
            )
        return expr


class StatementPlaceholderSession(SinglePlaceholderSession):
    _placeholder_msg = textwrap.dedent('''
        Entering StatementPlaceholder session.
        When you have an expression that works, press ctrl+D to end the session 
        and replace the placeholder with the last line you typed.
        Alternatively, call exit() to abort.
        
        # TODO: fill statement "{key}"
    ''')

    @staticmethod
    def evaluate_fill(
        expression: CodeFillSingleT,
        frame_vars: FrameVarsT
    ) -> Tuple[ValueT, FrameVarsT]:
        exec(expression, frame_vars)
        try:
            value = _  # holy shit
        except NameError:
            value = None
        return value, frame_vars

    def parse_session(self, lines: List[str]) -> CodeFillSingleT:
        if not lines:
            raise ValueError('No lines entered; placeholder fill aborted')
        return lines[-1]


class MultilinePlaceholderSession(PlaceholderSession):
    _placeholder_msg = textwrap.dedent('''
        Entering MultilinePlaceholder session.
        Play around in your session.
        When you want to add a statement to the placeholder, prefix it with "!"
        e.g.
        >>> !x = x + 10

        When your placeholder is complete, press ctrl+D to exit the session and 
        overwrite the placeholder in source code.
        Alternatively, call exit() to abort.
        
        # TODO: fill statements at "{key}"
    ''')

    @staticmethod
    def evaluate_fill(fill: StatementsFill, frame_vars: FrameVarsT):
        # could probably be replaced by exec()
        interpreter = ValidInterpreter(locals=frame_vars)
        for line in fill:
            interpreter.runsource(line)
        updates = {}
        for k, v in interpreter.locals.items():
            updates[k] = v
        return None, frame_vars

    @staticmethod
    def mkread():
        lines = []
        def readfunc(prompt):
            line = input(prompt)
            if line.startswith('!'):
                line = line[1:]
                lines.append(line)
            return line
        return readfunc, lines

    def parse_session(self, lines: List[str]) -> StatementsFill:
        return lines


class PlaceholderAccessor:
    def __init__(self, name: Optional[str], via: str, parent: Any):
        self.name = name
        self.via = via
        self.parent = parent


class RewriteContext:
    def __init__(self, filename: str):
        self.filename = filename
        self.offset = 0

    def rewrite_allowed(
        self,
        base_filename: str,
        rewrite_source: bool = True,
        allow_propagation: bool = False,
    ) -> bool:
        if not rewrite_source:
            return False
        if (not allow_propagation) and base_filename != self.filename:
            raise ValueError((
                'Tried to edit file {}, but the placeholder was initialized in ' 
                'file {}. This is a safeguard to prevent you from editing ' 
                'files you did not intend to edit, pass `allow_propagation` to ' 
                'enable this behavior. '
            ).format(self.filename, base_filename))
        return True

    @staticmethod
    def _find_attr_access(
        caller_line: str,
        key: PlaceholderAccessor,
        frame_vars: FrameVarsT
    ) -> str:
        my_names = [k for k, v in frame_vars.items() if v is key.parent]
        if not my_names:
            raise ValueError(
                'Could not find a reference to placeholder accessor in your '
                'source. This indicates that you\'re calling it in a strange '
                'way, and it\'s unclear exactly what should be rewritten.'
            )
        my_name = my_names[0]
        accessor = '{}.{}'.format(my_name, key.name)

        if accessor not in caller_line:
            raise ValueError(
                'Could not find placeholder accessor in your source. It\'s '
                'likely that you\'re using Placeholder in an unusual way (e.g. '
                '__getattribute__) which will cause it to break.'
            )

        return accessor

    @staticmethod
    def _test_call(key: PlaceholderAccessor, call: str) -> bool:
        try:
            expr = ast.parse(call, mode='eval')
        except SyntaxError:
            return False
        if expr.body.__class__.__name__ != 'Call':
            return False
        args = expr.body.args
        if not args:
            return key.via == 'anonymous'

        if args[0].__class__.__name__ != 'Constant':
            raise ValueError(
                'Placeholder is unable to deeply inspect expressions to '
                'discriminate between accessors. Please call `set_placeholder` '
                'only with a constant expression for the first argument'
            )

        if args[0].value is None:
            return key.via == 'anonymous'
        elif args[0].value == key.name:
            return True

        return False

    @classmethod
    def _find_call_access(
        cls,
        caller_line: str,
        key: PlaceholderAccessor,
        frame_vars: FrameVarsT
    ) -> str:
        module = sys.modules[__package__]
        refs = [k for k, v in frame_vars.items() if v is key.parent]
        module_refs = [k for k, v in frame_vars.items() if v is module]
        for module_ref in module_refs:
            for k, v in frame_vars[module_ref].__dict__.items():
                if v is key.parent:
                    refs.append('{}.{}'.format(module_ref, k))
        for ref in refs:
            for start_pos in _find_all(caller_line, ref):
                for end_pos in _find_all(caller_line, ')', start_pos):
                    candidate = caller_line[start_pos:end_pos + 1]
                    if cls._test_call(key, candidate):
                        return candidate
        raise ValueError(
            'Could not find placeholder accessor in your source. It\'s '
            'likely that you\'re using Placeholder in an unusual way (e.g. '
            '__getattribute__) which will cause it to break.'
        )

    @classmethod
    def _find_accesspoint(
            cls,
            caller_line: str,
            key: PlaceholderAccessor,
            frame_vars: FrameVarsT,
    ) -> str:
        if key.via == 'attr':
            return cls._find_attr_access(caller_line, key, frame_vars)
        elif key.via == 'anonymous' or key.via == 'call':
            return cls._find_call_access(caller_line, key, frame_vars)
        else:
            raise NotImplementedError('Unsupported key via {}'.format(key.via))

    def rewrite_single(
            self,
            key: PlaceholderAccessor,
            fill: CodeFillSingleT,
            frame: FrameT,
            frame_vars: FrameVarsT,
    ) -> None:
        fname = frame.f_globals['__file__']
        with open(fname, 'r') as in_f:
            caller_source = in_f.readlines()
        caller_lineno = frame.f_lineno - 1 + self.offset
        caller_line = caller_source[caller_lineno]

        accessor = self._find_accesspoint(caller_line, key, frame_vars)

        caller_source[caller_lineno] = caller_line.replace(accessor, fill)
        with open(fname, 'w') as out_f:
            out_f.writelines(caller_source)

    def rewrite_multi(
            self,
            key: PlaceholderAccessor,
            fill: StatementsFill,
            frame: FrameT,
            frame_vars: FrameVarsT,
    ) -> None:
        fname = frame.f_globals['__file__']
        with open(fname, 'r') as in_f:
            caller_source = in_f.readlines()
        caller_lineno = frame.f_lineno - 1 + self.offset
        caller_line = caller_source[caller_lineno]

        accessor = self._find_accesspoint(caller_line, key, frame_vars)
        if set(caller_line.replace(accessor, '')) > {'', '\t', '\n'}:
            print(set(caller_line.replace(accessor, '')))
            raise ValueError(
                'A multi-line placeholder must be the only statement on the '
                'line it is called from. '
            )

        indent = caller_line[:caller_line.find(accessor)]

        caller_source.pop(caller_lineno)
        lineno = caller_lineno
        for line in fill:
            caller_source.insert(lineno, indent + line + '\n')
            lineno += 1

        with open(fname, 'w') as out_f:
            out_f.writelines(caller_source)

        self.offset += -1 + len(fill)


def set_placeholder(
    key: Union[str, PlaceholderAccessor] = None,
    replace_mode: str = None,
    rewrite_source: bool = True,
    allow_propagation: bool = False,
    _session: PlaceholderSession = None,
    _base_filename: str = None,
    _frame: FrameT = None,
):
    """
    Set up and enter a Placeholder session.

    This will open an interactive terminal in the context of the calling
    function, bound to the key passed as an argument.
    The terminal session can be used to control the return value of the function
    call.
    When the session is complete, the call to this method will be rewritten in
    the source code to match the terminal session.

    The source code rewriting mechanics for this method are a bit delicate, and
    will likely fail if you do something much more complicated than simply
    calling this function (e.g. trying to run in an executor, calling indirectly
    with `map`, assigning to an object within a dictionary then calling that,
    etc).

    :param key:
        Should be passed as a string constant ONLY, if you're using the rewrite
        functionality.
        Controls the "key" to which this terminal session is assigned.
        If a later placeholder call in a different context tries to access the
        same key, it will be filled with the value of the original expression
        evaluated in the new context (!).
        If not provided, you will be given an "anonymous" key, which isn't
        shared with any other calls to `set_placeholder`.
    :param replace_mode:
        You need to decide beforehand if you're writing a placeholder for a
        python `expression`, a single line `statement`, or multiple statements.
        Valid values for this argument are:
            - "expression"
            - "statement"
            - "multiline"
        If none is provided, it will default to "expression"
    :param rewrite_source:
        Boolean flag to enable the source code editing functionality of
        placeholder.
        If you disable this, placeholder expressions will still be filled with
        the expression you enter in your terminal session, but the originating
        calls will not be rewritten with this expression.
    :param allow_propagation:
        If used through a Placeholder object, this allows modifying the source
        code of a different file than the one where the placeholder object was
        first created.
        When calling `set_placeholder` directly, this flag will do nothing under
        normal circumstances, and is safe to ignore.
    :param _session:
        Used internally by placeholder objects. Safe to ignore.
    :param _base_filename:
        Used internally by placeholder objects. Safe to ignore.
    :param _frame:
        Used internally by placeholder objects. Safe to ignore.
    """
    frame = _frame
    if frame is None:
        frame = inspect.currentframe().f_back
    filename = frame.f_globals['__file__']

    session = _session
    if session is None:
        if replace_mode is None:
            replace_mode = 'expression'
        if (filename, replace_mode) not in default_session:
            session_t = {
                'expression': ExpressionPlaceholderSession,
                'statement': StatementPlaceholderSession,
                'multiline': MultilinePlaceholderSession,
            }.get(replace_mode)
            if session_t is None:
                raise ValueError('Invalid replace mode {}'.format(replace_mode))
            default_session[(filename, replace_mode)] = session_t()
        session = default_session[(filename, replace_mode)]
    elif replace_mode is not None:
        raise ValueError('Cannot provide both `replace_mode` and Session')

    base_filename = _base_filename
    if rewrite_source:
        if any([
                base_filename is None,
                (base_filename == filename),
                allow_propagation,
        ]):
            if filename not in default_rewrite_ctx:
                default_rewrite_ctx[filename] = RewriteContext(filename)
            rewrite_ctx = default_rewrite_ctx[filename]
        else:
            raise ValueError((
                'Tried to edit file {}, but the placeholder was initialized in '
                'file {}. This is a safeguard to prevent you from editing '
                'files you did not intend to edit, pass `allow_propagation` to '
                'enable this behavior. '
            ).format(filename, base_filename))
    else:
        rewrite_ctx = None

    if key is None:
        key = PlaceholderAccessor(None, 'anonymous', set_placeholder)
    elif isinstance(key, str):
        key = PlaceholderAccessor(key, 'call', set_placeholder)
    elif not isinstance(key, PlaceholderAccessor):
        raise ValueError('Invalid key {} of type {}'.format(key, type(key)))

    frame_vars = get_frame_vars(frame)
    fill = session.get_fill(key, frame_vars)
    frame_vars = get_frame_vars(frame)
    value, updates = session.evaluate_fill(fill, frame_vars)

    if rewrite_ctx is not None:
        if isinstance(session, MultilinePlaceholderSession):
            rewrite_ctx.rewrite_multi(key, fill, frame, frame_vars)
        else:
            rewrite_ctx.rewrite_single(key, fill, frame, frame_vars)

    inject_vars(frame, updates)

    return value


class PlaceholderBase(object):
    """
    This is a placeholder context.

    When you access an object of the context, an interpreter session will be
    fired up with access to the local environment where the variable was
    accessed.

    You should use that environment to figure out what needs to replace the
    placeholder.

    When the session completes, the value of the accessed object will become
    the value of the last valid expression from the interpreter session, and
    (optionally, default True) the placeholder in source code will be replaced
    by the last line of input.

    E.g.

    placeholder = Placeholder()
    ...
    # Running this will open a terminal session to find the value of "filename"
    print('My file is', placeholder.filename)
    ...
    # The value of "filename" from the previous session will be re-used, but
    # it will be rewritten with the same expression
    file = open(placeholder.filename, 'r')
    """

    session_t: Type[PlaceholderSession]

    def __init__(
        self,
        rewrite_source=True,
        allow_propagation=False,
        _frame=None,
    ):
        """
        Create a placeholder context.
        You probably only need one of these.

        :param rewrite_source:
            When the placeholder completes, edits the source code of the place
            where the placeholder was called from to replace the placeholder
            with the given expression.

        :param allow_propagation:
            If you pass the placeholder context to some function, it will still
            be able to rewrite source code in places where it is used. Probably
            you do not want this, to avoid rewriting code in strange places or
            even system libraries.
            By default, placeholder will restrict editing to only the file
            where the placeholder context was initialized. `allow_propagation`
            will disable this safeguard.

        :param _frame:
            If this init function is called via 'super', _frame should be set
            by the calling class.
        """
        self._rewrite_source = rewrite_source
        self._allow_propagation = allow_propagation
        self._expressions = {}
        self._session = self._session_t()

        if _frame is None:
            _frame = inspect.currentframe().f_back
        self._filename = _frame.f_locals['__file__']

    def __getattribute__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        caller_frame = inspect.currentframe().f_back

        return set_placeholder(
            PlaceholderAccessor(key, 'attr', self),
            rewrite_source=self._rewrite_source,
            allow_propagation=self._allow_propagation,
            _session=self._session,
            _base_filename=self._filename,
            _frame=caller_frame,
        )


class ExpressionPlaceholder(PlaceholderBase):
    _session_t = ExpressionPlaceholderSession


class StatementPlaceholder(PlaceholderBase):
    _session_t = StatementPlaceholderSession


class MultilinePlaceholder(PlaceholderBase):
    _session_t = MultilinePlaceholderSession


Placeholder = ExpressionPlaceholder
