import importlib
import lldb
import re
import sys

def crochet(regex=None, maxdepth=1, file=None, depth=0, visited=set(), p=None):

    if depth == 0:
        class GeneralizedPrinter:
            def __init__(self, file):
                self.file = open(file, 'w') if file is not None else None
                self.last_str = None
            def __call__(self, s):
                if self.last_str == s:
                    return
                self.last_str = s
                print(s)
                if self.file is not None:
                    self.file.write(s+'\n')
        
        p = GeneralizedPrinter(file)

    indent = "  "*depth

    if depth > maxdepth:
        p(f"{indent}<...> (too deep)")
        return

    for var in lldb.frame.variables:
        s = repr(var)
        indent = "  "*depth
        
        #if var.addr.offset in visited:
        if s in visited:
            #p(f'{indent}<...> (see above)')
            continue

        if regex is None or re.search(regex, s, re.I | re.UNICODE | re.MULTILINE):
            p(f'{indent}{var}')

        #visited.add(var.addr.offset)
        visited.add(s)

        if var.num_children > 0:
            #p(f'{indent}woop {depth}')
            crochet(regex, maxdepth, file, depth+1, visited, p)
