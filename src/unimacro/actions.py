# (unimacro - natlink macro wrapper/extensions)
# (c) copyright 2003 Quintijn Hoogenboom (quintijn@users.sourceforge.net)
#                    Ben Staniford (ben_staniford@users.sourceforge.net)
#                    Bart Jan van Os (bjvo@users.sourceforge.net)
#
# This file is part of a SourceForge project called "unimacro" see
# http://unimacro.SourceForge.net).
#
# "unimacro" is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, see:
# http://www.gnu.org/licenses/gpl.txt
#
# "unimacro" is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; See the GNU General Public License details.
#
# "unimacro" makes use of another SourceForge project "natlink",
# which has the following copyright notice:
#
# Python Macro Language for Dragon NaturallySpeaking
#   (c) Copyright 1999 by Joel Gould
#   Portions (c) Copyright 1999 by Dragon Systems, Inc.
#
# _actions.py 
#  written by: Quintijn Hoogenboom (QH softwaretraining & advies)
#  June 2003
#

"""This module contains actions that can be called from natlink grammars.

The central functions are "doAction" and "doKeystroke".

Extensive use is made from the ini file "actions.ini".

Editing actions, debugging actions and showing actions is performed through
special functions inside this module, but calling from another file (with
natlink grammar) is needed to activate these functions by voice.

"""
import re
import os
import sys
import types
import shutil
import os.path
import copy
import win32api
import win32gui
import win32con
import win32com.client
import inivars
import html.entities
import monitorfunctions
import messagefunctions
import autohotkeyactions # for AutoHotkey support
natut = __import__('natlinkutils')
natqh = __import__('natlinkutilsqh')
import natlink
import natlinkcorefunctions # extended environment variables....
import natlinkstatus
import time
import datetime
import subprocess  # for calling a ahk script
import utilsqh

external_actions_modules = {}  # the modules, None if not available (for prog)
external_action_instances = {} # the instances, None if not available (for hndle)
     
class ActionError(Exception): pass
class KeystrokeError(Exception): pass
class UnimacroError(Exception): pass
pendingMessage = ''
thisBaseDirectory = os.path.split(sys.modules[__name__].__dict__['__file__'])[0]

#####
##### get actions.ini from baseDirectory or SampleDirectory into userDirectory:
baseDirectory = natqh.getUnimacroDirectory()
if not baseDirectory:
    raise ImportError( 'no baseDirectory found while loading actions.py, stop loading this module')
sampleBase = baseDirectory

# get Unimacro sample directory:                 
sampleDirectory = os.path.join(baseDirectory, 'sample_ini')

if not os.path.isdir(sampleDirectory):
    print('\nNo Unimacro sample directory not found: %s\nCHECK YOUR CONFIGURATION!!!!!!!!!!!!!!!!\n'% sampleDirectory)
    sampleDirectory = ''

userDirectory = natqh.getUnimacroUserDirectory()

# check userDirectory, if false, actions.py is imported, probably from Vocola,
# actions.ini should go in the baseDirectory (Unimacro).
if userDirectory:
    if not os.path.isdir(userDirectory):
        raise IOError("The UnimacroUserDirectory does not exist: %s"% userDirectory)
    inifile = os.path.join(userDirectory, 'actions.ini')
    oldversioninifile = os.path.join(baseDirectory, 'actions.ini')
    if not os.path.isfile(oldversioninifile):
        oldversioninifile = ''
    debugFile = os.path.join(userDirectory, 'actions debug.txt')
else:
    # print 'Unimacro not enabled, use "actions.ini" in UnimacroDirectory: %s'% baseDirectory
    inifile = os.path.join(baseDirectory, 'actions.ini')
    oldversioninifile = ''
    debugFile = os.path.join(baseDirectory, 'actions debug.txt')
####

whatFile = os.path.join(os.environ['TEMP'],  __name__ + '.txt')
debugSock = None
samples = []

if not os.path.isfile(inifile):
    if userDirectory:  ## Unimacro enabled
        print('---try to find actions.ini file in old version (UnimacroDirectory) or sample_ini directory')
    else:
        print('---try to find actions.ini file in sample_ini directory')
        
    if os.path.isdir(sampleDirectory):
        sampleini = os.path.join(sampleDirectory, 'actions.ini')
        if os.path.isfile(sampleini):
            samples.append(sampleini)
        else:
            print("no valid 'actions.ini' file in %s"% sampleDirectory)
    else:
        print("no valid samples directory found for the (Unimacro) 'actions.ini' file: %s"% sampleDirectory)


    if userDirectory:       
        if os.path.isfile(oldversioninifile):
            samples.append(oldversioninifile)
            
    if not samples:
        raise IOError("cannot find a valid sample file 'actions.ini'")
    elif utilsqh.IsIdenticalFiles(samples):
        sample = samples[0]            
        print('----copy actions.ini -----:\nfrom %s\nto new location %s\n---'% (sample, inifile))
        shutil.copyfile(sample, inifile)
        if oldversioninifile in samples:
            print('----remove old actions.ini: %s\n---'% (oldversioninifile))
            os.remove(oldversioninifile)
            if os.path.isfile(oldversioninifile):
                print('----could not remove: %s'% oldversioninifile)
    else:
        newest = utilsqh.GetNewestFile(samples)
        print("Files 'actions.ini' are different,\ncopy newest %s to\nnew location %s\n---"% (newest, inifile))


if not os.path.isfile(inifile):
    if userDirectory:
        print("""

-------Cannot find a valid "actions.ini" configuraton file

This file is expected and needed in the
UnimacroUserDirectory (%s) in order
to let the Unimacro actions module work properly.

Copies of this file could not be found in one of the sample directories:
       (%s).
       
Also see http://qh.antenna.nl/unimacro/installation/inifilestrategy.html
---------
    
        """% (userDirectory, samples))
        time.sleep(0.2)
        raise ActionError('no inifile found for actions in unimacro or sample_ini')
    else:
        print("""

-------Cannot find a valid "actions.ini" configuraton file

This file is expected and needed in the
UnimacroDirectory (%s) in order
to let the Unimacro actions module work properly, while Unimacro itself is disabled.

Copies of this file could not be found in one of the sample directories:
       (%s).
       
Also see http://qh.antenna.nl/unimacro/installation/inifilestrategy.html
---------
    
        """% (baseDirectory, samples))
        time.sleep(0.2)
        raise ActionError('no inifile found for actions in unimacro or sample_ini')

if userDirectory and os.path.isfile(oldversioninifile):
    print('remove actions.ini from UnimacroDirectory (obsolete): %s\nis now in the UnimacroUserDirectory %s'% (oldversioninifile, userDirectory))
    os.remove(oldversioninifile)

if os.path.isfile(inifile):
    try:
        ini = inivars.IniVars(inifile)
    except inivars.IniError:
        
        print('Error in actions inifile: %s'% inifile)
        m = str(sys.exc_info()[1])
        print('message: %s'% m)
        pendingMessage = 'Please repair action.ini file\n\n' + m
        ini = None
        #win32api.ShellExecute(0, "open", inifile, None , "", 1)
else:
    raise IOError('no inifile found for Unimacro actions!')

metaActions = re.compile(r'(<<[^>]+>>)')
metaAction = re.compile(r'<<([^>]+)>>$')
metaNumber = re.compile(r' ([0-9]+)$')
metaNumberBack = re.compile(r'\bn\b')
actionIsList = re.compile('[,;\n]', re.M)
# for keystroke matching and splitting:
braceExact = re.compile (r'[{][^}]+[}]$')
hasBraces = re.compile (r'([{].+?[}])')
BracesExtractKey = re.compile (r'^[{]((alt|ctrl|shift)[+])*(?P<k>[^ ]+?)( [0-9]+)?[}]$', re.I)
        
# debugging and checking for changes (whenever actions are edited)
# are controlled to these global variables.  Whenever actions are edited
# through the function "editActions", checking for changes is performed
# until natlink is reloaded (or aNatSpeak is restarted)
debug = 0
checkForChanges = 0
iniFileDate = 0

