#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
This script archives the [[Wikipédia:Tudakozó]] (Reference Desk) on hu.wikipedia.
"""
#
# (C) qcz, 2008-2016
# (C) Tacsipacsi, 2016
#
# Distributed under the GNU General Public License, version 3 or later version.
#
from __future__ import absolute_import, unicode_literals

import re
import datetime
from datetime import date
import pywikibot

def main(*args):
    local_args = pywikibot.handle_args(args)
    
    site = pywikibot.Site('hu', 'wikipedia')
    site.login()
    
    ma = (date.today() - datetime.timedelta(days=1)).isoformat()
    maiArch = pywikibot.Page(site, 'Tudakozó/Archívum/' + ma, 4)
    if maiArch.exists():
        pywikibot.output('Ma már történt archiválás...')
    else:
        tudMost = pywikibot.Page(site, 'Tudakozó', 4)
        tudMost = tudMost.move(maiArch.title(), reason='Bot: Tudakozó napi archiválása', movetalkpage=False)
        regexp = r'\{\{/Fejrész\}\}'
        if re.search(regexp, tudMost.text) != None:
            tudMost.text = re.sub(regexp, '<noinclude>{{Tudakozó-keretes}}</noinclude>', tudMost.text)
            tudMost.save(summary='Bot: fejrész cseréje az archívumsablonra', minor=False)
        
        ujMost = pywikibot.Page(site, 'Tudakozó', 4)
        ujMost.text = '{{/Fejrész}}'
        ujMost.save(summary='Bot: új, üres oldal elhelyezése', minor=True)

if __name__ == '__main__':
    main()
