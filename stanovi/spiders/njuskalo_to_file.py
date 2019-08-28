import re

from math import ceil
from datetime import datetime

from scrapy.http import Request
from scrapy.spiders import Spider

class Njuskalo(Spider):
    name = 'njuskalo_to_file'
    allowed_domains = ['njuskalo.hr']
    # around 5K flats so far
    start_urls = [
        'https://www.njuskalo.hr/iznajmljivanje-kuca/zagreb',
        'https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb',
        'https://www.njuskalo.hr/iznajmljivanje-soba/zagreb',
    ]

    PAGE_SIZE = 25
    flat_cnt = 0
    datetime = None
    file_name = None
    flat_ad_template_url = "{response_url}?page={page_index}"

    # custom part for flat preferences:
    flat_price_range = [800.0, 4000.0]  # best to contain float type elements(in kunas!)
    flat_size_range = [30.0, 90.0]  # best to contain float type elements(in m2)

    def __init__(self):
        super(Spider, self).__init__()
        self.datetime = "{}".format(datetime.now().isoformat())
        self.file_name = "pot_stanovi_{datetime}_s_out".format(datetime=self.datetime)

    def parse(self, response):
        total_page_number = self.get_total_page_number(response)
        for page_index in range(1, total_page_number + 1):
            yield Request(
                url=self.flat_ad_template_url.format(response_url=response.url, page_index=page_index),
                callback=self.parse_flats_page
            )


    def get_total_page_number(self, response):
        number_of_ads = float(response.xpath('//strong[@class="entities-count"]/text()').extract_first())
        return int(ceil(number_of_ads / self.PAGE_SIZE))


    def parse_flats_page(self, response):
        flat_elements = response.xpath(
            '//div[contains(@class, "EntityList EntityList--Standard")]//ul[@class="EntityList-items"]/li'
        )
        for flat_element in flat_elements:
            flat_price = flat_element.xpath(
                './article/div[@class="entity-prices"]//strong[@class="price price--hrk"]/text()').extract()
            if not flat_price:
                continue
            flat_price = [float(x.strip(' ').replace('.', '')) for x in flat_price if x.strip(' ')][0]
            flat_description = flat_element.xpath(
                './article/div[@class="entity-description"]//div[@class="entity-description-main"]/text()').extract()
            if not flat_description:
                continue
            flat_description = ','.join([x.strip(' ') for x in flat_description if x.strip(' ')]).strip()
            flat_size = re.search(r'ina\s*:\s*(.+)', flat_description).group(1)
            flat_size = float(re.sub(r'm2', '', flat_size))
            if self.is_match(flat_price, flat_size):
                flat_uri = str(response.urljoin(flat_element.xpath(
                    './article/div[@class="entity-thumbnail"]/a/@href').extract_first()))
                self.flat_cnt += 1
                with open(self.file_name, 'a') as file:
                    line_to_write = "{cnt}. {flat_uri}\n".format(cnt=self.flat_cnt, flat_uri=flat_uri)
                    file.write(line_to_write)

    def is_match(self, flat_price, flat_size):
        return (flat_price >= min(self.flat_price_range) and flat_price <= max(self.flat_price_range) ) and \
               (flat_size >= min(self.flat_size_range) and  flat_size <= max(self.flat_size_range))