def doAction(action, completeAction=None, pauseBA=None, pauseBK=None,
             progInfo=None, modInfo=None, sectionList=None, comment='', comingFrom=None):
    global pendingMessage, checkForChanges
    topLevel = 0
    if comingFrom and comingFrom.interrupted:
        print('command was interrupted')
        return

    if debug > 4: D("doAction: %s"% action)

    # at first (nonrecursive) call check for all variables:
    if not completeAction:
        # first (nonrecursive) call,
        topLevel = 1
        if not ini:
            checkForChanges = 1
            if pendingMessage:
                m = pendingMessage
                pendingMessage = ''
                Message(m, alert=1)
                D('no valid inifile for actions')
                return
        if checkForChanges:
            if debug > 5: D('checking for changes')
            doCheckForChanges() # resetting the ini file if changes were made
        if not ini:
            D('no valid inifile for actions')
            return
        if modInfo is None:
            try:
                modInfo = natlink.getCurrentModule()
                # print("modInfo through natlink: %s"% repr(modInfo))
            except:
                modInfo = autohotkeyactions.getModInfo()
                # print("modInfo through AHK: %s"% repr(modInfo))
           
        progNew = natqh.getProgName(modInfo)    

        if progInfo is None:
            progInfo = natqh.getProgInfo(modInfo=modInfo)
        #D('new progInfo: %s'% repr(progInfo))
        prog, title, topchild, classname, hndle = progInfo
        if sectionList == None:
            sectionList = getSectionList(progInfo)
        if pauseBA == None:
            pauseBA = float(setting('pause between actions', '0', sectionList=sectionList))
        if pauseBK == None:
            pauseBK = float(setting('pause between keystrokes', '0', sectionList=sectionList))

        if debug: D('------new action: %(action)s, '% locals())
        if debug > 3 and comment:
            D('extra info: %(comment)s'% locals())
        if debug > 3: D('\n\tprogInfo: %(progInfo)s, '
                        'pause between actions: %(pauseBA)s' % locals())
        if debug > 5: D('sectionList at start action: %s'% sectionList)
        completeAction = action
        aList = list(inivars.getIniList(action))
        if action.find('USC') >= 0:
            bList = []
            for a in aList:
                if a.find('USC') >= 0:
                    bList.extend(a.split('USC'))
                else:
                    bList.append(a)
            aList = [t.strip() for t in bList if t]
            
        if debug > 2: D('action: %s, aList: %s'% (action, aList))
        if not aList:
            return
        for a in aList:
            if comingFrom and comingFrom.interrupted:
                return
            result = 1
            if not a: continue
            result = doAction(a, completeAction=completeAction,
                         pauseBA=pauseBA, pauseBK=pauseBK,
                         progInfo=progInfo, modInfo=None, sectionList=sectionList,
                         comment=comment, comingFrom=comingFrom)
            if not result: return
            if debug > 2:D('pause between actions: %s'% pauseBA) 
            do_W(pauseBA)
        return result
    else:
        if debug > 5: D('action: %s'% action)

    if not action:  return

    assert type(action) == str

    # now perform the action
    # check if action consists of several parts:
    # assume progInfo is now available:
    prog, title, topchild, classname, hndle = progInfo
    
    if metaAction.match(action):  # exactly a meta action, <<....>>
        a = metaAction.match(action).group(1)
        aNew = getMetaAction(a, sectionList, progInfo)
        if type(aNew) == tuple:
            # found function
            func, number = aNew
            if type(func) in (types.FunctionType, types.UnboundMethodType):
                func(number)
                return 1
            else:
                print('Error, not a valid action "%s" for "%s" in program "%s"'% (func, action, prog))
                return
        if debug > 5: D('doing meta action: <<%s>>: %s'% (a, aNew))
        if aNew:
            aNewList = list(inivars.getIniList(aNew))
            res = 0
            for aa in aNewList:
                if aa:
                    if debug > 3: D('\tdoing part of meta action: <<%s>>: %s'% (a, aa))
                    res = doAction(aa, completeAction=completeAction,
                             pauseBA=pauseBA, pauseBK=pauseBK,
                             progInfo=progInfo, sectionList=sectionList,
                             comment=comment, comingFrom=comingFrom)
                    if not res: return
            return res
        elif aNew == '':
            if debug > 1: D('empty action')
            return 1
        else:
            if debug > 3: D('error in meta action: "%s"'% a)
            partCom = '<<%s>>'%a
            t = '_actions, no valid meta action: "%s"'% partCom
            if partCom != completeAction:
                t += '\ncomplete command: "%s"'% completeAction
            raise ActionError(t)

    # try qh command:
    if action.find('(') > 0 and action.strip().endswith(')'):
        com, rest = tuple([t.strip() for t in action.split('(', 1)])
        rest = rest.strip()[:-1]
    elif action.find(' ') > 0:
        com, rest = tuple([t.strip() for t in action.split(' ',1)])
    else:
        com, rest = action.strip(), ''

    if 'do_'+com in globals():
        funcName = 'do_'+com
        args = convertToPythonArgs(rest)
        kw = {}
        kw['progInfo'] = progInfo
        kw['comingFrom'] = comingFrom
        func = globals()[funcName]
        if not type(func) == types.FunctionType:
            raise UnimacroError('appears to be not a function: %s (%s)'% (funcName, func))
        if debug > 5: D('doing USC command: |%s|, with args: %s and kw: %s'% (com, repr(args), kw))
        if debug > 1: do_W(debug*0.2)
        if args:
            result = func(*args, **kw)
        else:
            result = func(**kw)
                
        if debug > 5: print('did it, result: %s'% result)
        if debug > 1: do_W(debug*0.2)
        # skip pause between actions
        #do_W(pauseBA)
        return result

    # try meta actions inside:
    if metaActions.search(action): # action contains meta actions
        As = [t.strip() for t in metaActions.split(action)]
        if debug > 5: D('meta actions: %s'% As)
        for a in As:
            if not a: continue
            res = doAction(a, completeAction,
                     pauseBA=pauseBA, pauseBK=pauseBK, 
                     progInfo=progInfo, sectionList=sectionList,
                     comment=comment, comingFrom=comingFrom)
            if not res: return
            do_W(pauseBA)
            # skip pause between actions
            #do_W(pauseBA)
        return 1

    # try natspeak command:

    if com in natspeakCommands:
        rest = convertToDvcArgs(rest)
        C = com + ' ' + rest
        if debug: D('do dvc command: |%s|'% C)
        if debug > 1: do_W(debug*0.2)
        natlink.execScript(com + ' ' + rest)
        if debug > 5: print('did it')
        if debug > 1: do_W(debug*0.2)
        # skip pause between actions
        #do_W(pauseBA)
        return 1

    # all the rest:
    if debug > 5: D('do string: |%s|'% action)
    if debug > 1: do_W(debug*0.2)
    if action:
        doKeystroke(action, pauseBK=pauseBK,
                 progInfo=progInfo, sectionList=sectionList)
        if debug > 5: print('did it')
        if debug > 1: do_W(debug*0.2)
        # skip pause between actions
        #do_W(pauseBA)
        if topLevel: # first (nonrecursive) call,
            print('end of complete action')
        return 1
    else:
        if debug:
            print('empty keystrokes')
         #     
        
def doKeystroke(action, hardKeys=None, pauseBK=None,
                     progInfo=None, sectionList=None):
    global pendingMessage, checkForChanges
    #print 'doing keystroke: {%s'% action[1:]
    if not action:
        return
    ### bugfix as proposed by Frank Olaf:
    #if not action.startswith("{shift}"):
    #    action = "{shift}" + action

    if not ini:
        checkForChanges = 1
        if pendingMessage:
            m = pendingMessage
            pendingMessage = ''
            Message(m, alert=1)
            D('no valid inifile for actions')
            return
    if checkForChanges:
        if debug > 5: D('checking for changes')
        doCheckForChanges() # resetting the ini file if changes were made# 
    if not ini:
        D('no valid inifile for keystrokes')
    if type(hardKeys) != str:
        hardKeys = [hardKeys]
    elif hardKeys == 1:
        hardKeys = ['all']
    elif hardKeys == 0:
        hardKeys = ['none']

    if debug > 5: D('doKeystroke, pauseBK: %s, hardKeys: %s'% (pauseBK, hardKeys))

    if pauseBK == None or hardKeys == None:
        if sectionList == None:
            sectionList = getSectionList(progInfo)
        if pauseBK == None:
            pauseBK = int(setting('pause between keystrokes', '0',
                                  sectionList=sectionList))
        if hardKeys == None:
            hardKeys = setting('keystrokes with systemkeys', 'none', sectionList=sectionList)
            if debug > 5: D('hardKeys setting: |%s|'% hardKeys)

            hardKeys = actionIsList.split(hardKeys)
            if hardKeys:
                hardKeys = [k.strip() for k in hardKeys]
                if debug > 5: D('hardKeys as list: |%s|'% hardKeys)

        if debug > 5: D('new keystokes: |%s|, hardKeys: %s, pauseBK: %s'%
                        (action, hardKeys, pauseBK))

        
    elif debug > 5:
        D('keystokes: |%s|, hardKeys: %s, pauseBK: %s'%
                        (action, hardKeys, pauseBK))
    if pauseBK:
       l = hasBraces.split(action)
       for k in l:
           if not k:
               continue
           elif braceExact.match(action):
               doKeystroke(k, hardKeys=hardKeys, pauseBK = 0)
           else:
               for K in k:
                   doKeystroke(K, hardKeys=hardKeys, pauseBK = 0)
           if debug > 5: D('pausing: %s msec after keystroke: |%s|'%
                           (pauseBK, k))
           # skip pausing between keystrokes
           #do_W(pauseBK)
    elif braceExact.match(action):
        # exactly 1 {key}:
        if debug > 5: D('exact action, hardKeys[0]: %s'% hardKeys[0])
        if hardKeys[0] == 'none':
            natut.playString(action)  # the fastest way
            return
        elif hardKeys[0] == 'all':
            natut.playString(action, natut.hook_f_systemkeys)
            return
        m = BracesExtractKey.match(action)
        if m:
            # the key part is known and valid word
            # eg tab, down etc
            keyPart = m.group(0).lower()
            for mod in 'shift+', 'ctrl+', 'alt+':
                if keyPart.find(mod)>0: keyPart = keyPart.replace(mod, '')
            if keyPart in hardKeys:
                if debug > 3: D('doing "hard": |%s|'% action)
                natut.playString(action, natut.hook_f_systemkeys)
                return
            else:
                if debug > 3: D('doing "soft" (%s): |%s|'% (action, hardKeys))
                natut.playString(action)  # fastest way
                return
        else:
            if debug > 3: D('doing "soft" (%s): |%s|'% (action, hardKeys))
            natut.playString(action)
            return
        
    # now proceed with more complex keystroke possibilities:
    if hardKeys[0]  == 'all':
        natut.playString(action, natut.hook_f_systemkeys)
        return
    elif hardKeys[0]  == 'none':
        natut.playString(action)
        return
    if hasBraces.search(action):
        keystrokeList = hasBraces.split(action)
        for k in keystrokeList:
            if debug > 5: D('part of keystrokes: |%s|' % k)
            if not k: continue
            #print 'recursing? : %s (%s)'% (k, keystrokeList)
            doKeystroke(k, hardKeys=hardKeys, pauseBK = 0)
    else:
        if debug > 5: D('no braces keystrokes: |%s|' % action)
        natut.playString(action)
        
def getMetaAction(a, sectionList=None, progInfo=None):
    if progInfo is None:
        progInfo = natqh.getProgInfo()
    if sectionList is None:
        sectionList = getSectionList(progInfo)
    
    m = metaNumber.search(a)
    if m:
        number = m.group(1)
        A = a.replace(number, 'n')
        actionName = a.replace(number, '')
        actionName = actionName.replace(' ', '')
    else:
        A = a
        number = 0
        actionName = a.replace(' ', '')
    # try via actions_prog module:
    ext_instance = get_instance_from_progInfo(progInfo)
    if ext_instance:
        prog = progInfo[0]
        funcName = 'metaaction_%s'% actionName
        func = getattr(ext_instance,funcName, None)
        if func:
            if debug > 1:
                D('action by function from prog %s: |%s|(%s), arg: %s'% (prog, actionName, funcName, number))
            result = func, number
            if result: return result
            # otherwise go on with "normal" meta actions...

    # no result in actions_prog module, continue normal way:
    if debug > 5: D('search for action: |%s|, sectionList: %s' %
                    (A, sectionList))
    
    aNew = setting(A, default=None, sectionList=sectionList)
    if aNew == None:
        print('action: not found, meta action for %s: |%s|, searched in sectionList: %s' % \
              (a, aNew, sectionList))
        return 
    if m:
        aNew = metaNumberBack.sub(number, aNew)
    if debug:
        section = ini.getMatchingSection(sectionList, A)
        D('<<%s>> from [%s]: %s'% (A, section, aNew)) 
    return aNew        
    
