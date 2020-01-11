# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html
import re
from urllib import parse
from scrapy.item import Field
import scrapy
from scrapy.loader.processors import TakeFirst, MapCompose, Join


class cnki_chengguoItem(scrapy.Item):
    name = scrapy.Field()
    accomplish_person = scrapy.Field()
    first_accomplish_company = scrapy.Field()
    keyword = scrapy.Field()
    zt_type = scrapy.Field()
    xk_type = scrapy.Field()
    intro = scrapy.Field()
    type = scrapy.Field()
    time = scrapy.Field()
    research_time = scrapy.Field()
    website = scrapy.Field()
    link = scrapy.Field()
    create_time = scrapy.Field()
    spider_name = scrapy.Field()
    module_name = scrapy.Field()
