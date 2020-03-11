# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from ggjypt.items import ztbkItem
from utils.tools.attachment import get_attachments,get_times

script = """
function wait_for_element(splash, css, maxwait)
  -- Wait until a selector matches an element
  -- in the page. Return an error if waited more
  -- than maxwait seconds.
  if maxwait == nil then
      maxwait = 10
  end
  return splash:wait_for_resume(string.format([[
    function main(splash) {
      var selector = '%s';
      var maxwait = %s;
      var end = Date.now() + maxwait*1000;

      function check() {
        if(document.querySelector(selector)) {
          splash.resume('Element found');
        } else if(Date.now() >= end) {
          var err = 'Timeout waiting for element';
          splash.error(err + " " + selector);
        } else {
          setTimeout(check, 200);
        }
      }
      check();
    }
  ]], css, maxwait))
end

function main(splash, args)
  splash.images_enabled = false
  splash:go(args.url)
  wait_for_element(splash, ".pg_num_input")
  js = string.format("document.querySelector('#target').value =%d", args.page)
  splash:evaljs(js)
  splash:runjs("document.querySelector('#toview').innerHTML=''")
  splash:runjs("document.querySelector('#moreinfo').click()")
  wait_for_element(splash, ".list-tbnew")
  return splash:html()
end
"""

class GansuSpider(scrapy.Spider):
    name = 'chongqing_ggjypt'
    custom_settings = {
        'CONCURRENT_REQUESTS': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 10,
        'CONCURRENT_REQUESTS_PER_IP': 0,
        'DOWNLOAD_DELAY': 0.5,
        'DOWNLOADER_MIDDLEWARES' : {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES' : {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
        'HTTPCACHE_STORAGE' : 'scrapy_splash.SplashAwareFSCacheStorage',
        'ITEM_PIPELINES': {
            'utils.pipelines.MysqlTwistedPipeline.MysqlTwistedPipeline': 64,
            'utils.pipelines.DuplicatesPipeline.DuplicatesPipeline': 100,
        },
        'SPLASH_URL': "http://localhost:8050/"}

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
        try:
            contents = [
                {
                    'topic': 'chongqing',  # 重庆市公共资源拍卖交易网
                    'url': 'https://www.cqggzy.com/jyxx/jyxx-page.html'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'],
                    endpoint = 'execute',
                    args={
                        'lua_source': script,
                        'wait': 3,
                        'page': 1,
                        'url': content['url'],
                    },
                    callback=self.parse_page,
                    meta=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
        page_count = int(self.parse_pagenum(response))
        try:
            for pagenum in range(page_count):
                print(pagenum)
                if pagenum > 0:
                    yield SplashRequest(response.meta['url'],
                        endpoint='execute',
                        args={
                            'lua_source': script,
                            'wait': 1,
                            'page': pagenum,
                            'url': response.meta['url'],
                        },
                        callback=self.parse,
                        meta=response.meta)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_pagenum(self, response):
        try:
            # 在解析页码的方法中判断是否增量爬取并设定爬取列表页数，如果运行
            # 脚本时没有传入参数pagenum指定爬取前几页列表页，则全量爬取
            if not self.add_pagenum:
                return int(response.xpath('//*[@id="index"]').re(r'([1-9]\d*\.?\d*)')[1]) + 1
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)
    def parse(self, response):
        script = """
        function main(splash, args)
          assert(splash:go(args.url))
          assert(splash:wait(1))
          return {
            html = splash:html(),
          }
        end
        """
        for selector in response.xpath('//*[@class="list-tbnew"]/tbody/tr'):
            try:
                item = {}
                item['title'] = selector.xpath('./td[2]/a/text()').extract_first()
                item['time'] = selector.xpath('./td[4]/text()').extract_first()
                url = response.urljoin(selector.xpath('./td[2]/a/@href').extract_first())
                print(url)
                item['url'] = url
                yield SplashRequest(url,
                    endpoint='execute',
                    args={
                        'lua_source': script,
                        'wait': 1,
                        'url': url,
                    },
                    callback=self.parse_item,
                    meta=item)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response):
        if response.meta['title']:
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
                item['content'] = "".join(response.xpath('//div[@class="epoint-article-content"]').extract())
                item['source'] = response.xpath('//a[@class="originUrl"]/text()').extract_first()
                item['category'] = category
                item['type'] = ''
                item['region'] = '重庆市'
                item['time'] = get_times(response.meta['time'])
                item['website'] = '重庆市公共资源交易服务平台'
                item['module_name'] = '重庆市-公共交易平台'
                item['spider_name'] = 'chongqing_ggjypt'
                item['txt'] = "".join(response.xpath('//div[@class="epoint-article-content"]//text()').extract())
                item['appendix_name'] = appendix_name
                item['link'] = response.meta['url']
                item['appendix'] = appendix
                print(
                    "===========================>crawled one item" +
                    response.request.url)
                yield item
            except Exception as e:
                logging.error(
                    self.name +
                    " in parse_item: url=" +
                    response.request.url +
                    ", exception=" +
                    e.__str__())
                logging.exception(e)
