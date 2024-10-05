import importlib
import lldb
import re
import sys
import inspect

MAXVAL = 80

# Btw... the built-in function has it all.
# Example: dwim-print -A -P 3 this
# Children limit can be increased with "settings show target.max-children-count 1024"
# Too bad it keeps crashing

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

def crochet_rec (var, regex, maxdepth, depth , visited, p, stacc, strm):
    try:
        indent = "" if depth == 0 else "  "*depth
        indent_p1 = "  "*(depth+1)

        t = var.GetType()

        is_array = t.IsArrayType()
        is_aggregate = t.IsAggregateType()
        is_null = var.GetType().IsPointerType() and var.GetValueAsUnsigned() == 0

        inheritance = var.path == 'this' and var.name != 'this'
        num_children = var.GetNumChildren()

        if regex is None or re.search(regex, var.GetName(), re.I | re.UNICODE | re.MULTILINE):
            if is_aggregate:
                type_str = ''
            else:
                type_str = f'({t.GetDisplayTypeName()})'

            if is_array:
                var.GetDescription(strm)
                val = " # " + strm.GetData().replace('\n', ' ').strip()
                strm.Clear()
            else:
                val = var.GetValue()
            if val and len(val) > MAXVAL:
                val = val[:MAXVAL-4] + ' ...'

            p(f'{indent}{": " if inheritance else ""}{".".join(stacc)} {"= " if val is not None else ""}{"{" if num_children > 1 and not inheritance and not is_null else ""}{val}')

        if is_null:
            return

        MAX_CHILDREN = 100
        for baby_id in range(min(num_children, MAX_CHILDREN)):
            baby = var.GetChildAtIndex(baby_id)
            if depth == maxdepth:
                p(f"{indent_p1}<...> (too deep)")
                break

            baby_name = baby.GetName()
            if baby_name is None:
                baby_name = '()'
            stacc.append(baby_name)

            # Not 100% sure but I think this is the criterion for base classes. We want base class members to be on the same level.
            is_base = baby.path == 'this'

            if baby.GetID() in visited:
                # Actually, this condition is error-prone. Babies don't typically carry IDs around.
                p(f'{indent_p1}{".".join(stacc)}')
                stacc.pop()
                continue

            visited.add(baby.GetID())

            # Not 100% sure but I think this is the criterion for base classes. We want base class members to be on the same level.
            # if is_base:
            #     new_depth = depth
            # else:
            #     new_depth = depth + 1
            new_depth = depth + 1

            crochet_rec(baby, regex, maxdepth, new_depth, visited, p, stacc, strm)

            stacc.pop()

        if num_children > 1 and not inheritance:
            p(f'{indent_p1}}}')

        if num_children > MAX_CHILDREN:
            p(f'{indent_p1}[...] (...) # Too many kids. I give up.')

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
            s += b'\n'
            sys.stdout.buffer.write(s)
            if self.file is not None:
                self.file.write(s)

    p = GeneralizedPrinter(file)

    for var in lldb.frame.variables:
        crochet_rec(var, regex, maxdepth, 0, visited, p, [var.GetName()], lldb.SBStream())
    
    p('bye')