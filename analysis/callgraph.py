#!/usr/bin/env python3
# quickly generate a call graph of backupy.py
# depends on pyan3 and graphviz
# tested with pyan3==1.0.4 (note this version has issues if running from a venv)
import os
import re

# don't need to cd into analysis
os.chdir(os.path.dirname(__file__))

# ignore nodes or edges on lines containing these strings
ignored_node_strings = [
    "abortRun",
    "internalTests",
    "rsync_proc",
    " -> backupy__fileman__FileManager [",
    " -> backupy__filescanner__FileScanner [",
    " -> backupy__transferlists__TransferLists ["
]

# modules to scan
modules = [
    "../backupy/backupman.py",
    "../backupy/fileman.py",
    "../backupy/filescanner.py",
    "../backupy/transferlists.py"
]

# quick workaround for pyan3 not supporting type hints or type inference
# WARNING, THIS WILL EDIT THESE MODULES, MAKE SURE ANY CHANGES ARE COMMITTED SO THEY CAN EASILY BE RESTORED
# depends on my coding style (linting with flake8), function defs containing objects of interest being 1 line, and indenting with 4 spaces
# probably better to use ast or tokenize, but can't generate code back easily from those (at that point might as well figure out how to add this to pyan)
print("Applying workarounds to modules to generate callgraph with pyan3")
class_names = []
for module in modules:
    with open(module, "r") as m:
        m = m.readlines()
        for line in m:
            class_name = re.match(r'class ([A-Za-z]+?)[\(: ]', line)
            if class_name:
                class_names.append(class_name.groups()[0])
for module in modules:
    with open(module, "r") as m:
        m = m.readlines()
        updated_module = []
        for line in m:
            updated_module.append(line)
            if line.strip().startswith("def "):
                spaces = line.index("def") + 4
                line = line[line.index("(")+1:line.index(")")].split(", ")
                for arg in line:
                    for class_name in class_names:
                        if class_name in arg:
                            arg_name = arg.split(":")[0]
                            new_line = " "*spaces + arg_name + " = " + class_name + "\n"
                            updated_module.append(new_line)
                            new_line = " "*spaces + "self." + arg_name + " = " + class_name + "\n"
                            updated_module.append(new_line)
    with open(module, "w") as m:
        m.writelines(updated_module)

# generate callgraph using pyan3
print("Generating callgraph")
os.system("pyan3 " + " ".join(modules) + " --no-defines --uses --colored --nested-groups --dot > callgraph.dot")

# clean up callgraph
with open("callgraph.dot", "r") as f:
    dot = f.readlines()
new_dot = [
    'digraph G {\n',
    '    graph [rankdir=TB, clusterrank="global", concentrate=false, ranksep="2", nodesep="0.2"];\n',
    '    overlap=false;\n'
    '    splines=true;\n',
    '    subgraph cluster_G {\n',
    '\n',
    '        graph [style="filled,rounded",fillcolor="#80808018", label=""];\n',
    '        backupy [label="backupy", style="filled", fillcolor="#ffffffb2", fontcolor="#000000", group="0"];\n'
]
i = 6
while i < len(dot):
    if "subgraph" in dot[i]:
        # node
        if not any([n in dot[i+3] for n in ignored_node_strings]):
            # keep
            if "}" in dot[i+4]:
                new_dot += dot[i:i+5]
                i += 5
            else:
                new_dot += dot[i:i+4]
                i += 4
        else:
            # shift brace if necessary (node discarded)
            if "}" in dot[i+4]:
                i += 5
            elif "}" not in dot[i+4] and "}" in new_dot[-1]:
                _ = new_dot.pop(-1)
                i += 4
            else:
                raise Exception("Error, unexpected node/subgraph nesting")
    else:
        # edge
        if not any([n in dot[i] for n in ignored_node_strings]):
            # keep
            new_dot.append(dot[i])
        i += 1
# sort edges so output is deterministic
newer_dot = []
newer_edges = []
edge_start = False
edge_end = False
for line in new_dot:
    if "->" in line and not edge_end:
        edge_start = True
        newer_edges.append(line)
    elif edge_start and not edge_end:
        edge_end = True
        newer_dot += sorted(newer_edges)
        newer_dot.append(line)
    else:
        newer_dot.append(line)   
with open("callgraph.dot", "w") as f:
    f.writelines(newer_dot)

# create svg with graphviz
os.system("dot -Tsvg callgraph.dot > callgraph.svg")

# cleanup
print("Cleaning up (restoring modules)")
for module in modules:
    os.system("git restore " + module)

print("Done")