natspeakCommands = ['ActiveControlPick', 'ActiveMenuPick', 'AppBringUp', 'AppSwapWith', 'Beep', 'ButtonClick',
 'ClearDesktop', 'ControlPick', 'DdeExecute', 'DdePoke', 'DllCall', 'DragToPoint', 'GoToSleep', 
 'HeardWord', 'HtmlHelp', 'MenuCancel', 'MenuPick', 'MouseGrid', 'MsgBoxConfirm', 'PlaySound',
 'RememberPoint', 'RunScriptFile', 'SendKeys', 'SendSystemKeys', 'SetCharFormat', 'SetMicrophone',
 'SetMousePosition', 'SetNaturalText', 'ShellExecute', 'TTSPlayString', 'Wait', 'WakeUp', 'WinHelp',
 'SetRecognitionMode']
# last one undocumented, only for version 7

def getSectionList(progInfo=None):
    if not progInfo:
        progInfo = natqh.getProgInfo()
    prog, title, topchild, classname, hndle = progInfo
    if debug > 5:
        D('search for prog: %s and title: %s' % (prog, title))
        D('type prog: %s, type title: %s'% (type(prog), type(title)))
    prog = utilsqh.convertToUnicode(prog)
    title = utilsqh.convertToUnicode(title)
    L = ini.getSectionsWithPrefix(prog, title)
    L2 = ini.getSectionsWithPrefix(prog, topchild)  # catch program top or program child
    for item in L2:
        if not item in L:
            L.append(item)
    L.extend(ini.getSectionsWithPrefix('default', topchild)) # catcg default top or default child
    if debug > 5: D('section list with progInfo: %s:\n===== %s' %
                    (progInfo, L))
                    
    return L

def convertToDvcArgs(text):
    text = text.strip()
    if not text:
        return ''
    L = text.split(',')
    L = list(map(_convertToDvcArg, L))
    return ', '.join(L)

hasDoubleQuotes = re.compile(r'^".*"$')
hasSingleQuotes = re.compile(r"^'.*'$")
hasDoubleQuote = re.compile(r'"')
def _convertToDvcArg(t):
    t = t.strip()
    if not t: return ''
    if debug > 1: D('convertToDvcArg: |%s|'%t)

    # if input string is a number, return string directly
    try:
        i = int(t)
        return t
    except ValueError:
        pass
    try:
        f = float(t)
        return t
    except ValueError:
        pass

    # now proceeding with strings:    
    if hasDoubleQuotes.match(t):
        return t
    elif hasSingleQuotes.match(t):
        if len(t) > 2:
            return '"' + t[1:-1] + '"'
        else:
            return ""
    if t.find('"') > 0:
        t = t.replace('"', '""')
    return '"%s"'%t

def convertToPythonArgs(text):
    """convert to numbers and strings,

    IF argument is enclosed in " " or ' ' it is kept as a string.

    """    
    text = text.strip()
    if not text:
        return    # None
    L = text.split(',')
    L = list(map(_convertToPythonArg, L))
    return tuple(L)

def _convertToPythonArg(t):
    t = t.strip()
    if not t: return ''
    if debug > 1: D('convertToPythonArg: |%s|'%t)

    # if input string is a number, return string directly
    try:
        i = int(t)
        if t == '0':
            return 0
        if t.startswith('0'):
            print('warning convertToPythonArg, could be int, but assume string: %s'% t)
            return '%s'% t
        return i
    except ValueError:
        pass
    try:
        f = float(t)
        if t.find(".") >= 0:
            return f
        else:
            print('warning convertToPythonArg, can be float, but assume string: %s'% t)
            return '%s'% t
    except ValueError:
        pass

    # now proceeding with strings:    
    if hasDoubleQuotes.match(t):
        return t[1:-1]
    elif hasSingleQuotes.match(t):
        return t[1:-1]
    else:
        return t
##    elif hasDoubleQuote.search(t):
##        return "'%s'"% t
##    else:
##        return '"%s"'% t
        

def getFromIni(keyword, default='',
                sectionList=None, progInfo=None):
    if not ini:
        return ''
    if sectionList == None:
        if progInfo == None: progInfo = natqh.getProgInfo()
        prog, title, topchild, classname, hndle = progInfo
        sectionList = ini.getSectionsWithPrefix(prog, title) + \
                      ini.getSectionsWithPrefix('default', title)
        if debug > 5: D('getFromIni, sectionList: |%s|' % sectionList)
    value = ini.get(sectionList, keyword, default)
    if debug > 5: D('got from setting/getFromIni: %s (keyword: %s'% (value, keyword))
    return value

setting = getFromIni

def get_external_module(prog):
    """try to import actions_prog and put in external_actions_modules
    
    if module not there, put None in this external_actions_modules dict
    """
    #print 'ask for program: %s'% prog
    if prog in external_actions_modules:
        return external_actions_modules[prog]
    try:
        modname = '%s-actions'% str(prog)
        _temp = __import__('actionclasses', fromlist=[modname])
        mod = getattr(_temp, modname)
        external_actions_modules[prog] = mod
        print('get_external_module, found actions module: %s'% modname)
        return mod
    except AttributeError:
        import traceback
        external_actions_modules[prog] = None
        # print 'get_external_module, no module found for: %s'% prog
 
def get_instance_from_progInfo(progInfo):
    """return the correct intances for progInfo
    """
    prog, title, topchild, classname, hndle = progInfo
    prog = str(prog)
    if hndle in external_action_instances:
        instance = external_action_instances[hndle]
        instance.update(progInfo)
        return instance
    
    mod = get_external_module(str(progInfo[0]))
    if not mod:
        # print 'no external module instance: %s'% progInfo[0]
        return # no module, no instance
    classRef = getattr(mod, '%sActions'% prog.capitalize())
    if classRef:
        instance = classRef(progInfo)
        instance.update(progInfo)
        print('new instance for actions for prog: %s, hndle: %s'% (prog, hndle))
    else:
        instance = None
    external_action_instances[hndle] = instance

    return instance

def doCheckForChanges(previousIni=None):
    global  ini, iniFileDate, topchildDict, childtopDict
    newDate = natqh.getFileDate(inifile)
    if newDate > iniFileDate:
        D('----------reloading ini file')
        try:
            topchildDict = None
            childtopDict = None
            ini = inivars.IniVars(inifile)
        except inivars.IniError:
            msg = 'repair actions ini file: \n\n' + str(sys.exc_info()[1])
            #win32api.ShellExecute(0, "open", inifile, None , "", 1)
            time.sleep(0.5)
            Message(msg)
            iniFileDate = newDate
            ini = previousIni
        iniFileDate = newDate


def writeDebug(s):
    if debugSock:
        debugSock.write(s+'\n')
        debugSock.flush()
        print('_actions: %s' % s)
    else:
        print('_actions debug: %s'% s)
       
D =writeDebug
def debugActions(n, openMode='w'):
    global debug, debugSock
    debug = n
    print('setting debug actions: %s'% debug)
    if debugSock:
        debugSock.close()
        debugSock = None
    if n:
        debugSock = open(debugFile, openMode)
        
        


def debugActionsShow():
    print('opening debugFile: %s automatically is disabled.'% debugFile)
    #win32api.ShellExecute(0, "open", debugFile, None , "", 1)
    

def showActions(progInfo=None, lineLen=60, sort=1, comingFrom=None, name=None):
    if progInfo == None:
        progInfo = natqh.getProgInfo()
    language = natqh.getLanguage()
    
    sectionList = getSectionList(progInfo)

    l = ['actions for program: %s\n\twindow title: %s (topchild: %s, windowHandle: %s)'% progInfo,
         '\tsection list: %s'% sectionList,
         '']
    l.append(ini.formatKeysOrderedFromSections(sectionList,
                                lineLen=lineLen, sort=sort))
    
    T = getTranslation  # local function here, because no knowledge of the grammars is here
    l.append(T(language, dict(enx= '\n"edit actions" to edit the actions',
                              nld='\n"bewerk acties" om de acties te bewerken')))
    l.append(T(language, dict(enx='"show actions" gives this list',
                            nld= '"toon acties" geeft deze lijst')))
    l.append(T(language, dict(enx='"trace actions (on|off|0|1|...|10)" sets/clears trace mode',
                              nld='"trees acties (aan|uit|0|1|...|10)" zet trace modus aan of uit')))
    l.append(T(language, dict(enx='consult grammar "control" for the exact commands',
                              nld='raadpleeg grammatica "controle" voor de precieze commando\'s')))
    
    sock = open(whatFile, 'w')
    sock.write('\n'.join(l))
    sock.close()
    if comingFrom:
        name=name or ""
        comingFrom.openFileDefault(whatFile, name=name)
    else:
        print('show file: ', whatFile)
        print('showing actions by ShellExecute crashed NatSpeak, please open by hand above file')
    #win32api.ShellExecute(0, "open", whatFile, None , "", 1)

def getTranslation(language, Dict):
    """get with self.language as key the text from dict, if invalid, return 'enx' text
    """
    if language in Dict:
        return Dict[language]
    else:
        return Dict['enx']


def editActions(comingFrom=None, name=None):
    global checkForChanges, iniFileDate, topchildDict, childtopDict
    iniFileDate = natqh.getFileDate(inifile)
    checkForChanges = 1
    topchildDict = None
    childtopDict = None
    if comingFrom:
        name=name or ""
        comingFrom.openFileDefault(inifile, name=name)
    else:
        print('inifile: ', inifile)
        print('editing actions by ShellExecute crashed NatSpeak, please edit by hand above file')
    #win32api.ShellExecute(0, "open", inifile, None , "", 1)

def setPosition(name, pos, prog=None):
    """set in inifile, section 'positions'
    use prog for program specific positions
    """
    global checkForChanges, iniFileDate
    iniFileDate = natqh.getFileDate(inifile)
    checkForChanges = 1
    if prog:
        section = 'positions %s'% prog
    else:
        section = 'positions'
    ini.set(section, name, pos)
    natqh.Wait(0.1)
    ini.write()

def getPosition(name, prog=None):
    """get from inifile, section 'positions'
    for application specific gets, use prog as programSpecific
    
    """
    if prog:
        section = 'positions %s'% prog
    else:
        section = 'positions'
    return ini.getInt(section, name) or 0
# -----------------------------------------------------------

def do_TEST(*args, **kw):
    # x, y = natqh.testmonitorinfo(args[0], args[1])
    # print 'in do_test: ', x, y
    import ctypes
    tup = natlink.getCurrentModule()
    hndle = tup[2]
    print('foreground hndle: %s, type: %s'% (hndle, type(hndle)))
    curprog = ctypes.windll.user32.GetForegroundWindow()
    print('curprog: %s'% curprog)
    # result = ctypes.windll.user32.GetGUIThreadInfo(hndle, info)
    # 
    # print('result: %s'% result)
    # print('info: %s'% repr(info))
    # print('dir info: %s'% dir(info))
    kbLayout = ctypes.windll.user32.GetKeyboardLayout(0)
    print('kbLayout: %s'% kbLayout)


