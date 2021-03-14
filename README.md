# todo-placeholder

## Installation

```
pip install todo-placeholder
```

## Placeholder

This is a tool intended to speed the process of development in python.

You're writing your code, and you run into a spot where you don't know exactly 
what needs to go there.

Placeholder lets you fill that spot with a "placeholder" variable. 

At runtime, when it comes time that you actually need to compute the value, 
"placeholder" will open an interactive session that you can play around in to
get the value.

(Optional) When you're done with your session, the placeholder in your code is
replaced with expression from your terminal session.

THIS TOOL CAN EDIT YOUR SOURCE CODE. KEEP BACKUPS. I hear `git` is pretty nice.

### wtf

yeah

### Simple Example

Say we have `my_program.py`:

```
import todo

print(todo.set_placeholder('some_string'))
```

Run it with `python my_program.py` and you'll enter an interactive session.

```
TODO: fill variable "some_string"
When you have an expression that works, press ctrl+D to end the session and
replace the placeholder with the last line you typed.
Alternatively, call exit() to abort.

>>>
```

This is a `code.interact` session, which means you have all of python available
to you. I recommend learning to use `help()` and `dir()` to inspect your 
environment and see what's available to you.

From here, you should fill in the value of `some_string`

```
>>> 'hello world!'
'hello world!'
>>> <ctrl+D>
now exiting InteractiveConsole...
```

`my_program.py` will continue execution, except the placeholder call to 
`some_string` is replaced with the expression 'hello world!'.

Note: the *expression*, not the *value* of the expression. You can use 
`set_placeholder('some_string')` later and the same expression will be 
re-evaluated in whatever context it was accessed from.

It's as if you ran a find+replace job with the last expression you wrote in
your terminal session.

When the program completes, you can check `my_program.py` again:

```
import todo

print('hello world!')
```

The placeholder has been replaced by the expression you used in your terminal
session.

### More realistic example

Say I'm writing a larger program that involves downloading something from the
web. Naturally, I'll use requests. But personally, I can never remember exactly
what variable in the response holds the HTTP response status.

This `my_program.py` is a toy example, but it would work the same in a larger
program:

```
import todo
import requests

def get_data(url):
    r = requests.get(url)
    # How do I get the response code here? TODO via placeholder
    if todo.set_placeholder('http_code') != 200:
        raise RuntimeError(f'Error: server responded with error code {todo.set_placeholder("http_code")}')
    return r.text

get_data('http://www.example.com/probably_404')
```

Running the program will drop me into an interactive session, where the local
context of `get_data` is all available.

```
TODO: fill variable "http_code"
When you have an expression that works, press ctrl+D to end the session and
replace the placeholder with the last line you typed.
Alternatively, call exit() to abort.

>>> r
<Response [404]>
>>> url
'http://www.example.com/probably_404'
>>> # Now I can use help() to figure out how to get the error code out of r
>>> help(r)

>>> # aha, it's r.status_code
>>> r.status_code
404
>>> <ctrl+D>
now exiting InteractiveConsole...
Traceback (most recent call last):
  File "my_program.py", line 12, in <module>
    get_data('http://www.example.com/probably_404')
  File "my_program.py", line 9, in get_data
    raise RuntimeError(f'Error: server responded with error code {r.status_code}')
RuntimeError: Error: server responded with error code 404
```

And if I check `my_program.py` again, the expression has been filled in

```
import todo
import requests


def get_data(url):
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f'Error: server responded with error code {r.status_code}')
    return r.text

get_data('http://www.example.com/probably_404')
```

### set_placeholder

`set_placeholder` is the simplest way of entering a placeholder context.

The minimum useful context is just a bare call to the function:

```
import todo
todo.set_placeholder()
```

More interesting is allowing your placeholder-filled expressions to be re-used
with the "key" argument:
```
import todo
x = todo.set_placeholder('foo')
...
print(todo.set_placeholder('foo'))
```

In this case, you'll be prompted to fill the first instance of `foo`, but the
second will re-use the expression you entered for the first.

Note that if you pass a key like this, it should be a constant string in order
for the rewriter to work properly.

Instead of just filling in expressions, you can also use a call to fill in a 
statement or even multiple statements, with the `replace_mode` parameter. 

