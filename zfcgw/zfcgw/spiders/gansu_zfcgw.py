# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy_splash import SplashRequest
from zfcgw.items import ztbkItem
from utils.tools.attachment import get_attachments,get_times
class GansuZfcgwSpider(scrapy.Spider):
    name = 'gansu_zfcgw'
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
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter'
        }

    def __init__(self, pagenum=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_pagenum = pagenum

    def start_requests(self):
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
          wait_for_element(splash, "input[name=button]")
          splash:runjs("submitSearch();")
          wait_for_element(splash, ".Expand_SearchSLisi a")
          splash:wait(1)
          return splash:html()
        end
        """
        try:
            contents = [
                {
                    'topic': 'zhcx',  # 综合查询
                    'url': 'http://www.ccgp-gansu.gov.cn/web/doSearchmxarticle.action'
                }
            ]
            for content in contents:
                yield SplashRequest(content['url'],
                                    endpoint='execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'url': content['url'],
                                    },
                                    callback=self.parse_page,
                                    meta=content)
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse_page(self, response):
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
          wait_for_element(splash, "input[name=button]")
          splash:runjs("submitSearch();")
          wait_for_element(splash, ".Expand_SearchSLisi a")
          splash:wait(1)
          splash:runjs("document.querySelector('.Expand_SearchSLisi').innerHTML = ''")
          js = string.format("JumpPage(%d)", args.pagenum)
          splash:evaljs(js)
          wait_for_element(splash, ".Expand_SearchSLisi a")
          splash:wait(1)
          return splash:html()
        end
        """
        page_count = int(self.parse_pagenum(response))
        try:
            for pagenum in range(page_count):
                url = response.meta['url']
                yield SplashRequest(url,
                                    endpoint='execute',
                                    args={
                                        'lua_source': script,
                                        'wait': 1,
                                        'pagenum': pagenum + 1,
                                        'url': url,
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
                return int(response.css('#total::attr(value)').extract_first().strip())
            return self.add_pagenum
        except Exception as e:
            logging.error(self.name + ": " + e.__str__())
            logging.exception(e)

    def parse(self, response):
        for href in response.css('.Expand_SearchSLisi a::attr(href)').extract():
            try:
                url = response.urljoin(href)
                result = {
                    'url': url
                }
                yield scrapy.Request(url, callback=self.parse_item, meta=result, dont_filter=True)
            except Exception as e:
                logging.error(self.name + ": " + e.__str__())
                logging.exception(e)

    def parse_item(self, response):
        try:
            appendix, appendix_name = get_attachments(response)
            title = response.css('.title::text').extract_first()
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
            else:
                category = '其他'
            item = ztbkItem()
            item['title'] = title
            item['content'] = response.css('#fontzoom').extract_first()
            item['appendix'] = appendix
            item['category'] = category
            item['time'] = response.css('.property span:nth-child(2)::text').extract_first().replace('发布时间：','')
            item['source'] = response.css('.property span:nth-child(1)::text').extract_first().replace('文章来源：','')
            item['website'] = '甘肃政府采购网'
            item['link'] = response.meta['url']
            item['type'] = '2'
            item['region'] = '甘肃省'
            item['appendix_name'] = appendix_name
            item['spider_name'] = 'gansu_zfcgw'
            item['txt'] = ''.join(response.css('#fontzoom *::text').extract())
            item['module_name'] = '甘肃-政府采购网'
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