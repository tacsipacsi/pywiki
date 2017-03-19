# -*- coding: utf-8 -*-
"""
This bot tries to gather relevant articles for the anniversaries on main page.
In Hungarian Wikipedia anniversaries are grouped by 5 years, so we have to
search for years with ending 0 or 5, 1 or 6 etc. But you may search for every
year as well.
(C)(D)(E)(F)(G)(A)(H)(C) Bináris
v0.8, 2014. január 12. Works with one date wired in main().
v1.0, 2014. január 15. 
    Supports "all year" lookups besides round anniversaries.
    Has some sample wrappers and commandline parameters.
    Default behaviour changed: existing target pages will be skipped (primarily
    for sparing time, not for protecting data); overwrite must be forced.
Tested in trunk (compat) branch of PWB.

ato, 2015. 06. 13.
Migrated to pywikibot core.

ato, 2015. 09. 12.
Exceptions are extendend to make it faster.

Bináris, 2016. 09. 12.
Using locale, simplified exceptions

Tacsipacsi, 2017. 03. 19.
Migrate to Python 3

KNOWN PARAMETERS
nextmonth:  takes the next month from calendar, and goes through every day
            ("every year" mode)
nextmonth5: as nextmonth, but searches for round anniversaries
            (elapsed time should be divisible by 5)
In lack of parameters the bot will work with data wired in main().
-noskip:    forces the bot to reprocess existing target pages (see above).
 
HELP FOR LOCALIZATION
This script is developed for Hungarian Wikipedia.
If you want to port this script to another Wikipedia, you should modify:
global stopsections
global infobox (if there is no such word, your task may be hard, eat chocolate)
global basepage -- where to save
global header
dailybot.yearregex, dateregex, dateregexwithyear (__init__)
dailybot.categories()
dailybot.createpage()
This requires a basic knowledge of regular expressions.
Remove the line "from binbotutils import levelez" below and any lines
containing "levelez", "hiba" or "fatal" (these serve my own needs).
When publishing the modified script, don't remove this help text and link
your script to hu:user:BinBot/anniversary.py as original.
See also [[hu:User:BinBot/anniversary.py/doc]].
 
Structure:
  dailybot processes one given day (with given year endings, if applicable).
  callbot validates the parameters for one day and calls dailybot.
  Any further frame may be written to call callbot in loop.
  There are some at the end for sample.
"""
'''
TODO
    Removal of cite* templates from main text
    Extraction of birth and death dates from introduction
    Some more wrappers and commandline parameters
    Completely new functionalities to read and write Wikidata?
'''

import re, datetime, locale
import pywikibot
from pywikibot import pagegenerators, date
from pywikibot.bot import SingleSiteBot
locale.setlocale(locale.LC_ALL, '')

# from binbotutils import levelez # Remove if you are not me
 
# List of usual section titles at the end of the article such as sources, where
# the bot will stop searching. Dates beyond this point are irrelevant.
# The bot will skip the trailng part from the first match of these.
stopsections = [
    'Külső hivatkozások',
    'Források',
    'Jegyzetek',
    'Lásd még',
    'Kapcsolódó szócikkek',
    'További információk',
]
stopsectionregex = re.compile(r'== *(%s) *==' % '|'.join(stopsections))
# A word that occurs in the name of infobox templates:
infobox = 'infobox'
# A page under which the subpages will be saved:
basepage = 'Wikipédia:Évfordulók kincsestára'
# Excepted articles (a list of compiled regexes)
# I except month names and dates
# and years as well as they are processed separately, just as list of asteroids.
# Will be searched, not matched! So mark ^ and $ if neccessary.
exceptions = [
    re.compile(r'^(%s)( \d{1,2}\.)?$' % '|'.join(date.makeMonthNamedList('hu', r'%s', makeUpperCase=True))),
    re.compile(r'^(I. e. )?\d+$'),
    re.compile(r' (keresztnév)$'),
    re.compile(r'listája$'),
]
# A header for the result pages
header = '''\
<!-- A lapot bot frissíti. Ha változtatás szükséges, jelezd Binárisnak! -->
{{tudnivalók eleje}}
Ez a lap a napi évfordulósablon elkészítéséhez nyújt segítséget. <br />
Itt van egy leírás, hogyan készült: [[Szerkesztő:BinBot/anniversary.py/doc]].
{{tudnivalók vége}}
Utolsó módosítás: ~~~~~

'''
# --*-- End of global stuff to be localized. Go to dailybot to continue. --*--
# Section titles (second level is enough for us):
sectionpattern = re.compile(r'^==[^=].*?==')
references =  re.compile(r'(?ism)<ref[ >].*?</ref>')
HTMLcomments = re.compile(r'(?s)<!--.*?-->')
TEMP_REGEX = re.compile(
    '(?sm){{(?:msg:)?(?P<name>[^{\|]+?)(?:\|(?P<params>[^{]+?(?:{[^{]+?}[^{]*?)?))?}}')