def do_AHK(script, **kw):
    """try autohotkey integration
    """
    result = autohotkeyactions.do_ahk_script(script)
    if type(result) == str:
        do_MSG(result)
        return
    return result

# HeardWord (recognition mimic), convert arguments to list:
def do_HW(*args, **kw):
    words = list(args)
    origWords = copy.copy(words)
##    print 'origWords for HW(recognitionMimic): |%s| (length: %s)'% (origWords, len(origWords))
    
    if len(words)  == 1:
        if words[0].find(',') > 0:
            words = words[0].split(',')
        else:
            words = words[0].split()
                    
    try:
        if debug > 3:
            D('words for HW(recognitionMimic): |%s|'% words)
        natlink.recognitionMimic(words)
    except:
        if words != origWords:
            try:
                if debug > 3:
                    D('words for HW(recognitionMimic): |%s|'% origWords)
                natlink.recognitionMimic(origWords)
            except:
                print("action HW probably has invalid words (splitted: %s) or (glued together: %s)" % \
                                 (words, origWords))
                return
        else:
            print("Cannot recognise words, HW probably has invalid words: %s" % words)
            return
    return 1

def do_MP(scrorwind, x, y, mouse='left', nClick=1, **kw):
    # Mouse position and click.
    # first parameter 0, absolute
    # new 2017: 3 = relative to active monitor
    # and 4 - relative to work area of active monitor (not considering task bar or dragon bar)
    if not scrorwind in [0,1,2,3,4,5]:
        raise UnimacroError('Mouse action not supported with relativeTo: %s' % scrorwind)
    # first parameter 1: relative:
    natqh.doMouse(0,scrorwind,x,y,mouse,nClick)  # abs, rel to window, x, y, click
    return 1

def do_CLICK(mouse='left', nClick=1, **kw):
    scrorwind = 2
    x, y, = 0, 0
    # click at current position:
    natqh.doMouse(0,scrorwind,x,y,mouse,nClick) 
    return 1


def do_ENDMOUSE(**kw):
    natqh.endMouse()
    return 1
    
def do_CANCELMOUSE(**kw):
    natqh.cancelMouse()
    return 1

def do_MDOWN(button='left', **kw):
    natqh.mousePushDown(button)
    return 1

def do_RM(**kw):
    natqh.rememberMouse()
    return 1
 
def do_MOUSEISMOVING(**kw):
    xold, yold = natlink.getCursorPos()
    time.sleep(0.05)
    for i in range(2):
        x, y = natlink.getCursorPos()
        time.sleep(0.05)
        if not (x == xold and y == yold):
            return 1
    return 0
    

def do_WAITMOUSEMOVE(**kw):
    """wait for the mouse start moving
    
    cancel after 2 seconds
    """
    xold,yold = natlink.getCursorPos()
    for i in range(40):
        time.sleep(0.05)
        x, y = natlink.getCursorPos()
        if x != xold or y != yold:
            return 1
    else:
        print('no mouse move detected, cancel action')
        return 0  # no result

def do_WAITMOUSESTOP(**kw):
    """wait for the mouse stops moving
    
    you get 2 seconds for stopping the movement.
    If you move more than 200 in x or y direction, the function is cancelled (with error)
    
    return value: 1 if succes
                  None is failure
    
    """
    natlink.setMicState('off')
    xstart, ystart = xold,yold = natlink.getCursorPos()

    while 1:
        time.sleep(0.05)
        x, y = natlink.getCursorPos()
        if x == xold and y == yold:
            for j in range(10):
                # check if it remains so (half a second)
                time.sleep(0.05)
                x, y = natlink.getCursorPos()
                if x != xold or y != yold:
                    break
            else:
                print('mouse stopped moving')
                natlink.setMicState('on')
                return 1
        if (x-xold)*(x-xold) + (y-yold)*(y-yold) > 100*100:
            print("user canceled WAITMOUSESTOP canceled by moving mouse more than 100 pixels")
            return
        xold, yold = x, y
        if natlink.getMicState() == "on":
            print('user canceled WAITMOUSESTOP by switching on microphone')
            return

def do_CHECKMOUSESTEADY(**kw):
    """returns 1 if the mouse is steady
    
    for 2.5 seconds
    """
    xold, yold = natlink.getCursorPos()
    for i in range(50):
        time.sleep(0.05)
        x, y = natlink.getCursorPos()
        if x == xold and y == yold:
            for j in range(10):
                # check if it remains so (half a second
                time.sleep(0.05)
                x, y = natlink.getCursorPos()
                if x != xold or y != yold:
                    break
            else:
                print('mouse stopped moving')
                natlink.setMicState('on')
                return 1



def do_CLICKIFSTEADY(mouse='left', nClick=1, **kw):
    """clicks only if mouse is steady,
    
    beeps if it was moving before, if it is steady just click
    returns 0 if it keeps moving
    """
    natqh.doMouse(0,scrorwind,x,y,mouse,nClick) 
    return 1


def do_RMP(scrorwind, x, y, mouse='left', nClick=1, **kw):
    # relative mouse position and click
    # new 2017: 3 = relative to active monitor
    if not scrorwind in [0,1,3,5]:
        raise UnimacroError('Mouse action not supported with relativeTo: %s' % scrorwind)
    # first parameter 1: relative:
    natqh.doMouse(1,scrorwind,x,y,mouse,nClick)  # relative, rel to window, x, y,click
    return 1
    
def do_PRMP(all=0, **kw):
    # print relative mouse position
    natqh.printMousePosition(1,all)  # relative
    return 1
    

def do_PMP(all=0, **kw):
    # print absolute mouse position
    natqh.printMousePosition(0,all)  # absolute
    return 1

def do_PALLMP(**kw):
    # print all mouse positions
    natqh.printMousePosition(0,1)  # absolute
    natqh.printMousePosition(1,1)  # relative
    

# Get the NatSpeak main menu:
def do_NSM(**kw):
    modInfo = natlink.getCurrentModule()
    prog = natqh.getProgName(modInfo)
    if prog == 'natspeak':
        if modInfo[1].find('DragonPad') >= 0:
            natut.playString('{alt+n}')
            return 1
    natlink.recognitionMimic(["NaturallySpeaking"])
    return natqh.waitForWindowTitle(['DragonBar', 'Dragon-balk', 'Voicebar'],10,0.1)


# shorthand for sendsystemkeys:
def do_SSK(s, **kw):
    natut.playString(s, natut.hook_f_systemkeys)
    return 1

def do_S(s, **kw):
    """do a simple keystroke
    temporarily with {shift} in front because of bugworkaround (Frank)
    """
    doKeystroke(s)
    return 1


def do_ALTNUM(s, **kw):
    """send keystrokes with alt and numkey inserted
    
    werkt niet!!
    """
    if type(s) == int:
        s = str(s)
    keydown = natut.wm_syskeydown
    keyup = natut.wm_syskeyup
    
    altdown = (keydown, natut.vk_menu, 1)
    altup = (keyup, natut.vk_menu, 1)
    numkeyzero = win32con.VK_NUMPAD0

    sequence = [altdown]
    for code in s:
        if not code in '0123456789':
            print('code should be a digit, not: %s (%s)'% (code, s))
            return
        i = int(s)
        keycode = numkeyzero + int(code)
        sequence.append( (keydown, keycode, 1))
        sequence.append( (keyup, keycode, 1))
    sequence.append(altup)
    natlink.playEvents(sequence)
    
def do_SCLIP(*s, **kw):
    """send keystrokes through the clipboard
    """
    natqh.saveClipboard()
    natqh.Wait()    
    ## actions should be able to catch , in string, now , seems to be separator for
    ## function parameters.
    ## assume , = ", "
    ## also assume {enter} = newline. No {enter 2}  etc recognised
    # print 's: %s type: %s'% (s, type(s))
    total = ', '.join(str(part) for part in s)
    #if len(s) > 1:
    #    for i, t in enumerate(s):
    #        print "SCLIP:", i, t
    total = total.replace("{enter}", "\n")
    # print 'SCLIP: %s type: %s'% (total, type(total))
    natqh.setClipboard(total, format=13)
    natqh.Wait()
    #print 'send through clipboard: %s'% total5N
    doAction("<<paste>>")
    natqh.Wait()
    natqh.restoreClipboard() 


def do_RW(**kw):
    natqh.rememberWindow()
    return 1

def do_CW(**kw):
    """obsolete..."""
    natqh.clearWindowHandle()
    return 1

def do_RTW(**kw):
    natqh.returnToWindow()
    return 1

def do_SELECTWORD(count=1, direction=None, **kw):
    """select the word under the cursor"""
    print('try to select %s word(s) under cursor (direction: %s)'% (count, direction))
    natqh.saveClipboard()
    if not direction in ['left', 'right']:
        # try if at end of word:
        doKeystroke("{extright}{shift+extleft}{ctrl+c}{extright}{extleft}")
        t = natqh.getClipboard()
        if t in utilsqh.letters:
            direction = 'right'
            print('make direction right')
        else:
            direction = 'left'
            print('make direction left')
    if direction == 'left':
        doKeystroke("{extleft}{ctrl+extright}{shift+ctrl+extleft %s}"% count)
    elif direction == 'right':
        doKeystroke("{extright}{ctrl+extleft}{shift+ctrl+extright %s}"% count)

    natqh.Wait()
    doAction("<<copy>>")
    natqh.visibleWait()
    t = natqh.getClipboard()
    if len(t) == 1 and t in utilsqh.letters:
        pass
    elif direction == 'left':
        while t and t.startswith(' '):
            doKeystroke("{shift+extright}")
            t = t[1:]
    else:
        while t and t.endswith(' '):
            doKeystroke("{shift+extleft}")
            t = t[:-1]
    natqh.restoreClipboard()
    #print 'SELECTWORD, selected word: |%s| (leave on clipboard: %s'% (repr(t), repr(natqh.getClipboard()))
    return t


# wait 20 (default) times standard waitingtime (default 0.05 seconds)
# (so default = 1 second)
# for a new window title, if no title is given
# wait for a change
def do_WTC(nWait=20, waitingTime=0.05, **kw):
    """wait for a change in window title, on succes return 1
    
    after found, check also if title is stable
    """
    return natqh.waitForNewWindow(nWait, waitingTime, **kw)
##    natqh.ForceGotBegin()

# wait for Window Title
def do_WWT(titleName, nWait=20, waitingTime=0.05, **kw):
    """wait for specified window title, on succes return 1
    """
    return natqh.waitForWindowTitle(titleName, nWait, waitingTime, **kw)
  
