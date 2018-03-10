# -*- coding: utf-8 -*-
import re
import logging
import datetime
import hashlib

import pytz
import scrapy

LOGGER = logging.getLogger(__name__)

TOP_URL = ("http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=1"
           "&vrn=100100031793505&region=0&prver=0&pronetvd=null")
"""The URL to start the crawl at.

Use the 2012 election for testing, for now.
"""

TURNOUT_REGEX = re.compile(
    "Предварительные сведения об участии избирателей в выборах",
    re.IGNORECASE | re.UNICODE
)
FEDERAL_RESULTS_REGEX = re.compile(
    "Сводная таблица (предварительных )?итогов голосования \
по федеральному избирательному округу",
    re.IGNORECASE | re.UNICODE
)
SINGLE_RESULTS_REGEX = re.compile(
    "Сводная таблица результатов выборов по \
одномандатному избирательному округу",
    re.IGNORECASE | re.UNICODE
)

#
# My understanding of the hierarchy is as follows.
# At the top you have the central IK (центральная избирательная комиссия).
# Below that is the area IK (окружная избирательная комиссия).
# Below that is the territory IK (территориальная избирательная комиссия).
# At the lowest level are the UIK (участковая избирательная коммиссия).
# The UIK are the actual polling stations.
#


#
# Set to True to restrict the region to the first one (Adygea).
#
TEST = True

TIK_XPATH = "/html/body/table[2]/tr[4]/td/table[5]/tr/td[2]/div/table/tr[1]/td/nobr/a"  # noqa
"""Get the territorial electoral committee links."""

UIK_XPATH = "/html/body/table[2]/tr[2]/td/a"
"""Get the link to the UIK table from a TIK table."""

TURNOUT_TIK_XPATH = "/html/body/table[2]/tr[4]/td/table[4]/tr/td[2]/a"
"""Get the territorial electoral committee links for turnout pages."""


def get_uik_link(selector):
    #
    # Для просмотра данных по участковым избирательным комиссиям перейдите
    # на сайт избирательной комиссии субъекта Российской Федерации
    #
    uik_link = selector.xpath(UIK_XPATH)
    return uik_link.xpath("./@href").extract_first()


class MyspiderSpider(scrapy.Spider):
    name = "myspider"
    allowed_domains = ["vybory.izbirkom.ru"]
    start_urls = (TOP_URL,)

    def parse(self, response):
        meth_name = "parse"
        self.logger.debug(
            "%s: handling reponse from url: %r", meth_name, response.url
        )

        for value in response.xpath("//option/@value").extract():
            self.logger.debug("%s: extracted value: %r", meth_name, value)
            yield scrapy.Request(value, callback=self.__parse_level1)
            if TEST:
                break

    def __parse_level1(self, response):
        meth_name = "__parse_level1"
        self.logger.debug(
            "%s: handling reponse from url: %r", meth_name, response.url
        )

        for value in response.xpath("//option/@value").extract():
            self.logger.debug("%s: extracted value: %r", meth_name, value)
            yield scrapy.Request(value, callback=self.__parse_level2)
            if TEST:
                break

    def __parse_level2(self, response):
        meth_name = "__parse_level2"
        self.logger.debug(
            "%s: handling reponse from url: %r", meth_name, response.url
        )

        callbacks = {
            FEDERAL_RESULTS_REGEX: self.__parse_federal_table,
            SINGLE_RESULTS_REGEX: self.__parse_single_table,
            TURNOUT_REGEX: self.__parse_turnout_table
        }
        matched_regexes = set()

        for hyperlink in response.xpath("//a"):
            text = join(hyperlink.xpath("./text()").extract())
            self.logger.debug("%s: text: %r", meth_name, text)

            for regex, callback in callbacks.items():
                if regex.search(text):
                    matched_regexes.add(regex)
                    href = hyperlink.xpath("./@href").extract_first()
                    self.logger.debug(
                        "%s: extracted href: %r", meth_name, href
                    )
                    yield scrapy.Request(href, callback=callback)

        # Make sure we've got all the data for this region
        assert len(matched_regexes) == 3

    def __parse_federal_table(self, response):
        #
        # Link to each individual electoral commission
        #
        ik_links = response.selector.xpath(TIK_XPATH)
        for link in ik_links:
            href = link.xpath("./@href").extract_first()
            yield scrapy.Request(href, callback=self.__parse_federal_table_ik)
        yield parse_voting_summary_table(response)

    def __parse_federal_table_ik(self, response):
        uik_link = get_uik_link(response.selector)
        assert uik_link, "unable to get_uik_link"
        yield scrapy.Request(uik_link, callback=self.__parse_federal_table_uik)

    def __parse_federal_table_uik(self, response):
        yield parse_voting_summary_table(response, data_type="federal_uik")

    def __parse_single_table(self, response):
        yield parse_voting_summary_table(response, data_type="single")

    def __parse_turnout_table(self, response):
        meth_name = "__parse_turnout_table"
        ik_links = response.selector.xpath(TURNOUT_TIK_XPATH)
        self.logger.debug("%s: len(ik_links): %d", meth_name, len(ik_links))
        for link in ik_links:
            href = link.xpath("./@href").extract_first()
            yield scrapy.Request(href, callback=self.__parse_turnout_table_ik)
        yield parse_turnout_table(response)

    def __parse_turnout_table_ik(self, response):
        meth_name = "__parse_turnout_table_ik"
        uik_link = get_uik_link(response.selector)
        self.logger.debug("%s: uik_link: %r", meth_name, uik_link)
        if uik_link:
            yield scrapy.Request(
                uik_link, callback=self.__parse_turnout_table_uik
            )

    def __parse_turnout_table_uik(self, response):
        meth_name = "__parse_turnout_table_uik"
        self.logger.debug("%s: url: %r", meth_name, response.url)
        yield parse_turnout_table(response, data_type="turnout_uik")


