# -*- coding: utf-8 -*-
import scrapy

import logging
from utils.tools.attachment import get_attachments,get_times
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

class YunnanSpider(scrapy.Spider):
    name = 'yunnan'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 0,
        'DOWNLOAD_DELAY': 0.5,
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddleware.useragent.UserAgentMiddleware': None,
            'utils.middlewares.MyUserAgentMiddleware.MyUserAgentMiddleware': 126,
            'utils.middlewares.DeduplicateMiddleware.DeduplicateMiddleware': 130,
            'scrapy_splash.SplashCookiesMiddleware': 140,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': "http://47.106.239.73:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'zxwj',  # 最新文件
                    'url': 'http://www.yn.gov.cn/zwgk/zcwj/zxwj/index.html'
                },
                {
                    'topic': 'bmjd',  # 部门解读
                    'url': 'http://www.yn.gov.cn/zwgk/zcjd/bmjd/index.html'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'], args={'lua_source': script, 'wait': 1}, callback=self.parse_page,
                                    meta=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        try:
            for pagenum in range(page_count):
                if pagenum == 0:
                    url = response.meta['url']
                else:
                    url = response.meta['url'].replace(
                        '.html', '_' + str(pagenum) + '.html')
                yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, meta=response.meta)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.css('.ya-pagination li:nth-last-child(3) a::text').extract_first())
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        if response.meta['topic'] == 'zxwj':
            for href in response.css('.gwright a::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield scrapy.Request(url, callback=self.parse_zxwj, meta={'url': url}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)
        else:
            for href in response.css('.thc a::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield scrapy.Request(url, callback=self.parse_bmjd, meta={'url': url}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)

    def parse_zxwj(self, response):
        try:
            item = rmzfzcItem()
            appendix, appendix_name = get_attachments(response)
            item['title'] = response.css('.h3class::text').extract_first().strip()
            item['article_num'] = response.css('.referencebox dl:nth-child(2) dd::text').extract_first()
            if len(response.css('.TRS_UEDITOR').extract()) > 0:
                item['content'] = response.css('.TRS_UEDITOR').extract_first()
                item['txt'] = ''.join(response.css('.TRS_UEDITOR *::text').extract())
            else:
                item['content'] = response.css('.TRS_Editor').extract_first()
                item['txt'] = ''.join(response.css('.TRS_Editor *::text').extract())
            item['appendix'] = appendix
            item['source'] = response.css('.referencebox dl:nth-child(3) dd::text').extract_first()
            item['time'] = response.css('.referencebox dl:nth-child(4) dd::text').extract_first()
            item['province'] = '云南省'
            item['city'] = ''
            item['area'] = ''
            item['website'] = '云南省人民政府'
            item['link'] = response.meta['url']
            item['appendix_name'] = appendix_name
            item['module_name'] = '云南省人民政府'
            item['spider_name'] = 'yunnan'
            item['time'] = get_times(item['time'])
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

    def parse_bmjd(self, response):
        try:
            item = rmzfzcItem()
            item['title'] = response.css('.h3class::text').extract_first().strip()
            item['article_num'] = ''

            if len(response.css('.TRS_UEDITOR').extract()) > 0:
                item['content'] = response.css('.TRS_UEDITOR').extract_first()
                item['txt'] = ''.join(response.css('.TRS_UEDITOR *::text').extract())
            else:
                item['content'] = response.css('.TRS_Editor').extract_first()
                item['txt'] = ''.join(response.css('.TRS_Editor *::text').extract())
            item['appendix'] = ''
            item['source'] = response.css('.datetime::text').extract_first().strip().splitlines()[0].replace('来源：','')
            item['time'] = response.css('.datetime::text').extract_first().strip().splitlines()[2].strip()
            item['province'] = '云南省'
            item['city'] = ''
            item['area'] = ''
            item['website'] = '云南省人民政府'
            item['link'] = response.meta['url']
            #item['txt'] = ''.join(response.css('.TRS_UEDITOR *::text').extract())
            item['appendix_name'] = ''
            item['module_name'] = '云南省人民政府'
            item['spider_name'] = 'yunnan'
            item['time'] = get_times(item['time'])
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