```
import todo
todo.set_placeholder('foo', replace_mode='expression')  # default
todo.set_placeholder('foo', replace_mode='statement')
todo.set_placeholder('foo', replace_mode='multiline')
```

Filled expressions are scoped to the replace mode, so this example would 
trigger three terminal sessions to fill in three different instances of `foo`.

See the [docs for `set_placeholder`](https://github.com/antonpaquin/todo-placeholder/blob/master/todo/placeholder.py#L404) 
for more advanced usage.

### Placeholder Objects

For more control over the placeholder sessions, you can use a placeholder
object instead of directly calling `set_placeholder`.

These are:
- `todo.Placeholder` (alias for `ExpressionPlaceholder`)
- `todo.ExpressionPlaceholder` 
- `todo.StatementPlaceholder`
- `todo.MultilinePlaceholder`

Example:

```
import todo

print(todo.set_placeholder('some_string'))
```

Is equivalent to 

```
import todo
placeholder = todo.Placeholder()

print(placeholder.some_string)
```

A placeholder object is used through its attributes, and is configured when the
object is created.

All placeholder objects take the options `rewrite_source` and 
`allow_propagation`.
See [parameters](#parameters) for more information.

#### ExpressionPlaceholder

This is the simplest placeholder: it evaluates a single expression and does not
modify the local environment beyond the value of that expression.

#### StatementPlaceholder

`todo.StatementPlaceholder` allows for a single python statement, which can
be used to do things like assign to a variable.

Example:

```
import todo

placeholder = todo.StatementPlaceholder()

x = 1
print(x)
placeholder.incr_x
print(x)
placeholder.incr_x
print(x)
```

```
1

TODO: fill statement "incr_x"
When you have an expression that works, press ctrl+D to end the session and
replace the placeholder with the last line you typed.
Alternatively, call exit() to abort.

>>> x += 1
>>>
now exiting InteractiveConsole...
2
3
```

```
import todo

placeholder = todo.StatementPlaceholder()

x = 1
print(x)
x += 1
print(x)
x += 1
print(x)
```

#### MultilinePlaceholder

`todo.MultilinePlaceholder` allows for replacing a placeholder with many lines
of input.

To use this, the placeholder should be the only expression on the line where it
is accessed, and you should prefix any lines you want to add to the replacement 
with '!'

Example:

```
import todo

placeholder = todo.MultilinePlaceholder()

x = 1
y = -1
print(x, y)
placeholder.incr_xy
print(x, y)
placeholder.incr_xy
print(x, y)
```

```
1 -1

TODO: fill statements at "incr_xy"
Play around in your session.
When you want to add a statement to the placeholder, prefix it with "!"
e.g.
>>> !x = x + 10

When your placeholder is complete, press ctrl+D to exit the session and
overwrite the placeholder in source code.
Alternatively, call exit() to abort.

>>> !x += 1
>>> !y -= 1
>>>
now exiting InteractiveConsole...
2 -2
3 -3
```

```
import todo

placeholder = todo.MultilinePlaceholder()

x = 1
y = -1
print(x, y)
x += 1
y -= 1
print(x, y)
x += 1
y -= 1
print(x, y)
```

### Parameters

To disable rewriting the source code of the original program, you can pass 
`rewrite_source=False`.

By default, Placeholder will refuse to edit the source code of any file except
the one it was initialized. This is to prevent things like

```
placeholder = todo.Placeholder()

some_system_library(placeholder)
```

from editing important system files that it should not be touching.

To enable editing other files, pass `allow_propagation=True`.

### Caveats

`Placeholder` objects work by scanning your code for an accessor of the form 
`placeholder_var.some_key`. If you access it in an unusual way -- say, 
`__getattribute__`, it won't be able to find the item it should replace.

`set_placeholder` scans for a call to that method with some constant key 
argument, or else an "anonymous" call with no key.

The rewriter can't tell the difference between a "code" accessor and a 
"non-code" accessor. So if you have something like 

```
print('placeholder.key = {}'.format(placeholder.key))
```

Both instances of "placeholder.key" will be replaced in that line, even though
only one of them is the actual access point.

Because of how placeholder internals work, keys for Placeholder objects cannot 
start with an underscore '_'.

If your arrow keys aren't working, try `import readline`.