# waiting function:
def do_W(t=None, **kw):
    t = t or 0.1
    if debug > 7: D('waiting: %s'%t)
    elif debug and t > 2: D('waiting: %s'%t)
    natqh.Wait(t)
    return 1
        
do_WAIT = do_W
# Long Wait:
def do_LW(**kw):
    natqh.longWait()
    return 1
do_LONGWAIT = do_LW
# Visible Wait:
def do_VW(**kw):
    natqh.visibleWait()
    return 1
do_VISIBLEWAIT = do_VW

# Short Wait:
def do_SW(**kw):
    natqh.shortWait()
    return 1
do_SHORTWAIT = do_SW

def do_KW(action1=None, action2=None, progInfo=None, comingFrom=None):
    """kill window

    """
    if action1:
        if action2:
##        print 'KW with: %s'% action1
            killWindow(action1, action2, progInfo=progInfo, comingFrom=comingFrom)
        else:
            killWindow(action1, progInfo=progInfo, comingFrom=comingFrom)
    else:
##        print 'KW without action 1'
        killWindow(progInfo=progInfo, comingFrom=comingFrom)
    return 1

## def do_RS():
##     """reformat selection, cleaning newlines

##     """
##     natqh.saveClipboard()
##     doKeystroke('{ctrl+c}')
##     t = natqh.getClipboard()
##     natqh.restoreClipboard()
##     if t:
##         T = natqh.cleanParagraphs(t)
##         doKeystroke(T)
##     else:
##         print 'reformat selection (RS) requires a selection first'

def do_DATE(Format=None, Action=None, **kw):
    """give today's date

    format maybe adapted, default = "%d/%m"    
    action maybe adapted, default = "print",
        alternatives are "speak"
    """
    formatStrip = 0
    if Format is None or Format == 0:
        if Action in ['speak']:
            formatStrip = 0
            Format = "%B %d"
        else:
            formatStrip = 1
            Format = "%m/%d"
        
    cdate = datetime.date.today()
    fdate = cdate.strftime(Format)
    if Action in [None, 0, "print"]:
        if formatStrip:
            fdate = fdate.lstrip('0')
            fdate = fdate.replace('/0', '/')
            print('stripped fdate: |%s|'% fdate)
        doKeystroke(fdate)
    elif Action in ['speak']:
        command = 'TTSPlayString "%s"'% fdate
        natlink.execScript(command)
    else:
        print('invalid Action for DATE: %s'% Action)
    return 1

def do_TIME(Format=None, Action=None, **kw):
    """give current time

    Format maybe adapted, default = "%H:%M"    
    Action maybe adapted, default = "print",
        alternatives are "speak"
    """
    ctime = datetime.datetime.now().time()
    formatStrip = 0
    if Format is None or Format == 0:
        if Action in ['speak']:
            formatStrip = 0
            Format = "%H:%M"
        else:
            formatStrip = 1
            Format = "%H:%M"
        
    ftime = ctime.strftime(Format)
    if Action in [None, "print"]:
        doKeystroke(ftime)
    elif Action in ['speak']:
        command = 'TTSPlayString "%s"'% ftime
        natlink.execScript(command)
    else:
        print('invalid Action for DATE: %s'% Action)
        
    return 1

Date = do_DATE

def do_SPEAK(t, **kw):
    """speak text through TTSPlayString
    """
    command = 'TTSPlayString "%s"'% t
    natlink.execScript(command)

def do_PRINT(t, **kw):
    """print text to Messages of Python Macros window
    """
    print(t)

def do_PRINTALLENVVARIABLES(**kw):
    """print all environment variables to the messages window
    """
    print('-'*40)
    print('These can be used for "expansion", as eg %NATLINKDIRECTORY% in the grammar _folders and other places:')
    natlinkcorefunctions.printAllEnvVariables()
    print('-'*40)

def do_PRINTNATLINKENVVARIABLES(**kw):
    """print all environment variables to the messages window
    """
    natlinkEnvVariables = natlinkstatus.AddNatlinkEnvironmentVariables()
    print('-'*40)
    print('These can be used for "expansion", as eg %NATLINKDIRECTORY% in the grammar _folders and other places:')
    for k in sorted(natlinkEnvVariables.keys()):
        print("%s\t%s"% (k, natlinkEnvVariables[k]))
    print('-'*40)
    
def do_T(**kw):
    """return true only"""
    return 1

def do_F(**kw):
    """return false only (empty action will do as well)"""
    return 

def do_A(n, **kw):
    """print ascii code

    A 208 prints the ETH character
    

    """
    doKeystroke(chr(n))
    return 1

def do_U(n, **kw):
    """print unicode code
    U Delta
    U 00cb  (Euml)
    U Alpha or U 0391 (same) (numbers are the hex code, like in the word insert symbol dialog.



    """
    if type(n) != str:
        Code = html.entities.name2codepoint.get(n, n)
        if type(Code) == int:
            # is in defs
            pass
        else:
            # some 4 letter hexcode:
            # print 'stringlike code: %s, convert to hex number'% Code
            exec("Code = 0x%s"% Code)
    elif type(n) == int:
        # intended as hex code, but by unimacro converted into int. 
        # convert to back to hex:
        # print 'numlike code, convert to hex: %s'% n
        exec("Code = 0x%.4d"% n)
    else:
        raise ValueError("action U, invalid type of %s (%s)"% (n, type(n)))
    # lookup in above file, if found we have an integer code
    # print 'U in: %s, Code: %s(type: %s)'% (n, Code, type(Code))
    if Code <256:
        # print 'do direct, ascii: %s, %s'% (Code, chr(Code))
        natut.playString(chr(Code))
        return
    u = chr(Code)
    # output through the clipboard with special code:
    natqh.saveClipboard()
    #win32con.CF_UNICODETEXT = 13
    natqh.setClipboard(u, format=13)
    natut.playString('{ctrl+v}')
    natqh.restoreClipboard()    
    return 1
                


def do_MSG(*args, **kw):
    """message on screen"""
    t = ', '.join(args)
    return Message(t, **kw)

def do_DOCUMENT(number=None, **kw):
    """switch to document (program specific) with number"""
##    print 'action: goto task: %s'% number
    prog, title, topchild, classname, hndle = natqh.getProgInfo()
    if not prog:
        print('action DOCUMENT, no program in foreground: %s (%S)'% (prog, title))
        return
    if number:
        try:
            count = int(number)
        except ValueError:
            print('action DOCUMENT, invalid number: %s'% number)
            return
        if not count:
            print('action DOCUMENT, invalid number: %s'% number)
            return

        section = 'positions %s'% prog
        if not ini.get(section):
            print('no mouse positions defined for DOCUMENT action in program: %s'% prog)
            return

        mouseX1 = ini.getInt(section, 'mousex1')
        mouseY1 = ini.getInt(section, 'mousey1')
        mouseXdiff = ini.getInt(section, 'mousexdiff')
        mouseYdiff = ini.getInt(section, 'mouseydiff')
        mx = mouseX1 + (count-1)*mouseXdiff
        my = mouseY1 + (count-1)*mouseYdiff
##        print 'mx, my:', mx, my
        #print 'task to %s, %s'% (mx, my)
        natqh.doMouse(0, 0, mx, my)
##        natqh.shortWait()
##        natqh.buttonClick()
    else:
        print('call action DOCUMENT with a number!')
        return
    return 1

    
def do_TASK(number=None, **kw):
    """switch to task with number"""
##    print 'action: goto task: %s'% number
    prog, title, topchild, classname, hndle = kw['progInfo']
    if prog == 'explorer' and not title:
        doKeystroke('{esc}')
        natqh.shortWait()
    if number:
        try:
            count = int(number)
        except ValueError:
            print('action TASK, invalid number: %s'% number)
            return
        if not count:
            print('action TASK, invalid number: %s'% number)
            return

        # extra to remove focus:        
        do_WINKEY("b")
        do_SW()

        mouseX1 = ini.getInt('positions', 'mousex1')
        mouseY1 = ini.getInt('positions', 'mousey1')
        mouseXdiff = ini.getInt('positions', 'mousexdiff')
        mouseYdiff = ini.getInt('positions', 'mouseydiff')
        mx = mouseX1 + (count-1)*mouseXdiff
        my = mouseY1 + (count-1)*mouseYdiff
        # print 'mx, my:', mx, my
        #print 'task to %s, %s'% (mx, my)
        natqh.doMouse(0, 0, mx, my)
        # natqh.longWait()
##        natqh.shortWait()
##        natqh.buttonClick()
    else:
        print('call action TASK with a number!')
    return 1

def do_TOCLOCK(click=None, **kw):
    """position mouse on clock, which gives taskbar menu
    """
    x = ini.get('positions', 'clockx')
    y = ini.get('positions', 'clocky')
    try:
        x = int(x) or 0
        y = int(y) or 0
    except ValueError:
        x = y = 0
    if x and y:
        natqh.doMouse(0,0,x,y,click)
        natqh.Wait()
    else:
        print('invalid mouse position for clock, do "task position clock" from grammar _general')
    return 1
 
def do_CLIPSAVE(**kw):
    """saves and empties the clipboard"""
    natqh.saveClipboard()
    return 1

def do_CLIPRESTORE(**kw):
    """saves and empties the clipboard"""
    natqh.restoreClipboard()
    return 1

def do_CLIPISNOTEMPTY(**kw):
    """returns 1 if clipboard is not empty

    should be done after a CLIPEMPTY
    restores the clipboard if 0
    """
    t = natqh.getClipboard()
    if t:
        return 1
    D('empty clipboard found, restore and return')
    natqh.restoreClipboard()
    
def do_GETCLIPBOARD(**kw):
    """returns the contents of the clipboars"""
    return natqh.getClipboard()
   
def do_COPYNAME(**kw):
    """returns the name of a file or folder if windows explorer or #32770
    """
    print('abacadabra')
    return 'abacadabra'

    
def do_IFWT(title, action, **kw):
    """unimacro shorthand command IfWindowTitleDoAction
    insert a standard wait in order to let the previous action be performed...
    """
    print('do_IFWT, %s, %s'% (title, action))
    do_W()
    return IfWindowTitleDoAction(title, action)

def IfWindowTitleDoAction(title, action, **kw):
    """do an action only if the title matches the window title
    """
    if natqh.matchTitle(title):
        # print 'title: %s, yes, action: %s'% (title, action)
        doAction(action)
    # else:
        # print 'title: %s, does not match'% title
    return 1
    
