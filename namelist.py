"""Read file with names (address book) and make nice list
for import in naturally speaking

testfile in unittest\namelist, some doctests in this file

possibilities for spoken forms, but not extensively elaborated.
the spoken forms for "-" seem to be not needed anymore.

Can be run from inputoutput.py (function namelist) or unimacro (function namelistUnimacro) 

"""
import os, os.path, pprint, string, re
try:
    set
except AttributeError:
    from sets import Set as set
from utilsqh import path

# complete words that need a spoken form:
needsSpokenForm = {}
needsSpokenForm['kcs'] = 'kasee es'
needsSpokenForm['ksc'] = 'ka essee'
needsSpokenForm['ict'] = 'isee thee'
needsSpokenForm['rhd'] = 'er hadee'
needsSpokenForm['mwn'] = 'emwee en'
needsSpokenForm['mwu'] = 'emwee u'
needsSpokenForm['kb'] = 'kabee'
needsSpokenForm['bv'] = 'beevee'
needsSpokenForm["'t"] = "ut"

# parts of words that need a spoken form (combine in future with regularFormsDetails:
##spokenFormDetails = {}
##spokenFormDetails[chr(246) + "h"] = 'eu' # o umlaut + h
##spokenFormDetails[chr(246)] = 'u' # o umlaut
##spokenFormDetails["eij"] = 'ei'

# regular expressions that need spoken form:
regularForm = {}
regularExpr = {}
regularForm[r'sche$'] = 'se'
regularForm[r'^cha'] = 'sja'

# words that should not be capitalized, unless in the beginning of the name:
inBetweenWords = ['de', 'van']

def namelist(inputfile, outputfile):
    """Check filenames from input string end write good results to output

    "-" and spaces ok,

    ignore words with "_" or starting with number

    """
    firstNames = set()
    secondNames = set()
    fullNames = set()
    voornamenList = ['jan']
    for line in open(inputfile):
        tt = cleanLine(line)
        if not tt: continue
        tt = tt.split()
        firstName = ""
        secondName = ""
        if len(tt) < 1:
            continue
        elif len(tt) == 1:
            secondName = tt
        elif len(tt) == 2:
            firstName = tt[:1]
            secondName = tt[1:]
        elif tt[1] in voornamenList:
            # len(tt) > 2
            firstName = tt[:2]
            secondName = tt[2:]
            #print 'voor  first:', firstName
            #print 'voor second:', secondName
        else:
            firstName = tt[:1]
            secondName = tt[1:]
            #print 'achter first:', firstName
            #print 'achtersecond:', secondName
        if firstName:
            firstName = WrittenSpoken(' '.join(firstName))
            firstNames.add(str(firstName))
        if secondName:
            secondName = WrittenSpoken(' '.join(secondName)) 
            secondNames.add(str(secondName))
        if firstName and secondName:
            fullName = firstName + secondName
            fullNames.add(str(fullName))
    total = filter(None, list(fullNames | firstNames | secondNames))
    total.sort()
    outFile = open(outputfile, 'w').write('\n'.join(total))

def namelistUnimacro(inputstring, ini=None):
    """Take a string as input, and get the several words lists as language dependent.

    Output a list of words.

    "-" and spaces ok,

    ignore words with "_" or starting with number

    """
    voornamenList = []
    inbetweenwords = []
    spokenForms = {}
    regularForms = {}
    result = []
    if ini:
        voornamenList =ini.getList("name phrase", "secondchristiannames") or []
        inbetweenwords = ini.getList("name phrase", "inbetweenwords") or []
        spokenFormKeys = ini.get("spoken forms")
        for k in spokenForms:
            spokenForms[k] = ini.get("spoken forms", k)
##        regularFormKeys = ini.get("regular forms")
##        for k in regularFormKeys:
##            regularForms[k] = ini.get("regular forms", k)
    
    tt = cleanLine(inputstring)
    if not tt: return 
    tt = tt.split()
    firstName = ""
    secondName = ""
    if len(tt) < 1:
        return 
    elif len(tt) == 1:
        secondName = tt
    elif len(tt) == 2:
        firstName = tt[:1]
        secondName = tt[1:]
    elif tt[1] in voornamenList:
        # len(tt) > 2
        firstName = tt[:2]
        secondName = tt[2:]
        #print 'voor  first:', firstName
        #print 'voor second:', secondName
    else:
        firstName = tt[:1]
        secondName = tt[1:]
        #print 'achter first:', firstName
        #print 'achtersecond:', secondName
    if firstName:
        firstName = WrittenSpoken(' '.join(firstName),
                                  spokenForms=spokenForms, regularForms=regularForms,
                                  inbetweenWords=inbetweenwords)
        result.append(str(firstName))
        
    if secondName:
        secondName = WrittenSpoken(' '.join(secondName),
                                   spokenForms=spokenForms, regularForms=regularForms,
                                   inbetweenWords=inbetweenwords) 
        result.append(str(secondName))
    if firstName and secondName:
        fullName = firstName + secondName
        result.append(str(fullName))
    return result


