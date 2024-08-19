Default grammars
==============================================================================

The default grammars are briefly introduced above. 

_control
  This grammar is located in the unimacro repository (in the root). Normally in the site-packages directory of your python install.

The other grammars listed above (_brackets, _clickbyvoice, _folders, _general, _lines, _numbers simple, _tags and _tasks) are in the subdirectory UnimacroGrammars of that directory.

Configuration
------------------

Each grammar can be tuned to your wishes by a configuration file, named grammarname.ini. The so called ini file. Ini files play a central role in unimacro.

You can get info about a grammar and change these by calling "show brackets" or "edit brackets". (I take the grammar brackets as example). After changing something in the ini file, at next utterance, or at least at mic toggle, the grammar should be reloaded with the new info. If that does not work, you can say "switch on brackets", to force reload of the grammar.

A grammar can be switched off ("switch off brackets"), or switched on again ("switch on brackets"). The new state is put into the ini file, so preserved between sessions. When you want to view the state of the unimacro grammars, you can say "show all grammars". (Unfortunately the "details" of the info window shown with this command does not work yet.)




.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   control
   brackets
