# quickly generate a call graph of backupy.py
# depends on pyan3 and graphviz

# ignore nodes or edges on lines containing these strings
ignored_node_strings = [
    "File -> backupy__dirinfo__DirInfo [",
    "DiffSummary -> backupy__dirinfo__DirInfo [",
    "performBackup -> backupy__dirinfo__DirInfo [",
    "Consistency -> backupy__transferlists__TransferLists [",
    "DiffSummary -> backupy__transferlists__TransferLists [",
    "performBackup -> backupy__transferlists__TransferLists ["
]

# generate callgraph using pyan3
import os
os.system("pyan3 ../backupy/backupman.py ../backupy/dirinfo.py ../backupy/fileman.py ../backupy/transferlists.py --no-defines --uses --colored --nested-groups --dot > callgraph.dot")

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
with open("callgraph.dot", "w") as f:
    f.writelines(new_dot)

# create svg with graphviz
os.system("dot -Tsvg callgraph.dot > callgraph.svg")