# The above 3 regexes are copied from textlib.py. TEMP_REGEX is far not perfect
# for nested templates but currently the best known effort.

class DailyBot(SingleSiteBot):
    def __init__(self, month, day, yearmodulo5=None, overwrite=False):
        """Constructor.
        
        Parameters:
        month, day: a day of year as integers (e.g. 12 and 6); compulsory
        yearmodulo5: integer between 0 and 4, see the preface; optional
            If given, the bot will search for years that have the given
            remainder modulo5 (e.g. yearmodulo5=3 => we search for years
            with ending 3 and 8. If None, all the years are valid results.
        overwrite: if True, existence of the result page won't be checked,
            rather the target will be ruined and built again (defaults to False).
        """
        super(DailyBot, self).__init__()
        self.month = month
        self.day = day
        self.year5 = yearmodulo5
        self.overwrite = overwrite
        # This dictionary will contain the roles where the date is found.
        # Currently birth, death, infobox and other, and articles of years.
        # Each list contains dictionaries with 'page', 'year' and 'text'.
        # 'year' is the sortkey and is not directly output.
        self.data = dict()
        self.data['births'] = [] # Currently not implemented yet.
        self.data['deaths'] = [] # Currently not implemented yet.
        self.data['infobox'] = []
        self.data['other'] = []
        self.data['years'] = []
        # A regex for the titles of articles about years. I don't bother years
        # b. C. because anniversaries would be confused anyhow.
        # Listing b. C. years will seriously slow the program down!
        # As in most wikis year articles have the title in the form of a simple
        # number, and number articles have some addition, usually you
        # don't have to modify this.
        if self.year5 is None: # 0 is not a year
            # If you want to search anniversaries in every year:
            self.yearregex = r'^[1-9]\d*$'
        elif self.year5 == 0: # 0 is not a year
            # Will search for years with the appropriate ending modulo 5:
            self.yearregex = r'^(\d+0|\d*5)$'
        else:
            self.yearregex = r'^\d*[%d%d]$' % (self.year5, self.year5 + 5)
        # Create a regex which shows how the dates are written in your wiki.
        # Think of various linking possibilities!
        # This one does not contain year; may be used in the articles of years.
        if self.day < 10:
            r = r'0?%d' % self.day
        else:
            r = r'%d' % self.day
        m = date.monthName(self.site.lang, self.month)
        # ?P<year> identifies the year part (this is the sortkey for results)
        # ?P<date> identifies the date part w/o year (currently not used AFAIK)
        self.dateregex = re.compile(
            r'(?Li)(\[{2})?(?P<date>%s *%s\.?)(\|.*?)?(\]{2})?(?!\d)' % (m, r))
        # And this one with years (I don't treat 0 separately here)
        # I use the bot with year5 only, so I may use it in regex,
        # but if you use it without year5, don't use it here either!
        self.dateregexwithyear = re.compile(
        r'(?Li)(\[{2})?(?P<year>\d*[%d%d])(\]{2})?\.? *(\[{2})?(?P<date>%s *%s\.?)(\|.*?)?(\]{2})?(?!\d)' \
            % (self.year5, self.year5 + 5, m, r))
        self.fd = date.FormatDate(self.site)
        gens = [self.list(self.month, self.day), self.yearlist()]
        self.generator = pagegenerators.PreloadingGenerator(pagegenerators.CombinedPageGenerator(gens))
        
    def list(self, month, day):
        """ Return a page generator for the articles linking to the date. """
        daypage = pywikibot.Page(self.site, self.fd(month, day))
        return pagegenerators.RegexFilterPageGenerator(
            pagegenerators.NamespaceFilterPageGenerator(
                pagegenerators.ReferringPageGenerator(daypage), 0, self.site),
            exceptions, quantifier='none')
 
    def yearlist(self):
        """ Return a page generator for the articles of years. """
        for i in range(1, datetime.datetime.today().year):
            yield pywikibot.Page(self.site, str(i))
    
    def parse3(self, text):
        """Parse the text.
        
        We divide the page text to 3 parts:
        A: text before the first == level section title
        B: text from the first section title to the first stopsection
        C: text from the first stopsection to the end.
        A and B will be returned as a tuple and poor C will be thrown away.
        """
        lines = text.splitlines(1)
        comeon = True
        where = 0
        linenum = 0
        tx1 = tx2 = ''
        while comeon and linenum < len(lines):
            line = lines[linenum]
            if sectionpattern.match(line) and not pywikibot.isDisabled(text,where):
                tx2 = line
                comeon = False
            else:
                tx1 += line
            where += len(line)
            linenum += 1
        comeon = True
        while comeon and linenum < len(lines):
            line = lines[linenum]
            if stopsectionregex.match(line) and not pywikibot.isDisabled(text,where):
                comeon = False
            else:
                tx2 += line
            where += len(line)
            linenum += 1
        return (tx1, tx2)
    
    def template_processor(self, page, introtext):
        """Process templates.
        
        Infoboxes in the introduction will be processed and removed.
        Other templates will just be removed (most often these are amboxes).
        page is needed as parameter for storing as result
        """
        templates = pywikibot.extract_templates_and_params(introtext)
        for t in templates:
            if re.search(infobox, t[0]):
                # print t #debug only
                for k in t[1].keys():
                    # pywikibot.output(k) #debug only
                    # pywikibot.output(t[1][k])
                    m = self.dateregexwithyear.search(t[1][k])
                    if m:
                        # We have just found the date we are looking for :-)
                        d = {
                            'page': page,
                            'year': int(m.group('year')),
                            'text': k + ' = ' + m.group()
                        }
                        self.data['infobox'].append(d)
                        # pywikibot.output('\03{green}Bingó! ' + d['text'] + '\03{default}')
        # Removal (must be repeated for nested templates):
        while TEMP_REGEX.search(introtext):
            introtext = TEMP_REGEX.sub('',introtext)
        return introtext
    
    def birthdeath(self, page, introtext):
        """ Trying to find birth and death dates in introduction. """
        # But not yet
        pass
    
    def otherdates(self, page, text):
        # First we remove any cite* templates (öööö erghh later someday)
 
        for m in self.dateregexwithyear.finditer(text):
            # print m.group()
            minus = min(m.start(), 60)
            plus = min(len(text) - m.end(), 60)
            show = text[m.start()-minus : m.end()+plus].replace('\n', ' ')
            show = show.replace('<', '&lt;') # Just in case
            show = show.replace('>', '&gt;') # escape any <nowiki>s
            show = "''<nowiki>" + show + "</nowiki>''"
            d = {
                'page': page,
                'year': int(m.group('year')),
                'text': show
            }
            self.data['other'].append(d)
            # pywikibot.output('\03{green}Bingó! ' + d['text'] + '\03{default}')
    
    def yearprocess(self, page, text):
        # This will be more simple.
        for line in text.splitlines():
            m = self.dateregex.search(line)
            if m:
                # We have just found the date we are looking for :-)
                if line.startswith('*'):
                    line = line[1:]
                show = line.replace('nowiki>', '') # Just in case
                show = "''<nowiki>" + show + "</nowiki>''"
                d = {
                    'page': page,
                    'year': int(page.title()),
                    'text': show
                }
                self.data['years'].append(d)
                # pywikibot.output('\03{green}Bingó! ' + d['text'] + '\03{default}')
    
    def treat(self, page):
        """ Process a page. """
        try:
            text = page.get()
        except pywikibot.NoPage:
            return # Bot runs slowly, we cannot exclude a deletion meanwhile.
        except pywikibot.IsRedirectPage:
            return
        # OK to run
        pywikibot.output('* [[%s]]' % page.title())
        # pywikibot.output(text) # debug only
        # First task is to remove references as they often contain dates of
        # publishing. And HTML comments as well, because why not?
        text = references.sub('', text)
        text = HTMLcomments.sub('', text)
        texttuple = self.parse3(text)
        # pywikibot.output(texttuple[1]) # debug only
        if not re.compile(self.yearregex, re.I).search(page.title()):
            introtext = self.template_processor(page, texttuple[0])
            # pywikibot.output(introtext) # debug only
            self.birthdeath(page, introtext)
            self.otherdates(page, introtext + texttuple[1])
        else: # An article of a year
            text = texttuple[0] + texttuple[1]
            self.yearprocess(page, text)
    
    def categories(self):
        """
        Generate the categories of the result page.
        
        This method will return a string with the categories of the result
        page. This string will be copied to the bottom of the page.
        You may write here anything else you want to see at the bottom or
        return '' for leaving it empty.
        """
        footer = u"\n[[Kategória:Évfordulók adatbázisa (’%d és ’%d)]]\n" % \
            (self.year5, self.year5 + 5)
        footer += u"[[Kategória:Évfordulók adatbázisa (%s)]]\n" % \
            date.monthName(self.site.lang, self.month)
        return footer
    
    def createpage(self, checkonly=False):
        #global hiba - That's my own stuff.
        # For localization modify the page name and 4 section titles below.
        # Page will be created with the title basepage/daytitle.
        # If checkonly is True, this method won't create anything, rather
        # returns the title of the result page for checking its existence.
        daytitle = '/’%d és ’%d/%02d-%02d' % \
            (self.year5, self.year5 + 5, self.month, self.day)
        targetpage = basepage + daytitle # Where to save the result
        if checkonly:
            return targetpage
        # The template which appears in the anniversaries section of main page:
        templatepage = 'Sablon:Évfordulók' + daytitle
        sections = dict()
        # Section title for births (currently not implemented)
        sections['births'] = 'Születések'
        # Section title for deaths (currently not implemented)
        sections['deaths'] = 'Halálozások'
        # Section title for infoboxes
        sections['infobox'] = 'Infoboxok'
        # Section title for the remaining
        sections['other'] = 'Egyéb'
        # Section title for the articles about years
        sections['years'] = 'Évszámos cikkek'
        # At the beginning of the page we link the article of the date itself.
        # It is not subject to analyzation as it is human readable.
        # This is the "main article" template and a warning to sources as they
        # are often missing from articles of dates. Localize this, too.
        outtext = header + \
            '{{fő|%s}}\n' % self.fd(self.month, self.day)
        #Now we link the template where the anniversaries may be written:
        outtext += '* A kezdőlapra kerülő sablon: [[%s]]\n' % templatepage
 
        # This loop will determine the order of output:
        for sect in ['births', 'deaths', 'infobox', 'other', 'years']:
            if len(self.data[sect]):
                outtext += '== '+ sections[sect] + ' ==\n'
                for item in sorted(self.data[sect], key=lambda x: x['year']):
                    outtext += u"* '''%s''': %s\n" % (
                            item['page'].title(asLink=True), item['text'])
        outtext += self.categories() # Anything you want to write at the bottom
        pywikibot.output(outtext)
        # Write here your bot's summary:
        editsummary = 'Az évfordulók frissítése bottal'
 
        # And finally, we are ready to save the result!
        page = pywikibot.Page(self.site, targetpage)
        try:
            page.put(outtext, editsummary)
        except:
            pywikibot.output(daytitle + ' not saved.')
            #hiba = True - That's my own stuff.
    
    def run(self):
        pywikibot.output(self.fd(self.month, self.day))
        # Do we have to process anything at all? Depends on overwrite.
        if not self.overwrite:
            page = pywikibot.Page(self.site, self.createpage(checkonly=True))
            if page.exists():
                pywikibot.output(
                    '\03{lightyellow}' + page.title(asLink=True) + \
                    ' already exists, will be skipped.\03{default}' + \
                    '\nUse -noskip to force the bot to process it.')
                return

        super(DailyBot, self).run()
 
        # And finally:
        self.createpage()

