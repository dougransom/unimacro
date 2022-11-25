#loads a file with the same name from Unimacro.UnimacroGrammars

from  pathlib import Path
from importlib import import_module, __import__
unimacro_grammar_file_name=__file__
module_to_load=Path(unimacro_grammar_file_name).stem
qualified_module_to_load=f"unimacro.UnimacroGrammars.{module_to_load}"
print(f"Loading {qualified_module_to_load}")
loaded1 =  __import__(qualified_module_to_load,globals(),locals())
v=vars(loaded1)
for k in v:
    globals()[k]=v[k]
del loaded1,v,k

