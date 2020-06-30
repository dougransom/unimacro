"""template for _folders grammar, remember function.
This template is filled with the actual values and fired. It asks for a spoken form to "remember a given file", this value
is put in the _folders.ini config file.
"""

import wx
import time
import inivars

prompt = """Remember in Unimacro _folders grammar"""  # readable text
text = """Remember file "C:/faunabescherming/briefpapier/persbericht faunabescherming 30-6-2020.docx" for future calling?

Please give a spoken form for this file and choose OK; or Cancel..."""          # input text, the key of the 
inifile = "C:/Users/Gebruiker/Documents/unimacro_qh/nld_inifiles/_folders.ini"
section = "files"
value = "C:/faunabescherming/briefpapier/persbericht faunabescherming 30-6-2020.docx"
title = "test"
default = "persbericht faunabescherming dertig zes twee duizend twintig"
pausetime = 3  # should be replaced by 0 or a positive int value



def InputBox(text, prompt, title, default):
    """the dialog, which returns the spoken form"""
    app = wx.App()
    dialog = wx.TextEntryDialog(None,
    text, prompt, default, style=wx.OK|wx.CANCEL)
    if dialog.ShowModal() == wx.ID_OK:
        result = dialog.GetValue()
    else:
        result = None
    dialog.Destroy()
    return result

if __name__ == "__main__":
    result = InputBox(text, prompt, title, default)
    if result:
        key = result
        ini = inivars.IniVars(inifile)
        ini.set(section, key, value)
        ini.write()
        print('Wrote "%s = %s" to inifile'% (key, value))
        print('Call "edit folders" to edit or delete')
    else:
        print("Action canceled, no change of ini file")
    # if pausetime is given, launch as .py, otherwise launch as .pyw:
    if pausetime:
        # print "sleep: %s"% pausetime
        time.sleep(pausetime)
    