def join(list_of_strings):
    return " ".join(list_of_strings).strip()

#
# While the content and layouts for the federal and single-mandate pages are
# approximately the same, the xpath selectors are slightly different.
#
XPATHS = {
    "federal": {
        "row_header": "/html/body/table[2]/tr[4]/td/table[5]/tr/td[1]/table/tr/td[2]",  # noqa
        "col_header": "/html/body/table[2]/tr[4]/td/table[5]/tr/td[2]/div/table/tr[1]/td",  # noqa
        "total": "/html/body/table[2]/tr[4]/td/table[5]/tr/td[1]/table/tr[%d]/td[3]/nobr/b/text()",  # noqa
        "cell": "/html/body/table[2]/tr[4]/td/table[5]/tr/td[2]/div/table/tr[%d]/td[%d]/nobr/b/text()"  # noqa
    },
    "federal_uik": {
        "row_header": "/html/body/table[3]/tr[4]/td/table[5]/tr/td[1]/table/tr/td[2]",  # noqa
        "col_header": "/html/body/table[3]/tr[4]/td/table[5]/tr/td[2]/div/table/tr[1]/td",  # noqa
        "total": "/html/body/table[3]/tr[4]/td/table[5]/tr/td[1]/table/tr[%d]/td[3]/nobr/b/text()",  # noqa
        "cell": "/html/body/table[3]/tr[4]/td/table[5]/tr/td[2]/div/table/tr[%d]/td[%d]/nobr/b/text()"  # noqa
    },
    "single": {
        "row_header": "/html/body/table[2]/tr[4]/td/div/table/tr/td[1]/table/tr/td[2]",  # noqa
        "col_header": "/html/body/table[2]/tr[4]/td/div/table/tr/td[2]/div/table/tr[1]/td",  # noqa
        "total": "/html/body/table[2]/tr[4]/td/div/table/tr/td[1]/table/tr[%d]/td[3]/nobr/b/text()",  # noqa
        "cell": "/html/body/table[2]/tr[4]/td/div/table/tr/td[2]/div/table/tr[%d]/td[%d]/nobr/b/text()",  # noqa
    },
    "turnout": {
        "row_header": "/html/body/table[2]/tr[4]/td/table[4]/tr/td[2]",
        "cell": "/html/body/table[2]/tr[4]/td/table[4]/tr[%d]/td[%d]//text()"
    },
    "turnout_uik": {
        "row_header": "/html/body/table[3]/tr[4]/td/table[4]/tr/td[2]",
        "cell": "/html/body/table[3]/tr[4]/td/table[4]/tr[%d]/td[%d]//text()"
    }
}

#
# The 1st row is the header.
# The next rows are the stats.
# The 20th row is blank.
# The remaining rows are the candidates (parties and people in federal and
# single-mandate elections, respectively).
#
FIRST_STAT = 1
LAST_STAT = 19
FIRST_CANDIDATE = 20


def now():
    """Return the current UTC datetime (time-zone aware)."""
    #
    # http://stackoverflow.com/questions/2331592/datetime-datetime-utcnow-why-no-tzinfo
    #
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def get_name(root):
    """Return the electorate region, committee number and name."""
    region = join(
        root.xpath("/html/body/table[2]/tr[1]/td/a[2]/text()").extract()
    )
    area_ik = join(
        root.xpath("/html/body/table[2]/tr[1]/td/a[3]/text()").extract()
    )
    #
    # Наименование избирательной комиссии
    #
    area_ik_long = join(
        root.xpath(
            "/html/body/table[2]/tr[4]/td/table[3]/tr[2]/td[2]/text()"
        ).extract()
    )
    del root
    return locals()


