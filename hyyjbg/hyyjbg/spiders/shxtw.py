# -*- coding: utf-8 -*-
import scrapy
import logging

from hyyjbg.items import hyyjbgItem
from utils.tools.attachment import get_times
class ShxtwSpider(scrapy.Spider):
    name = 'shxtw'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 0,
        'DOWNLOAD_DELAY': 0.5,
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        # 'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': "http://localhost:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'shxtw',  # 上海信托网
                    'url': 'http://www.shxtw.net/class/zjgd/list_26_1.html'
                }
            ]
            for content in contents:
                yield scrapy.Request(content['url'], callback=self.parse_page, meta=content, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        try:
            for pagenum in range(page_count):
                url = response.meta['url']
                if pagenum == 0:
                    yield scrapy.Request(url, callback=self.parse, meta=response.meta, dont_filter=True)
                else:
                    url = url.replace('1.html', str(pagenum + 1) + '.html')
                    yield scrapy.Request(url, callback=self.parse, meta=response.meta, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.css('.pageinfo strong:nth-child(1)::text').extract_first())
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for href in response.css('.img a::attr(href)').extract():
            try:
                url = response.urljoin(href)
                yield scrapy.Request(url, callback=self.parse_item, meta={'url': url}, dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response):
        try:
            item = hyyjbgItem()
            item['title'] = response.css('h1::text').extract_first()
            item['date'] = response.css('p.p::text').extract_first().split('作者')[0].replace('时间：', '').strip()
            item['resource'] = ''
            content = ''
            txt = ''
            for selector in response.xpath('//div[@class="news_det"]/*'):
                if selector.xpath('./@class').extract_first() != 'mt1':
                    content = content + ''.join(selector.xpath('.').extract())
                    txt = content + ''.join(selector.xpath('.//text()').extract())
            item['content'] = content
            item['website'] = '上海信托网'
            item['link'] = response.meta['url']
            item['spider_name'] = 'shxtw'
            item['txt'] = txt
            item['module_name'] = '信托融资一行业基本报告-上海信托网'
            item['date'] = get_times(item['date'])
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