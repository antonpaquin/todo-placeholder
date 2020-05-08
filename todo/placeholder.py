#! /usr/bin/env python

# This is how you know it's gonna be good
import ast
import code
import inspect


__all__ = [
    'Placeholder',
    'PlaceholderExpression',
    'PlaceholderMultiline',
    'PlaceholderStatement',
]


def _get_frame_vars(frame):
    return {**frame.f_globals, **frame.f_locals}


class ValidInterpreter(code.InteractiveConsole):
    def showtraceback(self):
        raise


class PlaceholderBase(object):

    def __init__(self, rewrite_source=True, allow_propagation=False, _frame=None):
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
        
        if _frame is None:
            _frame = inspect.currentframe().f_back
        self._filename = _frame.f_locals['__file__']

    def _get_expression(self, key, frame_vars):
        if key not in self._expressions:
            self._expressions[key] = self._interact(key, frame_vars)
        return self._expressions[key]

    def _interact(self, key, frame_vars):
        lines = self._run_interpreter(
            banner=self._placeholder_msg.format(key=key), 
            local=frame_vars
        )
        return self._parse_session(lines)

    def _parse_session(self, lines):
        return NotImplementedError('stub!')

    def _evaluate_expression(self, expression, frame_vars):
        exec(expression, frame_vars)
        try:
            # holy shit
            value = _
        except NameError:
            value = None
        return value, frame_vars

    def _rewrite_allowed(self, frame_vars):
        if not self._rewrite_source:
            return False
        if (not self._allow_propagation) and frame_vars['__file__'] != self._filename:
            raise ValueError((
                "Tried to edit file {}, but the placeholder was initialized in "
                "file {}. This is a safeguard to prevent you from editing "
                "files you did not intend to edit, pass `allow_propagation` to "
                "enable this behavior. "
            ).format(frame_vars['__file__'], self._filename))
        return True

    def _apply_rewrite(self, key, expression, frame):
        return NotImplementedError('stub!')

    def _inject_results(self, frame, updates):
        for k, v in updates.items():
            frame.f_locals[k] = v

    def _fill_placeholder(self, key, frame):
        frame_vars = _get_frame_vars(frame)
        expression = self._get_expression(key, frame_vars)
        frame_vars = _get_frame_vars(frame)
        value, updates = self._evaluate_expression(expression, frame_vars)
        if self._rewrite_allowed(frame_vars):
            self._apply_rewrite(key, expression, frame, frame_vars)
        self._inject_results(frame, updates)
        return value

    @staticmethod
    def _mkread():
        lines = []
        def readfunc(prompt):
            line = input(prompt)
            lines.append(line)
            return line
        return readfunc, lines

    @classmethod
    def _run_interpreter(cls, banner, local):
        read_fn, read_lines = cls._mkread()
        code.interact(
            banner=banner,
            readfunc=read_fn,
            local=local,
        )
        return read_lines


class PlaceholderStatement(PlaceholderBase):
    _placeholder_msg = '''
TODO: fill statement "{key}"
When you have an expression that works, press ctrl+D to end the session and 
replace the placeholder with the last line you typed.
Alternatively, call exit() to abort.
'''

    def _parse_session(self, lines):
        return lines[-1]

    def _apply_rewrite(self, key, expression, frame, frame_vars):
        fname = frame.f_globals['__file__']
        with open(fname, 'r') as in_f:
            caller_source = in_f.readlines()
        caller_lineno = frame.f_lineno - 1
        caller_line = caller_source[caller_lineno]

        my_name = [k for k, v in frame_vars.items() if v is self][0]
        accessor = '{}.{}'.format(my_name, key)
        if accessor not in caller_line:
            raise ValueError(
                "Could not find placeholder accessor in your source. It's "
                "likely that you're using Placeholder in an unusual way (e.g. "
                "__getattribute__) which will cause it to break."
            )

        caller_source[caller_lineno] = caller_line.replace(accessor, expression)
        with open(fname, 'w') as out_f:
            out_f.writelines(caller_source)

    def __getattribute__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        caller_frame = inspect.currentframe().f_back
        return self._fill_placeholder(key, caller_frame)


class PlaceholderExpression(PlaceholderStatement):
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

    _placeholder_msg = '''
TODO: fill variable "{key}"
When you have an expression that works, press ctrl+D to end the session and 
replace the placeholder with the last line you typed.
Alternatively, call exit() to abort.
'''
    def _parse_session(self, lines):
        expr = lines[-1]
        if (ast.parse(expr).body[0].__class__.__name__ != 'Expr'):
            raise ValueError(
                "Your statement was not an expression, it won't work for "
                "PlaceholderExpression. Try PlaceholderStatement."
            )
        return expr


    def _inject_results(self, frame, updates):
        pass


Placeholder = PlaceholderExpression


class PlaceholderMultiline(PlaceholderBase):
    _placeholder_msg = '''
TODO: fill statements at "{key}"
Play around in your session.
When you want to add a statement to the placeholder, prefix it with "!"
e.g.
>>> !x = x + 10

When your placeholder is complete, press ctrl+D to exit the session and 
overwrite the placeholder in source code.
Alternatively, call exit() to abort.
'''
    def __init__(self, rewrite_source=True, allow_propagation=False):
        super(PlaceholderMultiline, self).__init__(
            rewrite_source=rewrite_source,
            allow_propagation=allow_propagation,
            _frame=inspect.currentframe().f_back
        )
        self._offset = 0

    @staticmethod
    def _mkread():
        lines = []
        def readfunc(prompt):
            line = input(prompt)
            if line.startswith('!'):
                line = line[1:]
                lines.append(line)
            return line
        return readfunc, lines

    def _parse_session(self, lines):
        return lines

    def _evaluate_expression(self, expression, frame_vars):
        # could probably be replaced by exec()
        interpreter = ValidInterpreter(locals=frame_vars)
        for line in expression:
            interpreter.runsource(line)
        updates = {}
        for k, v in interpreter.locals.items():
            updates[k] = v
        return None, frame_vars

    def _apply_rewrite(self, key, expression, frame, frame_vars):
        fname = frame.f_globals['__file__']
        with open(fname, 'r') as in_f:
            caller_source = in_f.readlines()
        caller_lineno = frame.f_lineno - 1 + self._offset
        caller_line = caller_source[caller_lineno]

        my_name = [k for k, v in frame_vars.items() if v is self][0]
        accessor = '{}.{}'.format(my_name, key)
        if accessor not in caller_line:
            print(accessor)
            raise ValueError(
                "Could not find placeholder accessor in your source. It's "
                "likely that you're using Placeholder in an unusual way (e.g. "
                "__getattribute__) which will cause it to break."
            )
        if set(caller_line.replace(accessor, '')) > {'', '\t', '\n'}:
            print(set(caller_line.replace(accessor, '')))
            raise ValueError(
                "A multi-line placeholder must be the only statement on the "
                "line it is called from. "
            )

        indent = caller_line[:caller_line.find(accessor)]

        caller_source.pop(caller_lineno)
        lineno = caller_lineno
        for line in expression:
            caller_source.insert(lineno, indent + line + '\n')
            lineno += 1

        with open(fname, 'w') as out_f:
            out_f.writelines(caller_source)

        self._offset += -1 + len(expression)

    def __getattribute__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        caller_frame = inspect.currentframe().f_back
        return self._fill_placeholder(key, caller_frame)
