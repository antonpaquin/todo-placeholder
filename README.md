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

THIS TOOL CAN EDIT YOUR SOURCE CODE. KEEP BACKUPS.

### wtf

yeah

### Simple Example

Say we have `my_program.py`:

```
from todo import Placeholder
placeholder = Placeholder()

print(placeholder.some_string)
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

`my_program.py` will continue execution, except `some_string` is replaced with
the expression 'hello world!'.

Note: the *expression*, not the *value* of the expression. You can use 
`placeholder.some_string` later and the same expression will be re-evaluated in 
whatever context it was accessed from.

When the program completes, you can check `my_program.py` again:

```
from todo import Placeholder
placeholder = Placeholder()

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
from todo import Placeholder
import requests

placeholder = Placeholder()

def get_data(url):
    r = requests.get(url)
    # How do I get the response code here? TODO via placeholder
    if placeholder.http_code != 200:
        raise RuntimeError(f'Error: server responded with error code {placeholder.http_code}')
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
from todo import Placeholder
import requests

placeholder = Placeholder()

def get_data(url):
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f'Error: server responded with error code {r.status_code}')
    return r.text

get_data('http://www.example.com/probably_404')
```

### Other Placeholders

#### PlaceholderExpression

`todo.Placeholder` is an alias for `todo.PlaceholderExpression`. This is the
simplest placeholder: it evaluates a single expression and does not modify the
local environment beyond the value of that expression.

#### PlaceholderStatement

`todo.PlaceholderStatement` allows for a single python statement, which can
be used to do things like assign to a variable.

Example:

```
import todo

placeholder = todo.PlaceholderStatement()

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

placeholder = todo.PlaceholderStatement()

x = 1
print(x)
x += 1
print(x)
x += 1
print(x)
```

#### PlaceholderMultiline

`todo.PlaceholderMultiline` allows for replacing a placeholder with many lines
of input.

To use this, the placeholder should be the only expression on the line where it
is accessed, and you should prefix any lines you want to add to the replacement 
with '!'

Example:

```
import todo

placeholder = todo.PlaceholderMultiline()

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

placeholder = todo.PlaceholderMultiline()

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

`Placeholder` works by scanning your code for an accessor of the form 
`placeholder_var.some_key`. If you access it in an unusual way -- say, 
`__getattribute__`, it won't be able to find the item it should replace.

Furthermore, it can't tell the difference between a "code" accessor and a 
"non-code" accessor. So if you have something like 

```
print('placeholder.key = {}'.format(placeholder.key))
```

Both instances of "placeholder.key" will be replaced in that line, even though
only one of them is the actual access point.

Because of how placeholder internals work, your keys cannot start with an
underscore '_'.
