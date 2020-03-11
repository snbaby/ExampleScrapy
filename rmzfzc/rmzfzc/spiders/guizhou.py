# -*- coding: utf-8 -*-
import scrapy

import logging

from scrapy_splash import SplashRequest
from rmzfzc.items import rmzfzcItem
from utils.tools.attachment import get_attachments,get_times
script = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(3))
  return splash:html()
end
"""


class GuizhouSpider(scrapy.Spider):
    name = 'guizhou'
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
        'SPLASH_URL': "http://localhost:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'szfl',  # 省政府令
                    'url': 'http://www.guizhou.gov.cn/zwgk/zcfg/szfwj_8191/szfl_8192/index.html'
                },
                {
                    'topic': 'wzjd',  # 文字解读
                    'url': 'http://www.guizhou.gov.cn/jdhy/zcjd_8115/wzjd/index.html'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'], args={'lua_source': script, 'wait': 1, 'resource_timeout': 10}, callback=self.parse_page,
                                    meta=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        print(page_count)
        try:
            for pagenum in range(page_count):
                if pagenum == 0:
                    url = response.meta['url']
                else:
                    url = response.meta['url'].replace(
                        '.html', '_' + str(pagenum) + '.html')
                yield SplashRequest(url, args={'lua_source': script, 'wait': 1, 'resource_timeout': 10}, callback=self.parse, meta=response.meta)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                print(response.css('.page a:nth-last-child(3)::text').extract_first())
                return int(
                    response.css('.page a:nth-last-child(3)::text').extract_first())
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        if response.meta['topic'] == 'szfl':
            for href in response.css(
                    '.right-list-box ul li a::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield SplashRequest(url, args={'lua_source': script, 'wait': 1, 'resource_timeout': 10}, callback=self.parse_szfl, meta={'url': url}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)
        else:
            for href in response.css(
                    '.zcjd_list ul li h2 a::attr(href)').extract():
                try:
                    url = response.urljoin(href)
                    yield SplashRequest(url, args={'lua_source': script, 'wait': 1, 'resource_timeout': 10}, callback=self.parse_wzjd, meta={'url': url}, dont_filter=True)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)

    def parse_szfl(self, response):
        try:
            item = rmzfzcItem()
            appendix, appendix_name = get_attachments(response)
            item['title'] = response.css(
                '.Article_xx table tr:nth-child(4) td:nth-child(2)::text').extract_first().strip()
            item['article_num'] = response.css(
                '.Article_xx table tr:nth-child(3) td:nth-child(2)::text').extract_first().strip()
            item['content'] = response.css('.zw-con').extract_first()
            item['appendix'] = appendix
            item['source'] = response.xpath('//label[contains(text(),"文章来源")]/text()').extract_first().replace('文章来源：','')
            item['time'] = response.xpath(
                '//*[@class="Article_ly"]/span[contains(text(),"发布时间")]/text()').extract_first()
            item['province'] = '贵州省'
            item['city'] = ''
            item['area'] = ''
            item['website'] = '贵州省人民政府'
            item['link'] = response.meta['url']
            item['txt'] = ''.join(response.css('.zw-con *::text').extract())
            item['appendix_name'] = appendix_name
            item['module_name'] = '贵州省人民政府'
            item['spider_name'] = 'guizhou'
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

    def parse_wzjd(self, response):
        try:
            item = rmzfzcItem()
            appendix, appendix_name = get_attachments(response)
            if response.css('#Zoom div:nth-child(1)::attr(class)') == 'Article_xx':
                item['title'] = response.css(
                    '.Article_xx table tr:nth-child(4) td:nth-child(2)::text').extract_first().strip()
                item['article_num'] = response.css(
                    '.Article_xx table tr:nth-child(3) td:nth-child(2)::text').extract_first().strip()
                item['content'] = response.css('.zw-con').extract_first()
                item['appendix'] = appendix
                item['source'] = response.xpath('//label[contains(text(),"文章来源")]/text()').extract_first().replace('文章来源：','')
                item['time'] = response.xpath('//*[@class="Article_ly"]/span[contains(text(),"发布时间")]/text()').extract_first()
                item['province'] = '贵州省'
                item['city'] = ''
                item['area'] = ''
                item['website'] = '贵州省人民政府'
                item['link'] = response.meta['url']
                item['txt'] = ''.join(response.css('.zw-con *::text').extract())
                item['appendix_name'] = appendix_name
                item['module_name'] = '贵州省人民政府'
                item['spider_name'] = 'guizhou'
            else:
                item['title'] = response.css('.Article_bt h1::text').extract_first().strip()
                item['article_num'] = ''
                item['content'] = response.css('.zw-con').extract_first()
                item['appendix'] = appendix
                item['source'] = response.xpath('//label[contains(text(),"文章来源")]/text()').extract_first().replace('文章来源：','')
                item['time'] = response.xpath('//*[@class="Article_ly"]/span[contains(text(),"发布时间")]/text()').extract_first()
                item['province'] = '贵州省'
                item['city'] = ''
                item['area'] = ''
                item['website'] = '贵州省人民政府'
                item['link'] = response.meta['url']
                item['txt'] = ''.join(response.css('.zw-con *::text').extract())
                item['appendix_name'] = appendix_name
                item['module_name'] = '贵州省人民政府'
                item['spider_name'] = 'guizhou'
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