def one_month(month, yearmodulo5=None, overwrite=False):
    """ Go throuh one month. """
    if month not in range(1, 13):
        return
    if yearmodulo5 is not None and (yearmodulo5 < 0 or yearmodulo5 > 4):
        return
    for i in range(1, date.getNumberOfDaysInMonth(month)+1):
        bot = DailyBot(month, i, yearmodulo5, overwrite)
        bot.run()

def nextmonth(withmodulo5=False, overwrite=False):
    """
    Go through the next month.
    
    Parameter withmodulo5:
        If True, it looks anniversaries for the current year modulo 5 (see doc)
        If False, it takes every year
    """
    today = datetime.datetime.today()
    nextM = today.month + 1
    nextY = today.year
    if nextM > 12:
        nextM = 1
        nextY += 1
    print ('year=%d, month=%d' % (nextY, nextM))
    if withmodulo5:
        one_month(nextM, nextY % 5, overwrite)
    else:
        one_month(nextM, overwrite=overwrite)

def main(*args):
    mode = None
    overwrite = False
    for arg in pywikibot.handleArgs(*args):
        if arg in ['nextmonth', 'nextmonth5']:
            mode = arg
        elif arg == '-noskip':
            overwrite = True
    if mode == 'nextmonth':
        nextmonth(overwrite=overwrite)
    elif mode == 'nextmonth5':
        nextmonth(True, overwrite)
    else:
        # Wired-in behaviour
        # Callbot takes month, day and a year ending between 0 and 4 (year%5).
        # Sample:
        bot = DailyBot(4, 1, 4, overwrite)
        bot.run()

if __name__ == "__main__":
    try:
        #hiba = False
        #fatal = True
        main()
        #fatal = False
    finally:
        #levelez(fatal,hiba)
        pywikibot.stopme()
