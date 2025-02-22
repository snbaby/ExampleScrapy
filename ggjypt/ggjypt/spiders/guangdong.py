# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from ggjypt.items import ztbkItem
from utils.tools.attachment import get_attachments,get_times

script = """
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(1))
  return {
    html = splash:html(),
  }
end
"""


class guangdongSzfwjSpider(scrapy.Spider):
    name = 'guangdong_ggjypt'
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
        },
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'SPLASH_URL': "http://localhost:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            url = "http://www.gzzb.gd.cn/cms/wz/view/index/layout2/zfcglist.jsp?siteId=1&channelId=456"
            yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse_type)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_type(self, response):
        for href in response.xpath('//div[@class="cd_li"]//a[contains(@href,"cms")]/@href'):
            try:
                url = response.urljoin(href.extract())
                yield SplashRequest(url,callback=self.parse_page, dont_filter=True,meta={'url':url})
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        if page_count > 0:
            page_count = page_count + 1
            try:
                for pagenum in range(page_count):
                    if pagenum > 1:
                        temUrl = response.meta['url']
                        tmp = temUrl.split('?')
                        temUrl = tmp[0] + '?page='
                        url = temUrl + str(pagenum) + '&' + tmp[1]
                        yield SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse, dont_filter=True)
                    else:
                        yield SplashRequest(response.meta['url'], args={'lua_source': script, 'wait': 1}, callback=self.parse,
                                            dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)
        else:
            yield SplashRequest(response.meta['url'], args={'lua_source': script, 'wait': 1}, callback=self.parse,
                                dont_filter=True)
    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                if response.xpath('//*[@class="pagination page-mar"]/ul/span[3]').re(r'([1-9]\d*\.?\d*)'):
                    return int(
                        response.xpath('//*[@class="pagination page-mar"]/ul/span[3]').re(r'([1-9]\d*\.?\d*)')[0])
                else:
                    return 0
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for selector in response.xpath('//table[@class="wsbs-table"]/tr'):
            if selector.xpath('./td'):
                try:
                    item = {}
                    item['title'] = "".join(selector.xpath('./td[2]/a/text()').extract())
                    item['time'] = selector.xpath('./td[3]/text()').extract_first()
                    url = response.urljoin(selector.xpath('./td[2]/a/@href').extract_first())
                    print('url==='+url)
                    yield scrapy.Request(url,callback=self.parse_item, dont_filter=True, meta=item)
                except Exception as e:
                    logging.error(self.name + ": " + e.__str__())
                    logging.exception(e)
        # 处理翻页
        # 1. 获取翻页链接
        # 2. yield scrapy.Request(第二页链接, callback=self.parse, dont_filter=True)

    def parse_item(self, response):
        if response.xpath('//div[@class="xx-text"]'):
            try:
                appendix, appendix_name = get_attachments(response)
                category = '其他';
                title = response.meta['title']
                if title.find('招标') >= 0:
                    category = '招标'
                elif title.find('中标') >= 0:
                    category = '中标'
                elif title.find('成交') >= 0:
                    category = '成交'
                elif title.find('结果') >= 0:
                    category = '结果'
                elif title.find('单一') >= 0:
                    category = '单一'
                item = ztbkItem()
                item['title'] = title
                item['content'] = "".join(response.xpath('//div[@class="xx-text"]').extract())
                item['source'] = ''
                item['category'] = category
                item['type'] = ''
                item['region'] = '广东省'
                item['time'] = response.meta['time']
                item['website'] = '广东省公共资源交易服务平台'
                item['module_name'] = '广东省-公共交易平台'
                item['spider_name'] = 'guangdong_ggjypt'
                item['txt'] = "".join(response.xpath('//div[@class="xx-text"]//text()').extract())
                item['appendix_name'] = appendix_name
                item['link'] = response.request.url
                item['appendix'] = appendix
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
        else:
            logging.error('内容为空,url' + response.request.url)