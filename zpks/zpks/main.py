# -*- coding: utf-8 -*-import sys,osfrom scrapy.cmdline import executesys.path.append(os.path.abspath(os.path.dirname(__file__)))os.system("scrapy crawl boss")os.system("scrapy crawl zlzp")os.system("scrapy crawl zpks_qcwy")os.system("scrapy crawl lgw")