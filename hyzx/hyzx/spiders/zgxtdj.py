# -*- coding: utf-8 -*-
import scrapy
import logging

from hyzx.items import hyzxItem
from utils.tools.attachment import get_times
class ZgxtdjSpider(scrapy.Spider):
    name = 'zgxtdj'
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
        'SPLASH_URL': "http://47.106.239.73:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'zgxtdj',  # 中国信托登记
                    'url': 'http://www.chinatrc.com.cn/news/trade/index.html'
                }
            ]
            for content in contents:
                yield scrapy.Request(content['url'], callback=self.parse_page,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}, meta=content, dont_filter=True)
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
                    url = response.meta['url'].replace('.html',str(pagenum+1)+'.html')
                yield scrapy.Request(url, callback=self.parse,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}, meta=response.meta, dont_filter=True)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.css('.layui-laypage a:nth-last-child(2)::text').extract_first())
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for href in response.css('.news-main-list a::attr(href)').extract():
            try:
                url = response.urljoin(href)
                yield scrapy.Request(url, callback=self.parse_item,headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}, meta={'url': url}, dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response):
        try:
            item = hyzxItem()
            item['title'] = response.css('title::text').extract_first().replace(' - 中国信托登记有限责任公司','').strip()
            item['date'] = response.css('.news-detail-time::text').extract_first().split('时间：')[1].split('浏览')[0].strip()
            item['resource'] = response.css('.news-detail-time::text').extract_first().split('时间：')[0].split('来源：')[1].replace('来源：','').strip()
            item['content'] = response.css('.ueditor_content_parse').extract_first()
            item['website'] = '中国信托登记有限责任公司'
            item['link'] = response.meta['url']
            item['spider_name'] = 'zgxtdj'
            item['txt'] = ''.join(response.css('.ueditor_content_parse *::text').extract())
            item['module_name'] = '信托融资一行业资讯-中国信托登记有限责任公司'
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