def get_name_uik(root):
    region = join(
        root.xpath("/html/body/table[3]/tr[1]/td/a[1]/text()").extract()
    )
    area_ik = join(
        root.xpath("/html/body/table[3]/tr[1]/td/a[2]/text()").extract()
    )
    territory_ik = join(
        root.xpath("/html/body/table[3]/tr[1]/td/a[3]/text()").extract()
    )
    del root
    return locals()


BAD_COLUMN = -1
"""Sometimes values are just plain missing.  We can't really skip them,
since our stuff depends on the order of rows and columns, so let's have
a dummy value that we use to signify something went wrong."""
#
# noqa e.g. http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=772000043&tvd=27720001659726&vrn=100100067795849&prver=0&pronetvd=0&region=77&sub_region=77&type=453&vibid=27720001659726
# there's a blank row at the end of the column
#


def myfloat(value):
    try:
        return float(value)
    except ValueError:
        return BAD_COLUMN


def parse_voting_summary_table(response, data_type="federal"):
    """Parse the voting summary table.  Works for federal and single-mandate
    tables."""
    meth_name = "parse_voting_summary_table"

    root = response.selector
    url = response.url
    md5 = hashlib.md5(response.body).hexdigest()

    if data_type.endswith("_uik"):
        result = get_name_uik(root)
    else:
        result = get_name(root)

    logging.debug("%s: result: %r", meth_name, result)

    row_headers = [
        join(td.xpath(".//text()").extract())
        for td in root.xpath(XPATHS[data_type]["row_header"])
    ]
    logging.debug("%s: row_headers: %r", meth_name, row_headers)

    column_headers = [
        join(td.xpath(".//text()").extract())
        for td in root.xpath(XPATHS[data_type]["col_header"])
    ]
    logging.debug("%s: column_headers: %r", meth_name, column_headers)

    stats_rows = list(range(FIRST_STAT, LAST_STAT))
    votes_rows = list(range(FIRST_CANDIDATE, len(row_headers)))
    important_rows = stats_rows + votes_rows

    rows = []
    for row_number in important_rows:
        #
        # xpath rows use 1-based indexing
        #
        total_value = join(
            root.xpath(XPATHS[data_type]["total"] % (row_number + 1)).extract()
        )
        LOGGER.debug(
            "%s: row: %r total_value: %r", meth_name, row_number, total_value
        )

        columns = [myfloat(total_value)]

        for col_number, _ in enumerate(column_headers, 1):
            value = join(
                root.xpath(
                    XPATHS[data_type]["cell"] % (row_number + 1, col_number)
                ).extract()
            )
            columns.append(myfloat(value))

        rows.append(columns)

    row_headers = [
        rh for (i, rh) in enumerate(row_headers)
        if i in important_rows
    ]
    column_headers.insert(0, "Сумма")

    result.update(
        {
            "row_headers": row_headers, "column_headers": column_headers,
            "data": rows, "data_type": data_type,
            "timestamp": now().isoformat(), "url": url, "md5": md5
        }
    )
    return result


def parse_turnout_table(response, data_type="turnout"):
    """Pass the voting turnout table."""
    meth_name = "parse_turnout_table"

    root = response.selector
    url = response.url
    md5 = hashlib.md5(response.body).hexdigest()

    if data_type == "turnout_uik":
        result = get_name_uik(root)
    else:
        result = get_name(root)

    logging.debug("%s: result: %r", meth_name, result)

    row_headers = [
        join(row.xpath(".//text()").extract())
        for row in root.xpath(XPATHS[data_type]["row_header"])
    ]
    logging.debug("%s: row_headers: %r", meth_name, row_headers)

    important_rows = range(2, len(row_headers))
    important_cols = [2, 3, 4, 5]

    rows = []
    for row_num in important_rows:
        xp = XPATHS[data_type]["cell"]
        cols = [
            myfloat(
                join(
                    root.xpath(xp % (row_num + 1, col_num + 1)).extract()
                ).rstrip("%")
            )
            for col_num in important_cols
        ]
        rows.append(cols)

    result.update(
        {
            "md5": md5, "url": url, "data_type": data_type,
            "timestamp": now().isoformat(), "row_headers": row_headers[2:],
            "column_headers": ["10:00", "12:00", "15:00", "18:00"],
            "data": rows
        }
    )
    return result
