#!/usr/bin/python
# -*- coding: utf-8 -*-
r"""
Harvest all parameters of a template.

Usage:

* python pwb.py params_all -transcludes:"..."
* python pwb.py params_all [generators] -template:"..."

This will work on all pages that transclude the template.

These command line parameters can be used to specify which pages to work on:

&params;

Examples:

    python pwb.py param_all -lang:hu -transcludes:Literatur
"""
#
# (C) Multichill, Amir, 2013
# (C) Pywikibot team, 2013-2014
# (C) Tacsipacsi, 2018
#
# Distributed under the terms of MIT License.
#
from __future__ import absolute_import, unicode_literals

import codecs
import re
import signal

import pywikibot
from pywikibot import pagegenerators as pg, textlib, bot
from pywikibot.bot import SingleSiteBot

docuReplacements = {'&params;': pywikibot.pagegenerators.parameterHelp}

willstop = False

def _signal_handler(signal, frame):
    global willstop
    if not willstop:
        willstop = True
        print('Received ctrl-c. Finishing current item; '
              'press ctrl-c again to abort.')  # noqa
    else:
        raise KeyboardInterrupt

signal.signal(signal.SIGINT, _signal_handler)

class ParamsBot(SingleSiteBot):
    """A bot to harvest all parameters of a given template, including unused and misspelled ones."""

    def __init__(self, generator, templateTitle, file=None):
        """
        Constructor.

        Arguments:
            * generator     - A generator that yields Page objects.
            * templateTitle - The template to work on
            * file          - File name to write in, by default "params_<template title>.tsv"
        """
        super(ParamsBot, self).__init__()
        self.generator = pg.PreloadingGenerator(generator)
        self.templateTitle = templateTitle.replace(u'_', u' ')
        self.templateTitles = self.getTemplateSynonyms(self.templateTitle)
        self.file = file or u'params_%s.tsv' % templateTitle
        self.parameters = []

    def getTemplateSynonyms(self, title):
        """Fetch redirects of the title, so we can check against them."""
        temp = pywikibot.Page(pywikibot.Site(), title, ns=10)
        if not temp.exists():
            pywikibot.error(u'Template %s does not exist.' % temp.title())
            exit()

        # Put some output here since it can take a while
        pywikibot.output('Finding redirects...')
        if temp.isRedirectPage():
            temp = temp.getRedirectTarget()
        titles = [page.title(withNamespace=False)
                  for page in temp.getReferences(redirectsOnly=True, namespaces=[10],
                                                 follow_redirects=False)]
        titles.append(temp.title(withNamespace=False))
        return titles

    def write_file(self, text):
        with codecs.open(self.file, 'a', 'utf-8') as file:
            file.write(text)        

    def output(self, page, params):
        pywikibot.output(u'%s: %s' % (page.title(), params))

    def treat(self, page):
        """Process a single page."""
        if willstop:
            raise KeyboardInterrupt
        self.current_page = page
        
        pagetext = page.get()
        templates = textlib.extract_templates_and_params(pagetext)
        for (template, fielddict) in templates:
            # Clean up template
            try:
                template = pywikibot.Page(self.site, template,
                                          ns=10).title(withNamespace = False)
            except (pywikibot.exceptions.InvalidTitle, LookupError):
                pywikibot.error(
                    "Failed parsing template; '%s' should be the template name."
                    % template)
                continue
            # We found the template we were looking for
            if template in self.templateTitles:
                values = [None] * len(self.parameters)
                for param, value in fielddict.items():
                    param = param.strip()
                    value = value.strip()
                    if param in self.parameters:
                        values[self.parameters.index(param)] = value
                    else:
                        self.parameters.append(param)
                        values.append(value)
                self.output(page, fielddict)
                # Write in file
                self.write_file('%s\t%s\n' % (page.title(), '\t'.join([x if x is not None else '' for x in values])))

    def exit(self):
        self.write_file('\t%s\n' % '\t'.join(self.parameters))
        super(ParamsBot, self).exit()

def main(*args):
    """
    Process command line arguments and invoke bot.

    If args is an empty list, sys.argv is used.

    @param args: command line arguments
    @type args: list of unicode
    """
    template_title = None
    filename = None
    args = pywikibot.handle_args(*args)
    gen = pg.GeneratorFactory()
    
    for arg in args:
        if arg.startswith('-template'):
            if len(arg) == 9:
                template_title = pywikibot.input(u'Please enter the template to work on:')
            else:
                template_title = arg[10:]
        elif gen.handleArg(arg):
            if arg.startswith(u'-transcludes:'):
                template_title = arg[13:]
        elif arg.startswith('-outputfile'):
            if len(arg) == 11:
                filename = pywikibot.input(u'Please enter the output file name:')
            else:
                filename = arg[12:]

    if not template_title:
        pywikibot.error('Please specify either -template or -transcludes argument')
        return

    generator = gen.getCombinedGenerator()
    if not generator:
        gen.handleArg(u'-transcludes:' + template_title)
        generator = gen.getCombinedGenerator()

    bot = ParamsBot(generator, template_title, filename)
    bot.run()

if __name__ == '__main__':
    main()
