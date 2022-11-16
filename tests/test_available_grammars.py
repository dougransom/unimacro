import pytest

#@pytest.fixture
def expected_supplied_grammars():
    #NOTE that the supplied_grammars.txt file  must be update when a new grammar is added in 
    #UnimacroGrammars, run the powershell generateSuppliedGrammarList.ps1
    #we have to get rid of blank lines and trailing whitespace
    with open("supplied_grammars.txt") as supplied_grammars_file:
        return list(filter( lambda x: len(x)!=0, map(lambda line: line.rstrip(), supplied_grammars_file)))

def test_supplied_grammars_list():
    #we have to get rid of blank lines and trailing whitespace
    with open("supplied_grammars.txt") as supplied_grammars_file:
        supplied_grammars = list(filter( lambda x: len(x)!=0, [line.rstrip() for line in supplied_grammars_file]))
        print(f"Supplied grammars {supplied_grammars}")

print(f"expcted {expected_supplied_grammars()}")
 