# -*- coding: utf-8 -*-import sys,osfrom scrapy.cmdline import executesys.path.append(os.path.abspath(os.path.dirname(__file__)))execute("scrapy crawl QuanguoZuixin".split())execute("scrapy crawl beijing-zfwj".split())