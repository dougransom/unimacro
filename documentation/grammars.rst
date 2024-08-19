Grammars
============

This section includes the available grammars in the unimacro project.

The defaultgrammars are automatically activated when unimacro is installed in the Natlink project. (Although not all grammars are by default activated when Dragon starts.)

The additional grammars are less tested at the moment, and should be put in another "user directory" in order to be used.

The default grammars are:

_control
  This grammar can control the state and give information about other unimacro grammars. This grammar should always be present and is always activated.

_brackets
  This grammar can print (in the foreground window) all sorts of brackets, either empty, optionally with the cursor put in between the brackets. Optionally text can be dictated to be put inside the brackets. This grammar is fairly simple, and can serve as a starting example.

_clickbyvoice
  With this grammar, you can follow links on a website, provided the clickbyvoice addin is installed in that browser.

_folders
  By far the most useful and most used grammar, although additional testing and improvements should be done. You can jump to predefined folders, but also to predefined files (that you use often), or to websites. A list of recent visited folders can be maintained, which allows you to quickly jump back to folders you recently visited.

_general
  A mixture of useful and more obsolete commands. Very useful, especially when developing unimacro, are info commands (like "give window info"). Also for example chaining variable names.

_lines
  For applications with numbered lines, like many programming IDE's, but also Excel, you can jump to a line, or to more lines (that are selected). Move or copy around a line or more lines.

_numbers simple
  Dictated numbers, with some additional options. This proves to be more reliable than dictating numbers in dictate mode, and even in Dragon "number mode". Also in windows in which dictation is not available, you can put numbers on the screen with this grammar.

_tags
  Put html tags on your screen, possibly with dictated text, or around text that you have selected. A bit analogous with the _brackets grammar, fairly simple and a good starting example if you are working with html.

_tasks
  This one can jump to tasks on your taskbar and more, like change size or placement of a window (a "task")or  move it to another monitor.

The additional grammars are less tested at the moment.


..  toctree::
    :maxdepth: 2
    
    defaultgrammars
    additionalgrammars
