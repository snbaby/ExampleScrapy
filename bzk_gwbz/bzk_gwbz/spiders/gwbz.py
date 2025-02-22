# -*- coding: utf-8 -*-
import scrapy
import logging
from utils.tools.attachment import get_attachments,get_times
from scrapy_splash import SplashRequest
from bzk_gwbz.items import bzk_gwbzItem

class GwbzSpider(scrapy.Spider):
    name = 'gwbz'
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
                  splash:go(args.url)
                  wait_for_element(splash, "#ISO_list")
                  splash:runjs("submit('不限','','2','国际标准', 'ISO')")
                  splash:wait(5)
                  wait_for_element(splash, ".pages")
                  splash:runjs(args.js)
                  splash:wait(5)
                  return splash:html()
                end
                """
            urls = [
                'https://www.spc.org.cn/basicsearch'
            ]
            if not self.add_pagenum:
                pagenum = 30
            else:
                pagenum = self.add_pagenum
            for url in urls:
                for num in range(pagenum):
                    js = "submitIndexPage('" + str(num) + "')"
                    yield SplashRequest(url,
                                    endpoint='execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'url': url,
                                        'js': js
                                    },
                                    callback=self.parse,
                                    meta={
                                        'url': url
                                    })
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
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
                  splash:go(args.url)
                  splash:wait(1)
                  return splash:html()
                end
                """
        for list in response.css('.search-list'):
            try:
                url = 'https://www.spc.org.cn/online/' + list.css('a span::attr(title)').extract_first()
                yield SplashRequest(url,
                                    endpoint='execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'url': url,
                                    },
                                    callback=self.parse_item,
                                    dont_filter=True,
                                    meta={
                                        'url': url
                                    })
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)
        # 处理翻页
        # 1. 获取翻页链接
        # 2. yield scrapy.Request(第二页链接, callback=self.parse, dont_filter=True)\

    def parse_item(self, response):
        try:
            item = bzk_gwbzItem()
            item['name'] = response.css('#standard_name::text').extract_first().strip()
            item['code'] = response.css('#standard_code::text').extract_first().strip()
            item['status'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(1) > ul > li:nth-child(4) > span::text').extract_first().strip()
            item['committees'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(6) > ul > li:nth-child(6) > span::text').extract_first()
            item['approvalDate'] = ''
            item['implementationDate'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(1) > ul > li:nth-child(6) > span::text').extract_first()
            item['sourceWebsite'] = '中国标准在线服务网'
            item['ics'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(2) > ul > li:nth-child(1) > span::text').extract_first()
            item['pub_lang'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(1) > ul > li:nth-child(7) > span::text').extract_first()
            item['pub_organization'] = response.css(
                '#content > div.detailedinfo-main > div:nth-child(6) > ul > li:nth-child(8) > span::text').extract_first()
            item['replace'] = response.css("#a461::text").extract_first()
            item['replaced'] = response.css("#a461::text").extract_first()
            item['dept_host'] = ''
            item['scope'] = response.css(
                '#content > div.detailedinfo-top > div.stand-detail-description > div.detailedinfo-text::text').extract_first()
            item['link'] = response.meta['url']
            item['module_name'] = '标准库-国外标准'
            item['spider_name'] = 'gwbz'
            print("===========================>crawled one item" + response.request.url)
        except Exception as e:
            logging.error(self.name + " in parse_item: url=" + response.request.url + ", exception=" + e.__str__())
            logging.exception(e)
        yield item