def killWindow(action1='<<windowclose>>', action2='<<killletter>>', modInfo=None, progInfo=None, comingFrom=None):
    """Closes a window and asks automatically for confirmation

    The default action 1 is "{alt+f4}",

    The default action 2 is <<killletter>>, that can be changed to
    <<saveletter>>, in order to make this a "save and close window" 
    command
 
    """
    if not progInfo:
        progInfo = natqh.getProgInfo(modInfo=modInfo)
    
    prog, title, topchild, classname, hndle = progInfo
        
    progNew = prog
    prevHandle = hndle
    doAction(action1, progInfo=progInfo, comingFrom=comingFrom)
    natqh.shortWait()
    count = 0
    while count < 20:
        count += 1
        try:
            modInfo = natlink.getCurrentModule()
            print("modinfo through natlink: %s"% repr(modInfo))
        except:
            modInfo = autohotkeyactions.getModInfo()
            print("modinfo through AHK: %s"% repr(modInfo))
        progNew = natqh.getProgName(modInfo)
            
        if progNew != prog: break
        hndle = modInfo[2]
        if hndle != prevHandle:

            if not natqh.isTopWindow(hndle):
                # child:
                print('do action2: %s'% action2)
                doAction(action2)
            elif topWindowBehavesLikeChild(modInfo):
                print('topWindowBehavesLikeChild action2: %s'% action2)
                doAction(action2)
            break
        
        natqh.shortWait()
    else:
        # no break occurred, false return:
        return 0 
    return 1

topchildDict = None
childtopDict = None

def topWindowBehavesLikeChild(modInfo):
    """return the result of the ini file dict
    
    cache the contents in topchildDict
    """
    global topchildDict
    if topchildDict is None:
        topchildDict = ini.getDict('general', 'top behaves like child')
        #print 'topchildDict: %s'% topchildDict
    if topchildDict == {}:
        return
    prog, title, topchild, classname, hndle = natqh.getProgInfo(modInfo)
    result = matchProgTitleWithDict(prog, title, topchildDict, matchPart=1)
    if result: return result
    className = win32gui.GetClassName(hndle)
    # print('className: %s'% className)
    if className in ["MozillaDialogClass"]:
        return True
            
def childWindowBehavesLikeTop(modInfo):
    """return the result of the ini file dict
    
    input: modInfo (module info: (progpath, windowTitle, hndle) )
    cache the contents in childtopDict
    """
    global childtopDict
    if childtopDict is None:
        childtopDict = ini.getDict('general', 'child behaves like top')
        #print 'childtopDict: %s'% childtopDict
    if childtopDict == {}:
        return
    prog, title, topchild, classname, hndle = natqh.getProgInfo(modInfo)
    return matchProgTitleWithDict(prog, title, childtopDict, matchPart=1)

def matchProgTitleWithDict(prog, title, Dict, matchPart=None):
    """see if prog is in dict, if so, check title with value(s)
    
    """
    if not Dict: return
    if prog in Dict:
        titles = Dict[prog]
        if type(titles) == str:
            titles = [titles]
        titles = [t.lower() for t in titles]
        title = title.strip().lower()
        if matchPart:
            for t in titles:
                if title.find(t) >= 0:
                    return 1
            return
        # matchPart = False (default)
        if title in titles:
            return 1


def do_ALERT(alert=1, **kw):
    micState = natlink.getMicState()
    if micState in ['on', 'sleeping']:
        natlink.setMicState('off')
    if alert:
        try:
            nAlert = int(alert)
        except ValueError:
            nAlert = 1
        for i in range(nAlert):
            natlink.execScript('PlaySound "'+baseDirectory+'\\ding.wav"')
    natqh.Wait(0.1)
    if micState != 'off':
        natlink.setMicState(micState)
    return 1

Alert = do_ALERT

def do_WINKEY(letter=None, **kw):
    """call the winkeys.dll with one letter
    
    if a number is taken, this number is converted into a string"""
    winkey = win32con.VK_LWIN         # 91
    keyup = win32con.KEYEVENTF_KEYUP  # 2
    win32api.keybd_event(winkey, 0, 0, 0)  # key down
    try:
        if not letter is None:
            do_SSK(letter)
    finally:
        win32api.keybd_event(winkey, 0, keyup, 0)  # key up
    return 1

    #
    #dllFile = os.path.join(natqh.getOriginalUnimacroDirectory(), "dlls", "DNSKeys.dll")
    #letter = str(letter)
    #if letter.lower() == "{tab}":
    #    letter = '\t'
    #if len(letter) != 1:
    #    print 'cannot do WINKEY with key unequal length 1: |%s|'% letter
    #    return
    #natlink.execScript('DllCall "%s","WinKey","%s"'% (dllFile,letter))

Winkey = do_WINKEY        

def do_TASKTOSCREEN(screennumber, winHndle=None, **kw):
    """call the monitorfunctions to put task to screen 0, 1, ... depending on the number of screens"""
    if winHndle is None:
        winHndle = win32gui.GetForegroundWindow()
    mon = monitorfunctions.get_nearest_monitor_window(winHndle)
    allMonitors = copy.copy(monitorfunctions.MONITOR_HNDLES)
    try:
        wantedMonitor = allMonitors[screennumber]
    except IndexError:
        print('wanted monitor: %s, allMonitors: %s'% (screennumber, allMonitors))
        return
    if wantedMonitor == mon:
        print('already on monitor %s (%s)'% (screennumber, wantedMonitor))
        return_WTC
    resize = monitorfunctions.window_can_be_resized(winHndle)
    monitorfunctions.move_to_monitor(winHndle, wantedMonitor, mon, resize)
    return 1

def do_TASKOD(winHndle=None, **kw):
    """call the monitorfunctions to put task in other display"""
    if winHndle is None:
        winHndle = win32gui.GetForegroundWindow()
    mon = monitorfunctions.get_nearest_monitor_window(winHndle)
    otherMons = monitorfunctions.get_other_monitors(mon)
    if not otherMons:
        print('only one monitor found')
        return
    otherMon = otherMons[0]
    if len(otherMons) > 1:
        print('more than 1 other monitors found (%s), take first: %s'% \
                   (otherMons, otherMon))
    resize = monitorfunctions.window_can_be_resized(winHndle)
    monitorfunctions.move_to_monitor(winHndle, otherMon, mon, resize)
    return 1

def do_TASKMAX(winHndle=None, **kw):
    """call the monitorfunctions maximize task"""
    if winHndle is None:
        winHndle = win32gui.GetForegroundWindow()
    monitorfunctions.maximize_window(winHndle)
    return 1
def do_TASKMIN(winHndle=None, **kw):
    """call the monitorfunctions to minimize task"""
    if winHndle is None:
        winHndle = win32gui.GetForegroundWindow()
    monitorfunctions.minimize_window(winHndle)
    return 1
def do_TASKRESTORE(winHndle=None, keepinside=1, **kw):
    """call the monitorfunctions to restore task, keep inside monitor by default"""
    if winHndle is None:
        winHndle = win32gui.GetForegroundWindow()
    monitorfunctions.restore_window(winHndle, keepinside=keepinside)
    return 1

TaskOtherDisplay = do_TASKOD        


# do emacs command:
def do_EMACS(*args, **kw):
    """do emacs command in minibuffer"""
    doAction("{alt+x}")
    do_W()
    for a in args:
      doAction(a)
    do_W()
    doAction("{enter}")
    do_W()
    return 1


# put quotes around text and escape quotes inside text.
def checkTextInMessage(t):
    """change " \n and \r so execScript can hndle it

    especially for the test in a MessageBoxConfirm
    """
    if t.find('"') >= 0:
        t = '""'.join(t.split('"'))
    if t.find('\n') >= 0:
        t = t.replace('\n', '"+chr$(10)+"')
    if t.find('\r') >= 0:
        t = t.replace('\r', '"+chr$(13)+"')
    return t

def stripTextInMessage(t):
    """strip " \n and \r, so execScript does not raise an error

    especially for the title in a MessageBoxConfirm
    """
    if t.find('"') >= 0:
        t = t.replace('"', '')
    if t.find('\n') >= 0:
        t = t.replace('\n', ' ')
    if t.find('\r') >= 0:
        t = t.replace('\r', ' ')
    return t


# the icons in the msgboxconfirm:
MsgboxConfirmIconDict = dict(critical=16, query=32, warning=48, information=64)

def Message(t, title=None, icon=64, alert=None, switchOnMic=None, progInfo=None, comingFrom=None):
    """put message on screen

    from grammar, call through self.DisplayMessage, only in some circumstances
    this function is called

    but can also be called directly of from shorthand command MSG
    
    switchOnMic can be True, in which case the mic is temporarily switched on
    while the message box is on.
    """
    if icon in MsgboxConfirmIconDict:
        icon = MsgboxConfirmIconDict[icon]
    if icon not in list(MsgboxConfirmIconDict.values()):
        raise ValueError("Unimacro actions Message, invalid value for icon: %s"% icon)

    if type(t) != str:
        t = '\n'.join(t)

    tt = checkTextInMessage(t)
    title = title or "Unimacro Message"
    title = stripTextInMessage(title)
    if alert:
        do_ALERT(alert)
    micState = natlink.getMicState()
    #print "Message, initial mic state: %s"% micState
    
    if switchOnMic and micState in ['sleeping', 'off']:
            natlink.setMicState('on')

    try:
        natlink.execScript('MsgBoxConfirm "%s", %s, "%s"'% (tt, icon, title))
    except SyntaxError:
        print('execScript SyntaxError\n' \
              'tt: %s\n' \
              'icon: %s\n' \
              'title: %s\n'% (tt, icon, title))
    newMicState = natlink.getMicState()
    if switchOnMic and micState != newMicState:
        natlink.setMicState(micState)
    
do_MESSAGE = do_MSG

