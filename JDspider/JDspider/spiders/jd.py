# -*- coding: utf-8 -*-
import json

import scrapy

from JDspider.JDspider.items import BookItem


class JdSpider(scrapy.Spider):
    name = 'jd'
    allowed_domains = ['jd.com']
    start_urls = ['https://book.jd.com/booksort.html']

    redis_key = "book:jd:start_url"

    def parse(self, response):
        dt_list = response.xpath('//div[@class="mc"]/dl/dt')
        dd_list = response.xpath('//div[@class="mc"]/dl/dd')

        cat_1_titles = dt_list.xpath('.//a/text()').extract()

        for cat_1_title,dd in zip(cat_1_titles,dd_list):
            cat_2_titles = dd.xpath('.//a/text()').extract()
            cat_2_hrefs = dd.xpath('.//a/@href').extract()


            for cat_2_title,cat_2_href in zip(cat_2_titles,cat_2_hrefs):
                print(cat_1_title,'----->',cat_2_title,'---->',cat_2_href)


                yield scrapy.Request(
                    url='https:'+cat_2_href,
                    meta={
                        'cat_1':cat_1_title,
                        'cat-2':cat_2_title
                    },
                    callback=self.parse_product_list
                )

        pass

    def parse_product_list(self, response):

        li_list = response.xpath('//li[@class="gl-item"]')
        sku_list = []

        items = []
        for li in li_list:
            item = {}
            item["name"] = li.xpath('.//div[@class="p-name"]/a/em/text()').extract_first().strip()
            data_sku = li.xpath('./div/@data-sku').extract_first()
            if data_sku is not None:
                item["price_key"] = "J_" + data_sku
                items.append(item)
                sku_list.append(item["price_key"])

        sku_list_string = ",".join(sku_list)
        # 发送获取价格的请求

        yield scrapy.Request(
            url="https://p.3.cn/prices/mgets?skuIds=" + sku_list_string,
            callback=self.parse_prices,
            meta={
                "items": items
            }
        )

    def parse_prices(self, response):

        print("*" * 100)
        items = response.meta["items"]
        prices = json.loads(response.body.decode('utf-8'))

        # 问题
        # items 列表
        '''
        [
            {
                "name":"xxx",
                "price_key":"J_xxxx",
            },
            {
                "name":"xxx",
                "price_key":"J_xxxx",
            }
        ]
        '''

        # prices 列表
        '''
        [
            {
                "op": "55.80",
                "m": "93.00",
                "id": "J_11757834",
                "p": "55.80"
            },
            {
                "op": "55.80",
                "m": "93.00",
                "id": "J_11757834",
                "p": "55.80"
            }
        ]

        转换后
        {
            "J_11757834":{
                "op": "55.80",
                "m": "93.00",
                "id": "J_11757834",
                "p": "55.80"
            },
            "J_11757834":{
                "op": "55.80",
                "m": "93.00",
                "id": "J_11757834",
                "p": "55.80"
            }
        }
        '''

        prices_dict = dict([[price["id"], price] for price in prices])

        for item in items:
            price_dict = prices_dict[item["price_key"]]
            if price_dict is not None:
                price = price_dict["op"]
                bookItem = BookItem()
                bookItem["name"] = item["name"]
                bookItem["price"] = price
                yield bookItem
