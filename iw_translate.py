#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Translate article titles, i.e. list titles of articles in a given
language connected to articles in another language.

Arguments:

-targetlang       Language to translate to (required)

&params;
"""
#
# (0) 2021
#
# Released into the public domain
#
import pywikibot
from pywikibot import pagegenerators
from pywikibot.bot import SingleSiteBot

docuReplacements = {'&params;': pagegenerators.parameterHelp}

class IwTranslateBot(SingleSiteBot):
    def __init__(self, generator, targetlang: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.generator = generator
        self.targetlang = targetlang

    def treat(self, page):
        for link in page.iterlanglinks(include_obsolete=True):
            if link.site.lang == self.targetlang:
                print(pywikibot.Page(link).title(with_ns=True))

def main(*args):
    targetlang = None
    gen = pagegenerators.GeneratorFactory()
    for arg in pywikibot.handle_args(args):
        if arg.startswith('-targetlang:'):
            targetlang = arg[len('-targetlang:'):]
        else:
            gen.handle_arg(arg)
    generator = gen.getCombinedGenerator()
    bot = IwTranslateBot(generator, targetlang)
    bot.run()

if __name__ == '__main__':
    main()
