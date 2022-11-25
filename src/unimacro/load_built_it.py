#loads a file with the same name from Unimacro.UnimacroGrammars

from  pathlib import Path
from importlib import import_module
def load_unimacro_supplied_grammar(unimacro_grammar_file_name,):    
    """
    attempts to loads unimacro_grammar_file_name.
    """             
    module_to_load=Path(unimacro_grammar_file_name).stem
    return import_module(module_to_load,package="unimacro.UnimacroGrammars")

load_unimacro_supplied_grammar(__file__)