class WrittenSpoken(object):
    """Analyse the written\spoken for input

!!Note the doubling of backslashes, due to doctest functioning!    

Called with function above the needsSpokenForm and regularForm dicts as in this
file (for Dutch) are taken. From unimacro provide two dicts:
1. needsSpokenForms for words (abbrevs) that are translated completely
2. regularForms for patterns that are substituted (longest first)

FirstNames:
    
>>> str(WrittenSpoken("Dick"))
'Dick'
>>> str(WrittenSpoken("jan kees"))
'Jan Kees'
>>> str(WrittenSpoken("Jan-kees"))
'Jan-Kees'
>>> str(WrittenSpoken("Charaf-Marie"))
'Charaf-Marie\\\\sjaraf marie'

secondNames:
>>> str(WrittenSpoken("Jansen"))
'Jansen'
>>> str(WrittenSpoken("van Dijk-de Pater"))
'Van Dijk-de Pater'
>>> str(WrittenSpoken("van Dijk-De Graaf"))
'Van Dijk-De Graaf'

combinations:

>>> str(WrittenSpoken("Charaf de Graaf"))
'Charaf de Graaf\\\\sjaraf de graaf'

>>> str((WrittenSpoken("Charaf") + WrittenSpoken("de Leidsche")))
'Charaf de Leidsche\\\\sjaraf de leidse'

>>> str((WrittenSpoken("Kees") + WrittenSpoken("de Leidscher")))
'Kees de Leidscher'


    
    """

    def __init__(self, input, spokenForms=None, regularForms=None, inbetweenWords=None):
        self.needsSpokenForm = spokenForms or needsSpokenForm
        self.regularForm = regularForms or regularForm
        self.inbetweenWords = inbetweenWords or inBetweenWords  # from formal parms or global (Dutch)
##        print 'inbetweenWords: %s'% self.inbetweenWords
##        print 'needsSpokenForm: %s'% self.needsSpokenForm
##        print 'regularForm: %s'% self.regularForm
        
        if isinstance(input, WrittenSpoken):
            input = str(input)
        if input.find('\\') > 0:
            self.written =  input.split('\\')[0]
            self.spoken =  input.split('\\')[ - 1]
        elif input.find('-') > 0:
            parts = input.split('-')
            results = map(WrittenSpoken, parts)
            written = [r.written for r in results]
            spoken = [r.spoken for r in results]
            self.written = '-'.join(written)
            self.spoken = ' '.join(spoken)
        elif input.find(' ') > 0:
            parts = input.split(' ')
            results = map(WrittenSpoken, parts)
            written = [r.written for r in results]
            spoken = [r.spoken for r in results]
            self.written = ' '.join(written)
            self.spoken = ' '.join(spoken)
        else:
            # capitalize NOT if in inbetweenWords:
            if input in self.inbetweenWords:
                self.written = input
            else:
                self.written = input.capitalize()
            self.spoken = self.getSpokenForm(input)
            
            if input.lower() in needsSpokenForm:
                self.spoken = needsSpokenForm[input.lower()]

    def __add__(self, other):
        new = WrittenSpoken(self)
        if not isinstance(other, WrittenSpoken):
            other = WrittenSpoken(other)
        new.written += ' ' + other.written
        new.spoken += ' ' + other.spoken
        return new
    

    def __str__(self):
        """note "-" is not regarded as reason for spoken form anymore!

        """
        writtenClean = self.written.lower().replace('-', ' ')
        spokenClean = self.spoken.lower()
        if writtenClean == spokenClean:
            result = self.written
        else:
            result = self.written  + '\\' + self.spoken
        if result[0] in unicode(string.lowercase):
            result = result[0].capitalize() + result[1:]
        return result

    def getSpokenForm(self, word):
        """should be a single word"""
        word = word.lower()
        # first the list of needsSpokenForm:
        if word in self.needsSpokenForm:
            return self.needsSpokenForm[word]
        decorated = [( - len(k), k) for k in self.regularForm]
        decorated.sort()
        regularFormKeys = [k for (dummy, k) in decorated]
        for k in regularFormKeys:
            if re.search(k, word):
                word = re.sub(k, self.regularForm[k], word)
                
        return word
    
              
def cleanLine(line):
    """Cleanout unwanted things, like " - " (must be "-")

    when line contains _ or starts with number return None, meaning a false entry

    """
    if line.find('-'):
        line = line.replace("- ", "-")
        line = line.replace(" -", "-")

    if line.find("_") >= 0:
        return
    if line[0] in unicode(string.digits):
        return
    return line


def runPanel(frame, notebook):
    """add functions to controlpanel"""
    print 'starting cp %s'% __name__
    from controlpanel import ControlPanel
    cp = ControlPanel(notebook, frame, -1, __name__)
    cp.addFunction(namelist, 'inputfile, outputfile')
    cp.addDefaults()
    print 'started cp %s'% __name__
    return cp

def _test():
    import doctest, namelist
    reload(namelist)
    doctest.master = None
    return  doctest.testmod(namelist, verbose=0)

def _testrun():
    # need files on computer QH for this, sorry...
    dir = path('d:/projects/unittest/namelist')
    infile = dir/'names input.txt'
    outfile = dir/'names output.txt'
    namelist(infile, outfile)

if __name__ == "__main__":
    _test()
    _testrun()