def YesNo(t, title=None, icon=32, alert=None, defaultToSecondButton=0, progInfo=None, comingFrom=None):
    """put message on screen, ask for yes or no

    if yes return True    

    but can also be called directly of from shorthand command YESNO

    the microphone is switched on if not so already. After the test (execScript)
    it should be "on" when No was answered (return False)
    and "sleeping" when Yes was answered (return True)
    
    if the microphone is "off" after the execScript, the user probably switched it
    off, and a special 0 is returned.
    
    Note: the execScript is an old dvc script, with limited possibilities!
    """
    if icon in MsgboxConfirmIconDict:
        icon = MsgboxConfirmIconDict[icon]
    if icon not in list(MsgboxConfirmIconDict.values()):
        raise ValueError("Unimacro actions Message, invalid value for icon: %s"% icon)

    if type(t) != str:
        t = '\n'.join(t)
    tt = checkTextInMessage(t)
    title = title or "Unimacro Question"
    title = stripTextInMessage(title)

    if icon in MsgboxConfirmIconDict:
        icon = MsgboxConfirmIconDict[icon]
    if icon not in list(MsgboxConfirmIconDict.values()):
        raise ValueError("Unimacro actions YesNo, invalid value for icon: %s"% icon)
    icon += 4 # yes no button
    if defaultToSecondButton:
        icon += 256

    micState = natlink.getMicState()
    #print "YesNo, initial mic state: %s"% micState

    if alert:
        do_ALERT(alert)

    if micState != 'on':
        natqh.Wait(0.05)
        natlink.setMicState('on')
    newMicState = natlink.getMicState()
    natqh.Wait(0.1)
    ttt = tt
    for i in range(3):
        try:
            cmd = 'MsgBoxConfirm "%s", %s, "%s"\n\nSetMicrophone 1\nGoToSleep'% (ttt, icon, title)
            #print 'cmd: %s'% cmd
            natlink.execScript(cmd)
        except natlink.SyntaxError:
            print('execScript SyntaxError\n' \
                  'tt: %s\n' \
                  'icon: %s\n' \
                  'title: %s\n'% (tt, icon, title))
        natqh.Wait(0.1)
        newMicState = natlink.getMicState()
        result = (newMicState == 'sleeping')
        if newMicState != 'off': break   # ok, either on or sleeping
        # try again (maximum 3 times)
        natqh.Wait(0.05)
        natlink.setMicState('on')
        ttt = checkTextInMessage("Please do not switch off the microphone\nwhile (re)answering the question:\n\n")+tt
    else:
        raise UserWarning("microphone should not be switched off while answering the YesNo question\n(and you got 3 chances to answer correct)")
    if micState != newMicState:
        natlink.setMicState(micState)
        natqh.Wait(0.05)
    return result


do_YESNO = YesNo

cursorText = '#<CURSOR'

##QH13062003  cursor positioning and other switch things for voicecoder--------------
def putCursor():
    """just put cursor text at cursor or after selection"""
    doAction("{end}%s"% cursorText)
    

def findCursor():
    """find the previous entered cursor text"""
    doAction('<<startsearch>>; "%s"; VW; <<searchgo>>'% cursorText)
    prog, title, topchild, classname, hndle = natqh.getProgInfo()
    if prog == 'emacs':
        doAction("{shift+left %s}"% len(cursorText))
    doAction("CLIPSAVE; <<cut>>")
    t = natqh.getClipboard()
    if t == cursorText:
        doAction("CLIPRESTORE")
        return 1
    else:
        print('invalid clipboard: %s'% t)
        doAction("<<paste>>; CLIPRESTORE")


bringups = {}
# special:
voicecodeApp = 'emacs'

def UnimacroBringUp(app, filepath=None, title=None, extra=None, modInfo=None, progInfo=None, comingFrom=None):
    """get a running copy of app in the foreground

    the full path can be set in section [bringup app], key path
    the appname can also be set in this section, key appname
    
    if filepath == None:
        if appname is in the foreground, no switching needs to be done.
        if app is called for, waiting is until app is in the foreground.
    
    if filepath points to a valid file, this is added to appArgs.
    
    special cases for app:
        open: look in [bringup open] section for application extension, if not found,
                just open (with app set to None)
        edit: look in [bringup edit] section for application extension, if not found,
              take default edit program from edit section.
              
    if class or title is given, first attaching to a running instance is tried.
    """
    global bringups
    if checkForChanges:
        doCheckForChanges() # resetting the ini file if changes were made

    # intermediate app and special treatment:
    # for voicecode (which you can call with BRINGUP voicecode) you need
    # voicecodeApp ('emacs') and (optional, but in this case) function voicecodeBringUp
    #
    if filepath:
        app2 = None
        while app in ['open', 'edit']:
            if app == app2: break   #open = open...
            dummy, ext = os.path.splitext(filepath)
            section = 'bringup %s'% app
            ext = ext.strip('.')
            app2 = ini.get(section, ext)
            if app2:
                app = app2
            else:
                app = None
    else:
        if debug: D('starting UnimacroBringUp for app: %s'% app)
        specialApp = app + 'App'
        specialFunc = app + 'BringUp'
        if specialApp in globals() or specialFunc in globals():
            if specialApp in globals():
                appS = globals()[specialApp]
        ##        print 'do special: %s'% appS
                if not UnimacroBringUp(appS):
                    D('could not bringup: %s'% appS)
                    return
            if specialFunc in globals():
                func = globals()[specialFunc]
        ##                print 'func: %s (%s)'% (specialFunc, func)
                if type(func) != types.FunctionType:
                    raise UnimacroError("UnimacroBringUp, not a proper function: %s (%s)"% (specialFunc, func))
                return func()
        
    # now the "normal" cases:
    # get possibly different name and path from inifile:

    if app:
        appName = ini.get("bringup %s"% app, "name") or app
        appPath = ini.get("bringup %s"% app, "path") or None

        if appPath:
            #print 'appPath: %s'% appPath
            if os.path.isfile(appPath):
                appPath = os.path.normpath(appPath)
            else:
                appPath2 = natlinkcorefunctions.expandEnvVariableAtStart(appPath)
                if os.path.isfile(appPath2):
                    appPath = os.path.normpath(appPath2)
                elif appPath.lower().startswith("%programfiles%"):
                    appPathVariant = appPath.lower().replace("%programfiles", "%PROGRAMW6432%")
                    appPath2 = natlinkcorefunctions.expandEnvVariableAtStart(appPath)
                    if os.path.isfile(appPath2):
                        appPath = os.path.normpath(appPath2)
                    elif os.path.isdir(appPath2):
                        appPath = os.path.join(appPath2, appName)
                        if os.path.isfile(appPath):
                            appPath = os.path.normpath(appPath)
                        else:
                            raise IOError('invalid path for PROGRAMFILES to PROGRAMW6432, app %s: %s (expanded: %s)'% (app, appPath, appPath2))
                    else:
                        raise IOError('invalid path for app with PROGRAMFILES %s: %s (expanded: %s)'% (app, appPath, appPath2))
                else:
                    raise IOError('invalid path for  app %s: %s (expanded: %s)'% (app, appPath, appPath2))
        else:
            appPath = appName or app
        appArgs = ini.get("bringup %s"% app, "args") or None
    else:
        appPath = None
        appArgs = None
        appName = None
    if appName:
        if filepath:
            appName = appName + " " + filepath
    else:
        appName = filepath

    if filepath:
        filepath = '""'+filepath+'""'
        if appArgs:
            #if filepath.find(" ") > 0:
                # insert DOUBLE DOUBLE QUOTES for vba line recognition
            filepath = '""'+filepath+'""'
            appArgs = appArgs + " " + filepath
        else:
            appArgs = filepath
    # for future:
    appWindowStyle = ini.get("bringup %s"% app, "style") or None
    appDirectory = ini.get("bringup %s"% app, "directory") or None
    
    if not filepath:
        # for attaching to a running instance:
        appTitle = ini.get("bringup %s"% app, "title") or None
        appClass = ini.get("bringup %s"% app, "class") or None
        ## TODOQH
        prog, title, topchild, classname, hndle = natqh.getProgInfo()
        progFull, titleFull, hndle = natlink.getCurrentModule()
    
        if windowCorrespondsToApp(app, appName, prog, title):
            if debug > 1: D('already in this app: %s'% app)
            if app not in bringups:
                bringups[app] = (prog, title, hndle)
            return 1
    
        if app in bringups:
            # try to simply switchto previous:
            try:
                do_RW()
                hndle = bringups[app][2]
                if debug: D('hndle to switch to: %s'% hndle)
                if not natqh.SetForegroundWindow(hndle):
                    print('could not bring to foreground: %s, exit action'% hndle)
                    
                if do_WTC():
                    prog, title, topchild, classname, hndle = natqh.getProgInfo()
                    if prog == appName:
                        return 1
            except:
                if debug: D('error in switching to previous app: %s'% app)
                if debug > 2: D('bringups: %s'% bringups)
                if debug: D('delete %s from bringups'% app)
                del bringups[app]
                
    #    do_RW()
    #    if app in ('voicecode', 'dragonpad'):
    #        raise UnimacroError("Oops, BRINGUP voicecoder should not come here at all, bringing up: %s"% app)
    #    #print 'appTitle: %s, appClass: %s'% (appTitle, appClass)
    #    if appTitle or appClass:
    #        hndle = messagefunctions.findTopWindow(wantedClass=appClass, wantedText=appTitle)
    #        if hndle:
    #            if not natqh.SetForegroundWindow(hndle):
    #                print 'get window %s to foreground failed'% hndle
    #                
    #            natqh.Wait(0.1)
    #            prog, title, topchild, classname, hndle = natqh.getProgInfo()
    #            progFull, titleFull, hndle2 = natlink.getCurrentModule()
    #            if hndle == hndle2:
    #                #print 'OK, setting |%s|, currentModule: %s'% (app, repr(natlink.getCurrentModule()))
    #                bringups[app] = (prog, title, hndle)
    #                return 1
    #            else:
    #                print 'did not bring to foreground: %s (hndle: %s, hndle2: %s (current foreground: %s)'% (app, hndle, hndle2, prog)
    #                #print 'currentModedule: %s'% repr(natlink.getCurrentModule())
    ##do_RW()
    #print 'unimacrobringup: name: %s, app: %s, args: %s (filepath: %s)'% (appName, appPath, appArgs, filepath)
    result = natqh.AppBringUp(appName, appPath, appArgs, appWindowStyle, appDirectory)
    # print("result of UnimacroBringUp:", result)
    if extra:
        doAction(extra)
        
    return result
#    if do_WTC():
#        prog, title, topchild, classname, hndle = natqh.getProgInfo()
#        progFull, titleFull, hndle = natlink.getCurrentModule()
###        print 'app: %s, appName: %s, got prog: %s'% (app, appName, prog)
#        if prog == appName:
#            bringups[app] = (prog, title, hndle)
#            if app == 'voicecode':
#                return UnimacroBringupVoiceCode()
#            return 1
#    # something went wrong:
#    if app in bringups:
#        del bringups[app]       
#        if debug: D('fail to bringup %s, current appName: %s, path asked for: %s\n'
#                    'now in window %s, title %s, hndle: %s'%
#                    (app, appName, appPath, prog, title, hndle))
#    # else fail, return None

