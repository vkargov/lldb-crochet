import importlib
import lldb
import re
import sys
import inspect

MAXVAL = 200

def explore_methods(o):
    for n in dir(o):
        if n in ('Clear', '__del__'):
            # we're not *that* suicidal
            continue
        m = getattr(o, n)
        print(f'.{n}{"()" if callable(m) else ""} -> ', end='')
        try:
            if callable(m):
                val = m()
            else:
                val = m
            lines = str(val).split('\n')
            print(lines[0] + ('' if len(lines) <= 1 else ' ...'))
        except Exception as e:
            print(f'exception: {e}')

def crochet_rec (var, regex, maxdepth, depth , visited, p):
    try:
        indent = "" if depth == 0 else "  "*depth
        indent_p1 = "  "*(depth+1)

        if depth > maxdepth:
            p(f"{indent}<...> (too deep)")
            return

        t = var.GetType()

        is_array = t.IsArrayType()
        is_aggregate = t.IsAggregateType()

        inheritance = var.path == 'this' and var.name != 'this'

        if regex is None or re.search(regex, var.GetName(), re.I | re.UNICODE | re.MULTILINE):
            if is_aggregate:
                type_str = ''
            else:
                type_str = f'({t.GetDisplayTypeName()}) '
            
            lldb_val = var.GetValue()
            if lldb_val is None:
                val = ""
            else:
                val = " = " + str(var.GetValue()).replace('\n', ' ')
            if len(val) > MAXVAL:
                val = val[:MAXVAL-4] + ' ...'
            p(f'{indent}{": " if inheritance else ""}{type_str}{var.GetName()}{" {" if var.children and not inheritance else ""}{val}')

        if var.GetType().IsPointerType() and var.GetValueAsUnsigned() == 0:
            return

        for baby in var.children:
            # Not 100% sure but I think this is the criterion for base classes. We want base class members to be on the same level.
            is_base = baby.path == 'this'

            if baby.GetID() in visited:
                # Actually, this condition is error-prone. Babies don't typically carry IDs around.
                p(f'{indent_p1}{baby.GetName()}')
                continue

            visited.add(baby.GetID())

            # Not 100% sure but I think this is the criterion for base classes. We want base class members to be on the same level.
            if is_base:
                new_depth = depth
            else:
                new_depth = depth + 1

            crochet_rec(baby, regex, maxdepth, new_depth, visited, p)

            if not is_array and not is_base: # not sure second condition is needed
                p(f'{indent}}}')        

        if is_array:
            p(f'{indent}}}')


    except Exception as e:
        p(f'I am Error: {e}')

def crochet(regex=None, maxdepth=1, file=None, p=None):
    visited=set()
    class GeneralizedPrinter:
        def __init__(self, file):
            self.file = open(file, 'wb') if file is not None else None
            self.last_str = None
        def __call__(self, s):
            if type(s) is not str:
                s = str(s)
            s = s.encode('utf-8', errors='ignore')
            if self.last_str == s:
                return
            sys.stdout.buffer.write(s)
            if self.file is not None:
                self.file.write(s+b'\n')

    p = GeneralizedPrinter(file)

    for var in lldb.frame.variables:
        crochet_rec(var, regex, maxdepth, 0, visited, p)
    
    p('bye')