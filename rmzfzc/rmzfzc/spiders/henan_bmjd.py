# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from rmzfzc.items import rmzfzcItem

script = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(1))
  return {
    html = splash:html(),
  }
end
"""


class TianJinSzfwjSpider(scrapy.Spider):
    name = 'henan_bmjd'
    custom_settings = {
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'utils.middlewares.MyUserAgentMiddleware.MyUserAgentMiddleware': 126,
            'utils.middlewares.DeduplicateMiddleware.DeduplicateMiddleware': 130,
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': 'http://localhost:8050/'}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            url = "https://www.henan.gov.cn/zwgk/zcjd/bmjd/index.html"
            yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse_page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        try:
            # 在解析翻页数之前，首先解析首页内容
            self.parse(response)
            for pagenum in range(page_count):
                url = "https://www.henan.gov.cn/zwgk/zcjd/bmjd/index_" + \
                      str(pagenum) + ".html" if pagenum > 0 else "https://www.henan.gov.cn/zwgk/zcjd/bmjd/index.html"
                yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                self.add_pagenum = int(response.xpath('//div[@id="pageDec"]').re(r'([1-9]\d*\.?\d*)')[1])//int(response.xpath('//div[@id="pageDec"]').re(r'([1-9]\d*\.?\d*)')[0]) +1
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for href in response.xpath('//div[@class="mt15 list-box"]/ul/li/a/@href'):
            try:
                print('href===' + href.extract())
                yield scrapy.Request(href.extract(),callback=self.parse_item, dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)
        # 处理翻页
        # 1. 获取翻页链接
        # 2. yield scrapy.Request(第二页链接, callback=self.parse, dont_filter=True)

    def parse_item(self, response):
        try:
            item = rmzfzcItem()
            item['title'] = response.xpath('//*[@id="title"]/text()').extract_first()
            item['article_num'] = ''
            item['content'] = "".join(response.xpath('//div[@id="content"]').extract())
            item['source'] = response.xpath('//*[@id="source"]/text()').extract_first()
            item['time'] = response.xpath('//*[@id="pubDate"]/text()').extract_first()
            item['province'] = '河南省'
            item['city'] = ''
            item['area'] = ''
            item['website'] = '河南省人民政府'
            item['module_name'] = '河南省人民政府-部门解读'
            item['spider_name'] = 'henan_bmjd'
            item['txt'] = "".join(response.xpath('//div[@id="content"]//text()').extract())
            item['appendix_name'] = ''
            item['link'] = response.request.url
            appendix = []
            # for href in response.xpath('.relevantdoc.xgjd a::href'):
            #    appendix.append(href.extract())
            item['appendix'] = ''
            print(
                "===========================>crawled one item" +
                response.request.url)
        except Exception as e:
            logging.error(
                self.name +
                " in parse_item: url=" +
                response.request.url +
                ", exception=" +
                e.__str__())
            logging.exception(e)
        yield item
