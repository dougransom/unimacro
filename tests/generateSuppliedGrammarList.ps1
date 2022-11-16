Get-ChildItem ..\src\unimacro\UnimacroGrammars\*.py | 
    Where-Object {$_.Name -ne '__init__.py'} | 
    Format-Table -HidetableHeaders -Property Name 
    | Out-File   supplied_grammars.txt 