def AutoHotkeyBringUp(app, filepath=None, title=None, extra=None, modInfo=None, progInfo=None):
    """start a program, folder, file, with AutoHotkey
    
    This functions is related to UnimacroBringup, which works with AppBringup from Dragon,
    but sometimes fails.
    
    Besides, this function can also work without Dragon being on, not relying on natlink.
    So better fit for debugging purposes.
    
    """
    scriptFolder = autohotkeyactions.GetAhkScriptFolder()
    if not os.path.isdir(scriptFolder):
        raise IOError('no scriptfolder for AHK: %s'%s)
    WinInfoFile = os.path.join(scriptFolder, "WININFOfromAHK.txt")
    
    ## treat mode = open or edit, finding a app in actions.ini:
    if ((app and app.lower() == "winword") or
        (filepath and (filepath.endswith(".docx") or filepath.endswith('.doc')))):
        script = autohotkeyactions.GetRunWinwordScript(filepath, WinInfoFile)
        result = autohotkeyactions.do_ahk_script(script)

    elif app and title:
        ## start eg thunderbird.exe this way
        ## can also give additional startup instructions in extra
        extra = extra or ""
        script = '''SetTitleMatchMode, 2
Process, Exist, ##basename##
if !ErrorLevel = 0
{
IfWinNotActive, ##title##,
WinActivate, ##title##, 
WinWaitActive, ##title##,,1
if ErrorLevel {
    return
}
}
else
{
Run, ##app##
WinWait, ##title##,,5
if ErrorLevel {
    MsgBox, AutoHotkey, WinWait for running ##basename## timed out
    return
}
}
##extra##
WinGet pPath, ProcessPath, A
WinGetTitle, Title, A
WinGet wHndle, ID, A
FileDelete, ##WININFOfile##
FileAppend, %pPath%`n, ##WININFOfile##
FileAppend, %Title%`n, ##WININFOfile##
FileAppend, %wHndle%, ##WININFOfile##

'''
        basename = os.path.basename(app)
        script = script.replace('##extra##', extra)
        script = script.replace('##app##', app)
        script = script.replace('##basename##', basename)
        script = script.replace('##title##', title)
        script = script.replace('##WININFOfile##', WinInfoFile)
        result = autohotkeyactions.do_ahk_script(script)
            
    else:
        ## other programs:
        if app and filepath:
            script = ["Run, %s, %s,,NewPID"% (app, filepath)]
        elif filepath:
            script = ["Run, %s,,, NewPID"% filepath]
        elif app:
            script = ["Run, %s,,, NewPID"% app]
    
        script.append("WinWait, ahk_pid %NewPID%")
    
        script.append("WinGet, pPath, ProcessPath, ahk_pid %NewPID%")
        script.append("WinGetTitle, Title, A")  ##, ID, ahk_pid %NewPID%")
        script.append("WinGet, wHndle, ID, ahk_pid %NewPID%")
        script.append('FileDelete, ' + WinInfoFile)
        script.append('FileAppend, %pPath%`n, ' + WinInfoFile)
        script.append('FileAppend, %Title%`n, ' + WinInfoFile)
        script.append('FileAppend, %wHndle%, ' + WinInfoFile)
        script = '\n'.join(script)

        result = autohotkeyactions.do_ahk_script(script)

    ## collect the wHndle:
    if result == 1:
        winInfo = open(WinInfoFile, 'r').read().split('\n')
        if len(winInfo) == 3:
            # make hndle decimal number:
            pPath, wTitle, hndle = winInfo
            hndle = int(hndle, 16)
            print('extracted pPath: %s, wTitle: %s and hndle: %s'% (pPath, wTitle, hndle))
            return pPath, wTitle, hndle
        else:
            if natlink.isNatSpeakRunning():
                mess = "Result of ahk_script should be a 3 item list (pPath, wTitle, hndle), not: %s"% repr(winInfo)
                do_MSG(str(mess))
            print(str())
            return 0
    else:
        if natlink.isNatSpeakRunning():
            do_MSG(str(result))
        print(str(result))
        return 0


## was:

def getAppPath(app):
    """use from openFileDefault, get path of application or None
    """
    appPath = ini.get("bringup %s"% app, "path") or None
    return appPath

def getAppName(app):
    """use from openFileDefault, get name of application or None (mainly for edit)
    """
    appName = ini.get("bringup %s"% app, "name") or None
    return appName

def getAppForEditExt(ext):
    """use from openFileDefault, when choosing "edit", check with extension
    """
    section = "bringup edit"
    ext = ext.strip('.')
    appName = ini.get(section, ext) or ini.get(section, 'name')
    return appName
    

def dragonpadBringUp():
    i = 0
    natlink.recognitionMimic(["Start", "DragonPad"])
    sleepTime = 0.3
    waitSteps = 10
    while i < waitSteps:
        i += 1
        prog, title, topchild, classname, hndle = natqh.getProgInfo()
        if windowCorrespondsToApp('dragonpad', 'natspeak', prog, title):
            break
        do_W(sleepTime)
        if i > waitSteps/2:
            print('try to check for DP: %s (%s)'% (prog, i))
    else:
        print('could not bringup DragonPad after %s seconds'% sleepTime*waitSteps)
        return
    return 1
        
def messagesBringUp():
    """switch to the messages from python macros window"""
    if autohotkeyactions.ahk_is_active():
        do_AHK("showmessageswindow.ahk")
        return 1
    
    if natqh.switchToWindowWithTitle('Messages from python macros'):
        return 1
    if not natqh.switchToWindowWithTitle('Messages from python macros'):
        raise UnimacroError("cannot bring messages window to front")
    return 1


def voicecodeBringUp():
    """assume emacs is in front, check the other necessary things"""
    if debug: D('starting special: voicecodeBringUp')

    prog, title, topchild, classname, hndle = natqh.getProgInfo()
    if prog != voicecodeApp:
        if not UnimacroBringUp(voicecodeApp):
            D('did not bringup voicecodeApp: %s'% voicecodeApp)
            return
    if startVoiceCoder():
        return checkUser('VoiceCode')
    if not startMediator():
        print('could not bringup Mediator in cmd window, but try again to start voicecoder in emacs')
    # could be left in another app, so:
    if not UnimacroBringUp('emacs'):
        print('could not bringup emacs after starting the Mediator window')
        return
    if not startVoiceCoder():
        print('could not start voicecoder in emacs window')
        return
    # check user:
    return checkUser('VoiceCode')

def checkUser(userWanted):
    """open the correct user profile if needed"""
    if debug: D('checking user, should be or become %s'% userWanted)
    user, dummy = natlink.getCurrentUser()
    if user == userWanted:
        if debug: D('user OK: %s'% user)
        return 1
    # save old user and change to new:
    if debug: D('switch from %s to user %s'% (user, userWanted))
    natlink.saveUser()
    natlink.openUser(userWanted)
    user, dummy = natlink.getCurrentUser()
    if user == userWanted:
        if debug: D('switched to correct user %s'% user)
        return 1
    if debug: D('could not switch to user %s (now: %s)'% (userWanted, user))
    
def startVoiceCoder(nTrie=2):
    """if in emacs window, try to start the voicecoder window

    identified by "(yak" (case insensitive)
    """
    prog, title, topchild, classname, hndle = natqh.getProgInfo()
    if prog != voicecodeApp:
        print('startVoiceCoder needs correct app first: %s, not: %s'% (voicecodeApp, prog))
        return
    if title.find("(yak ") >= 0:
        if debug: D('found voicecoder right away')
        return 1
    i = 0
    while i < nTrie:
        if debug: D('Try to get vcode-mode: %s'% i)
        doAction("EMACS vcode-mode")
        do_W(0.5)
        prog, title, topchild, classname, hndle = natqh.getProgInfo()
        if title.find("(yak ") >= 0:
            if debug: D('found voicecoder')
            return 1
        i += 1
    if debug: D('NOT found voicecoder')
    
def startMediator():
    """start the mediator  for voicecoder"""
    natlink.setMicState("off")
    if not UnimacroBringUp("cmd"):
        print('could not BringUp "cmd"')
        return
    vcode_home = os.environ["VCODE_HOME"]
    if debug > 2: D('vcode_home: %s'% vcode_home)
    doKeystroke("%s{enter}"% vcode_home[:2])
    do_W(1)
    doKeystroke("cd %s{enter}"% os.path.join(vcode_home, 'mediator'))
    do_W(1)
    pythonExe = os.path.join(sys.prefix, "python.exe")
    doKeystroke("%s wxmediator.py{enter}"% pythonExe)
    if do_WWT("VoiceCode", 45,1):
        return 1


def windowCorrespondsToApp(app, appName, actualProg, actualTitle):
    """program, plus possibly title corresponds, so in correct window
    

    """
    if app == 'dragonpad':
        return (appName == actualProg and actualTitle.startswith("DragonPad"))
    else:
        return appName == actualProg
    

def clearBringups():
    global bringups
    bringups.clear()

do_CLEARBRINGUPS = clearBringups
do_BRINGUP = UnimacroBringUp      


def getPathOfOpenFile():
    """extract, in some way, the path and filename of the foreground file


    used for switching from eg pythonwin to emacs and back
    """
    fileName = None
    prog, title, topchild, classname, hndle = natqh.getProgInfo()
    if prog == 'pythonwin':
        doKeystroke("{ctrl+r}")
        doAction("W")
        natqh.saveClipboard()
        doKeystroke("{ctrl+c}{esc}")
        fileName = natqh.getClipboard()
        natqh.restoreClipboard()
        return fileName
    elif prog == 'emacs':
        # get from voicecode window title the filename part:
        if title.find("-- (yak") > 0:
            fileName = title.split("--")[0].strip()
        else:
            return
        # get from minibuffer the folder name:
        doKeystroke("{ctrl+x}{ctrl+w}")
        natqh.saveClipboard()
        doKeystroke("{shift+exthome}{alt+w}")
        doKeystroke("{ctrl+g}")
        folder = natqh.getClipboard()
        fileName = os.path.join(natqh.getClipboard(), fileName)
        natqh.restoreClipboard()
        return fileName
    elif prog == 'uedit32':
        # get from window title bar:
        if title.find("[") > 0:
            fileName = title.split("[")[-1]
            fileName = fileName.split("]")[0]
            return fileName
    elif prog == 'pythonw':
        # get from window title bar:
        # assume program is IDLE
        if title.find("-") > 0:
            fileName = title.split("-")[-1]
            fileName = fileName.strip('* ')
            return fileName
    if fileName:
        if os.path.isfile(fileName):
            return fileName
        else:
            print('not a valid fileName: %s'% fileName)
    else:
        print('no filename found for program: %s'% prog)

if debug:
    try:
        debugSock = open(debugFile, 'w')
    except IOError:
        print('_actions, IOError, cannot write debug statements to: %s'% debugFile)
else:
    try:
        os.remove(debugFile)
    except OSError:
        pass

if __name__ == '__main__':
    # s = 551345646373737373
    do_SCLIP(s)
    # UnimacroBringUp("edit", r"C:\NatlinkGIT3\Unimacro\_lines.py")
    
    