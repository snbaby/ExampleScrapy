# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from rmzfzc.items import rmzfzcItem
from utils.tools.attachment import get_attachments,get_times
script ="""
function main(splash, args)
  assert(splash:go(args.url))
  assert(splash:wait(1))
  return {
    html = splash:html(),
  }
end
"""

class QuanguoZuixinSpider(scrapy.Spider):
    name = 'quanguo_xxgk'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 0,
        'DOWNLOAD_DELAY': 0.5,
        'SPIDER_MIDDLEWARES':{
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

        'DUPEFILTER_CLASS':'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE':'scrapy_splash.SplashAwareFSCacheStorage',
    }
    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        urlList = ['http://sousuo.gov.cn/list.htm?q=&n=15&t=paper&childtype=&subchildtype=&pcodeJiguan=&pcodeYear=&pcodeNum=&location=&sort=publishDate&searchfield=&title=&content=&pcode=&puborg=&timetype=timeqb&mintime=&maxtime=&offsetp=-1&p=1']
        try:
            yield SplashRequest('http://sousuo.gov.cn/list.htm?q=&n=15&t=paper&childtype=&subchildtype=&pcodeJiguan=&pcodeYear=&pcodeNum=&location=&sort=publishDate&searchfield=&title=&content=&pcode=&puborg=&timetype=timeqb&mintime=&maxtime=&offsetp=-1&p=1', args={'lua_source': script, 'wait': 1}, callback=self.parse_page)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count  = int(self.parse_pagenum(response))
        print(page_count)
        try:
            preUrl = 'http://sousuo.gov.cn/list.htm?q=&n=15&p='
            for pagenum in range(page_count):
                url = preUrl + str(pagenum) +"&t=paper&sort=publishDate&childtype=&subchildtype=&pcodeJiguan=&pcodeYear=&pcodeNum=&location=&searchfield=&title=&content=&pcode=&puborg=&timetype=timeqb&mintime=&maxtime="
                yield  SplashRequest(url, args={'lua_source': script, 'wait': 1}, callback=self.parse)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return response.xpath('//*[@class="jilu"]').re(r'([1-9]\d*\.?\d*)')[0]
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for selector in response.xpath('//*[@class="dataList"]/tr'):
            try:
                item = {}
                item['title'] = selector.xpath('./td[2]/a/text()').extract_first()
                item['time'] = selector.xpath('./td[5]/text()').extract_first()
                item['article_num'] = selector.xpath('./td[3]/text()').extract_first()
                item['source'] = selector.xpath('./td[2]/ul/li[3]/text()').extract_first()
                url = selector.xpath('./td[2]/a/@href').extract_first()
                if url:
                    yield scrapy.Request(url,callback=self.parse_item, dont_filter=True, meta=item)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response):
        try:
            if response.meta['title']:
                item = rmzfzcItem()
                appendix, appendix_name = get_attachments(response)
                item['title'] = response.meta['title']
                item['article_num'] = response.meta['article_num']
                item['content'] = "".join(response.xpath('//*[@class="b12c"]').extract())
                item['appendix'] = appendix
                item['source'] = response.meta['source']
                item['time'] = response.meta['time']
                item['province'] = '国家'
                item['city'] = ''
                item['area'] = ''
                item['website'] = '中华人民共和国中央人民政府'
                item['module_name'] = '中华人民共和国中央人民政府-政策解读'
                item['spider_name'] = 'quanguo_xxgk'
                item['txt'] = "".join(response.xpath('//*[@class="b12c"]//text()').extract())
                item['appendix_name'] = appendix_name
                item['link'] = response.request.url
                item['time'] = get_times(item['time'])
                print("===========================>crawled one item" +
                    response.request.url)
        except Exception as e:
            logging.error(self.name + " in parse_item: url=" + response.request.url + ", exception=" + e.__str__())
            logging.exception(e)
        yield item
