#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# (C) Tacsipacsi, 2018
#
# Distributed under the terms of MIT License.
#
from __future__ import unicode_literals
import codecs
import re

import pywikibot
from pywikibot import pagegenerators as pg, textlib, bot
from pywikibot.bot import SingleSiteBot

class AssessmentTemplate(pywikibot.Page):
    """An assessment template."""
    multi = False
    redirs = []
    
    def __init__(self, source, title, multi=False):
        super(AssessmentTemplate, self).__init__(source, title, ns=10)
        self.multi = multi
        for redir in self.getReferences(redirectsOnly=True, namespaces=[10], follow_redirects=False):
            self.redirs.append(redir.title(withNamespace=False))
    
    def __eq__(self, other):
        if isinstance(other, pywikibot.page.BasePage):
            other = other.title(withNamespace=False)
        if isinstance(other, str):
            return (other == self.title(withNamespace=False) or other in self.redirs)
        else:
            return NotImplementedError

class SelfAssessmentCollecterBot(SingleSiteBot):
    """A bot collecting assessments of own articles."""
    
    file = 'selfassess.tsv'
    assessmentTemplateCategory = u'Műhelyek cikkértékelő sablonjai'
    multiAssessmentTemplate = u'Több WP'
    userParam = u'szerkesztő'
    fields_to_write = [u'besorolás', u'szint', u'fontosság', u'szerkesztő', u'dátum']
    
    templates = []
    
    def __init__(self, user):
        super(SelfAssessmentCollecterBot, self).__init__()
        self.user = pywikibot.User(self.site, user).title(withNamespace=False)
        pywikibot.output('User: %s' % self.user)
        self.generator = self.gen()
        self.getTemplates()
        self.multiAssessmentTemplate = AssessmentTemplate(self.site, self.multiAssessmentTemplate, True)
    
    def gen(self):
        for page in pg.PreloadingGenerator(pg.UserContributionsGenerator(self.user, namespaces=[0])):
            if next(page.revisions(reverse=True)).user == self.user:
                talk = page.toggleTalkPage()
                if talk.exists():
                    yield talk
        
    def getTemplates(self):
        category = pywikibot.Category(self.site, self.assessmentTemplateCategory)
        pages = set(pg.CategorizedPageGenerator(category, namespaces=[10]))
        pages.add(pywikibot.Page(self.site, self.multiAssessmentTemplate, ns=10))
        for member in pages:
            self.templates.append(member.title(withNamespace=False))
            for page in member.getReferences(redirectsOnly=True, namespaces=[10], follow_redirects=False):
                self.templates.append(page.title(withNamespace=False))
    
    def isSearchedUser(self, user):
        pywikibot.output('Assessing user: "%s"' % user)
        return (user and pywikibot.User(self.site, user).title(withNamespace=False) == self.user)
    
    def found(self, page, params, n=None):
        """Treat a found template.
        
        @param page: Page object of the found talk page.
        @param params: Template parameters dictionary.
        @param n: Which subtemplate is the match, or None if basic templates are used.
        """
        pywikibot.output('\03{lightgreen}MATCH: %s\03{default}' % page)
        fields = [page.title()]
        for field in self.fields_to_write:
            if n is not None:
                field = '%s%d' % (field, n)
            if field in params:
                fields.append(params[field])
            else:
                fields.append('')
        with codecs.open(self.file, 'a', 'utf-8') as file:
            file.write('\t'.join(fields))
    
    def treat(self, page):
        pywikibot.output(page)
        talktext = page.get()
        templates = textlib.extract_templates_and_params(talktext)
        for (template, fields) in templates:
            try:
                template = pywikibot.Page(self.site, template, ns=10).title(withNamespace=False)
            except (pywikibot.exceptions.InvalidTitle, LookupError):
                pywikibot.error('Invalid template name: %s' % template)
                continue
            if AssessmentTemplate(self.site, template) not in self.templates:
                continue
            params = {}
            for name, value in fields.items():
                name = name.strip()
                value = value.strip()
                params[name] = value
            if template == self.multiAssessmentTemplate:
                for name in params:
                    rem = re.match((r'%s(\d+)' % self.userParam), name)
                    if rem and self.isSearchedUser(params[name]):
                        self.found(page, params, rem.group(1))
            elif self.userParam in params and self.isSearchedUser(params[self.userParam]):
                self.found(page, params)
                    
def main(*args):
    args = pywikibot.handle_args(args)
    user = args[0]
    bot = SelfAssessmentCollecterBot(user)
    bot.run()

if __name__ == '__main__':
    main()
