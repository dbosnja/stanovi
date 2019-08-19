import re

from math import ceil

from scrapy.http import Request
from scrapy.spiders import Spider
from scrapy.mail import MailSender

class Njuskalo(Spider):
    name = 'njuskalo'
    allowed_domains = ['njuskalo.hr']
    # around 5K flats so far
    start_urls = [
        'https://www.njuskalo.hr/iznajmljivanje-kuca/zagreb',
        'https://www.njuskalo.hr/iznajmljivanje-stanova/zagreb',
        'https://www.njuskalo.hr/iznajmljivanje-soba/zagreb',
    ]
    PAGE_SIZE = 25
    flat_ad_template_url = "{response_url}?page={page_index}"
    # user's email credentials: DO NOT PUSH ON GITHUB WITH REAL DATA!!!
    user_mail = '@gmail.com'
    user_pass = ''
    # custom part for flat preferences:
    flat_price_range = [800.0, 2000.0]  # best to contain float type elements(in kunas!)
    flat_size_range = [30.0, 90.0]  # best to contain float type elements(in m2)

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
                    './article/div[@class="entity-thumbnail"]/a/@href').extract_first()
                ))
                self.send_mail(flat_uri)

    def is_match(self, flat_price, flat_size):
        return (flat_price >= min(self.flat_price_range) and flat_price <= max(self.flat_price_range) ) and \
               (flat_size >= min(self.flat_size_range) and  flat_size <= max(self.flat_size_range))

    def send_mail(self, flat_uri):
        # only for gmail smtps servers, read here for more: https://www.quora.com/What-is-SMTP-Host
        # check here for TLS vs SSL: http://www.smtp-gmail.com/
        # probably you will have to enable "Access for less secure apps"(on gmail host) for this to work
        mailer = MailSender(
            smtphost='smtp.gmail.com',
            mailfrom='scrapy_bot',
            smtpuser=self.user_mail,
            smtppass=self.user_pass,
            smtpssl=True,
            smtpport=465
        )
        mailer.send(
            to=self.user_mail,
            subject='detektiran potencijalan stan',
            body='robot je prepoznao sljedeci stan kao potencijalan:\n'+flat_uri
        )
