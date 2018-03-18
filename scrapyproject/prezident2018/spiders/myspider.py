# -*- coding: utf-8 -*-
import re
import logging
import datetime
import hashlib

import pytz
import scrapy

LOGGER = logging.getLogger(__name__)

#
# Set to True to restrict the region to the first one (Adygea).
#
TEST = False

TOP_URL = ("http://www.vybory.izbirkom.ru/region/izbirkom?action=show&root_a=652000016"
           "&vrn=100100084849062&region=0&global=true&type=0&prver=0&pronetvd=null")
"""The URL to start the crawl at."""

TURNOUT_REGEX = re.compile(
    "Предварительные сведения об участии избирателей в выборах",
    re.IGNORECASE | re.UNICODE
)
RESULTS_REGEX = re.compile(
    "Сводная таблица (предварительных )?итогов голосования",
    re.IGNORECASE | re.UNICODE
)

#
# My understanding of the hierarchy is as follows.
# IK = electoral commission
# At the top you have the central IK (центральная избирательная комиссия).
# Below that is the region IK (окружная избирательная комиссия).
# Below that is the territory IK (территориальная избирательная комиссия).
# At the lowest level are the UIK (участковая избирательная коммиссия).
# The UIK are the actual polling stations.
#
# central -> region -> territory -> polling station
#

TIK_XPATH = '/html/body/table[2]/tr[4]/td/table[6]/tr/td[2]/div/table/tr[1]/td/nobr/a'  # noqa
"""Get the territorial electoral committee links."""

UIK_XPATH = "/html/body/table[2]/tr[2]/td/a"
"""Get the link to the UIK table from a TIK table."""

TURNOUT_TIK_XPATH = "/html/body/table[2]/tr[4]/td/table[4]/tr/td[2]/a"
"""Get the territorial electoral committee links for turnout pages."""

RESULTS_TIK = 'results_tik'
"""Election results for a specific territorial IK.

Represents an an average across multiple UIKs.
"""

RESULTS_UIK = 'results_uik'
"""Election results for a specific UIK (polling station)."""

TURNOUT_TIK = 'turnout_tik'
"""Turnout for a specific territorial IK.

Represents an average across multiple UIKs.
"""

TURNOUT_UIK = 'turnout_uik'
"""Turnout results for a specific UIK (polling station)."""

TURNOUT_TIMES = ["10:00", "12:00", "15:00", "18:00"]
"""Different times at which the turnout is reported."""

TURNOUT_COLUMNS = [3, 4, 5, 6]
"""Column indices for each of the times in TURNOUT_TIMES."""

SKIP_TURNOUT_ROWS = 2
"""Skip this many rows in the turnout table because they contain headers or junk."""

XPATHS = {
    RESULTS_TIK: {
        "row_header": "/html/body/table[2]/tr[4]/td/table[6]/tr/td[1]/table/tr/td[2]",
        "col_header": "/html/body/table[2]/tr[4]/td/table[6]/tr/td[2]/div/table/tr[1]/td",
        "total": '/html/body/table[2]/tr[4]/td/table[6]/tr/td[1]/table/tr[%d]/td[%d]/nobr/b/text()',  # noqa
        "cell": '/html/body/table[2]/tr[4]/td/table[6]/tr/td[2]/div/table/tr[%d]/td[%d]/nobr/b/text()',  # noqa
    },
    RESULTS_UIK: {
        'row_header': '/html/body/table[3]/tr[4]/td/table[6]/tr/td[1]/table/tr/td[2]',  # noqa
        'col_header': '/html/body/table[3]/tr[4]/td/table[6]/tr/td[2]/div/table/tr[1]/td',  # noqa
        'total': '/html/body/table[3]/tr[4]/td/table[6]/tr/td[1]/table/tr[%d]/td[%d]/nobr/b/text()',  # noqa
        'cell': '/html/body/table[3]/tr[4]/td/table[6]/tr/td[2]/div/table/tr[%d]/td[%d]/nobr/b/text()',  # noqa
    },
    TURNOUT_TIK: {
        'row_header': '/html/body/table[2]/tr[4]/td/table[4]/tr/td[2]',
        "cell": "/html/body/table[2]/tr[4]/td/table[4]/tr[%d]/td[%d]//text()"
    },
    TURNOUT_UIK: {
        "row_header": "/html/body/table[3]/tr[4]/td/table[4]/tr/td[2]",
        "cell": "/html/body/table[3]/tr[4]/td/table[4]/tr[%d]/td[%d]//text()"
    }
}
"""Xpaths for various parts of the table in its different incarnations.

It's trivial to get them from Chrome, but don't forget to strip /tbody parts of the Xpath.
Chrome appears to insert them by itself, since the original pages don't contain them.

The dictionary is keyed by what we're trying to parse.

/nobr/b/text() gives us the inner text.  It's helpful when the text spans multiple elements.
"""


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

BAD_COLUMN = -1
"""Sometimes values are just plain missing.  We can't really skip them,
since our stuff depends on the order of rows and columns, so let's have
a dummy value that we use to signify something went wrong."""
#
# noqa e.g. http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=772000043&tvd=27720001659726&vrn=100100067795849&prver=0&pronetvd=0&region=77&sub_region=77&type=453&vibid=27720001659726
# there's a blank row at the end of the column
#


#
# For the election results, the crawler visits the following pages:
#
# 1. Central IK page
#   * region IK page
#     * Territory IK page (intermediate page)
#       1. List of results for each UIK (one page per TIK)
#
# The "intermediate page" contains a summary of the results for the entire TIK,
# which we don't really need.  It also single link that we have to click
# through to get the results for each individual UIK.
#
# The process for crawling turnout results is similar.
#


class MySpider(scrapy.Spider):
    name = "myspider"
    allowed_domains = ["vybory.izbirkom.ru"]
    start_urls = (TOP_URL,)

    def parse(self, response):
        self.logger.debug("handling reponse from url: %r", response.url)
        for thing in cb_central_ik_home(response):
            yield thing


#
# function names that start with cb_ are callbacks.
# They accept a response object from Scrapy, and yield one or many of:
#
#   - scapy.Request objects to indicate what should be scraped
#   - dictionaries indicating scraped items
#


def cb_central_ik_home(response):
    """Handle the response of scraping the top-level page.

    The only useful information this page contains is links to the underlying
    IK pages for the same election.

    Yields requests to scrape underlying IK pages.
    """
    #
    # example url:
    #
    # http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=1&vrn=100100031793505&region=0&prver=0&pronetvd=null # noqa
    #
    LOGGER.debug("handling response from url: %r", response.url)

    for value in response.selector.xpath("//option/@value").extract():
        LOGGER.debug("extracted value: %r", value)
        yield scrapy.Request(value, callback=cb_region_ik_home)
        if TEST:
            break


def cb_region_ik_home(response):
    """Handle the response of scraping an region IK page (one level below the top page).

    This page contains three useful links:

        1. Turnout (at 10:00, 12:00, 15:00 and 18:00) for each territorial IK
        2. A summary table for the entire IK
        3. A slightly more detailed table showing data for each TIK

    Yields requests to scrape the above useful links 1 and 3.
    Doesn't bother with 2 because it can be derived from 3.
    """
    #
    # example url:
    #
    # http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=1000022&tvd=100100031793851&vrn=100100031793505&prver=0&pronetvd=null&region=0&sub_region=0&type=0&vibid=100100031793851 # noqa
    #
    LOGGER.debug("handling response from url: %r", response.url)

    callbacks = {RESULTS_REGEX: cb_region_ik_results, TURNOUT_REGEX: cb_region_ik_turnout}

    matched_regexes = set()

    for hyperlink in response.selector.xpath("//a"):
        text = join(hyperlink.xpath("./text()").extract())
        LOGGER.debug("text: %r", text)

        for regex, callback in callbacks.items():
            if regex.search(text):
                matched_regexes.add(regex)
                href = hyperlink.xpath("./@href").extract_first()
                LOGGER.debug("extracted href: %r", href)
                yield scrapy.Request(href, callback=callback)

    # Make sure we've got all the data for this region
    assert len(matched_regexes) == len(callbacks)


def cb_region_ik_results(response):
    """Handle the response of scaping a regional IK result page.

    This page contains several useful things:

        1. The overall results for the AIK, with figures for each underlying TIK
        2. Links to individual TIK

    Yields the results, and request to crawl each link in 2.
    """
    #
    # example url:
    #
    # http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1000022&tvd=100100031793851&vrn=100100031793505&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100031793851&type=227 # noqa
    #
    ik_links = response.selector.xpath(TIK_XPATH)
    for link in ik_links:
        href = link.xpath("./@href").extract_first()
        yield scrapy.Request(href, callback=cb_intermediate_page_results)
    yield parse_voting_summary_table(response, data_type=RESULTS_TIK)


def cb_intermediate_page_results(response):
    """Handle the response of scraping an TIK result page.

    The only interesting part here is a link to the list of UIKs under this TIK.
    """
    #
    # example url:
    #
    # http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=12000001&tvd=2012000191040&vrn=100100031793505&prver=0&pronetvd=null&region=0&sub_region=0&type=227&vibid=2012000191040 # noqa
    #
    uik_link = get_uik_link(response.selector)
    assert uik_link, "unable to get uik_link"
    yield scrapy.Request(uik_link, callback=cb_parse_results_table)


def get_uik_link(selector):
    """Get the link to the UIK results from an intermediate page."""
    #
    # Для просмотра данных по участковым избирательным комиссиям перейдите
    # на сайт избирательной комиссии субъекта Российской Федерации
    #
    uik_link = selector.xpath(UIK_XPATH)
    return uik_link.xpath("./@href").extract_first()


def cb_parse_results_table(response):
    """Callback to handle the response of scraping a TIK result page.

    This page contains what we actually want: the results for each UIK under the TIK.
    """
    #
    # example url:
    #
    # http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=12000001&tvd=2012000191040&vrn=100100031793505&prver=0&pronetvd=null&region=1&sub_region=1&type=227&vibid=2012000191040
    #
    yield parse_voting_summary_table(response, data_type=RESULTS_UIK)


def cb_region_ik_turnout(response):
    ik_links = response.selector.xpath(TURNOUT_TIK_XPATH)
    LOGGER.debug("len(ik_links): %d", len(ik_links))
    for link in ik_links:
        href = link.xpath("./@href").extract_first()
        yield scrapy.Request(href, callback=cb_intermediate_page_turnout)
    yield parse_turnout_table(response, data_type=TURNOUT_TIK)


def cb_intermediate_page_turnout(response):
    uik_link = get_uik_link(response.selector)
    LOGGER.debug("uik_link: %r", uik_link)
    if uik_link:
        yield scrapy.Request(uik_link, callback=cb_parse_turnout_table_uik)


def cb_parse_turnout_table_uik(response):
    LOGGER.debug("url: %r", response.url)
    yield parse_turnout_table(response, data_type=TURNOUT_UIK)


def join(list_of_strings):
    return " ".join(list_of_strings).strip()


def now():
    """Return the current UTC datetime (time-zone aware)."""
    #
    # http://stackoverflow.com/questions/2331592/datetime-datetime-utcnow-why-no-tzinfo
    #
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


def get_name(root):
    """Return the electorate region, committee number and name."""
    region = join(root.xpath("/html/body/table[2]/tr[1]/td/a[2]/text()").extract())
    region_ik = join(root.xpath("/html/body/table[2]/tr[1]/td/a[3]/text()").extract())
    #
    # Наименование избирательной комиссии
    #
    region_ik_long = join(
        root.xpath("/html/body/table[2]/tr[4]/td/table[3]/tr[2]/td[2]/text()").extract()
    )
    del root
    return locals()


def get_name_uik(root):
    region = join(root.xpath("/html/body/table[3]/tr[1]/td/a[1]/text()").extract())
    region_ik = join(root.xpath("/html/body/table[3]/tr[1]/td/a[2]/text()").extract())
    territory_ik = join(root.xpath("/html/body/table[3]/tr[1]/td/a[3]/text()").extract())
    del root
    return locals()


def myfloat(value):
    try:
        return float(value)
    except ValueError:
        return BAD_COLUMN


def parse_table_headers(root, xpath):
    return [join(td.xpath(".//text()").extract()) for td in root.xpath(xpath)]


def parse_table_cell(root, xpath_formatstr, row_number, column_number):
    return join(root.xpath(xpath_formatstr % (row_number + 1, column_number)).extract())


def parse_voting_summary_table(response, data_type=RESULTS_TIK):
    """Parse the voting summary table.  Returns a dict."""
    if data_type not in (RESULTS_TIK, RESULTS_UIK):
        raise ValueError('bad data_type: %r', data_type)

    root = response.selector
    url = response.url
    md5 = hashlib.md5(response.body).hexdigest()

    if data_type == RESULTS_UIK:
        result = get_name_uik(root)
    else:
        result = get_name(root)

    LOGGER.debug("result: %r", result)

    xpaths = XPATHS[data_type]
    row_headers = parse_table_headers(root, xpaths["row_header"])
    LOGGER.debug("row_headers: %r", row_headers)

    column_headers = parse_table_headers(root, xpaths["col_header"])
    LOGGER.debug("column_headers: %r", column_headers)

    stats_rows = list(range(FIRST_STAT, LAST_STAT))
    votes_rows = list(range(FIRST_CANDIDATE, len(row_headers)))
    important_rows = stats_rows + votes_rows

    rows = []
    for row_number in important_rows:
        #
        # xpath rows use 1-based indexing
        #
        total_value = parse_table_cell(root, xpaths["total"], row_number, 3)
        LOGGER.debug("row: %r total_value: %r", row_number, total_value)

        columns = [myfloat(total_value)]

        for col_number, _ in enumerate(column_headers, 1):
            value = parse_table_cell(root, xpaths["cell"], row_number, col_number)
            columns.append(myfloat(value))

        rows.append(columns)

    row_headers = [rh for (i, rh) in enumerate(row_headers) if i in important_rows]
    column_headers.insert(0, "Сумма")

    result.update(
        {
            "row_headers": row_headers, "column_headers": column_headers,
            "data": rows, "data_type": data_type,
            "timestamp": now().isoformat(), "url": url, "md5": md5
        }
    )
    return result


def parse_turnout_table(response, data_type=TURNOUT_TIK):
    """Pass the voting turnout table."""
    if data_type not in (TURNOUT_TIK, TURNOUT_UIK):
        raise ValueError('bad data_type: %r', data_type)

    LOGGER.debug('data_type: %r', data_type)

    root = response.selector
    url = response.url
    md5 = hashlib.md5(response.body).hexdigest()

    if data_type == TURNOUT_UIK:
        result = get_name_uik(root)
    else:
        result = get_name(root)

    LOGGER.debug("result: %r", result)

    xpaths = XPATHS[data_type]
    row_headers = parse_table_headers(root, xpaths["row_header"])
    LOGGER.debug("row_headers: %r", row_headers)

    important_rows = range(SKIP_TURNOUT_ROWS, len(row_headers))

    rows = []
    for row_num in important_rows:
        cols = [parse_table_cell(root, xpaths['cell'], row_num, col_num)
                for col_num in TURNOUT_COLUMNS]
        rows.append([myfloat(c.replace('%', '')) for c in cols])

    LOGGER.debug('rows: %r', rows)

    result.update(
        {
            "md5": md5, "url": url, "data_type": data_type,
            "timestamp": now().isoformat(), "row_headers": row_headers[2:],
            "column_headers": TURNOUT_TIMES, "data": rows
        }
    )
    return result


def main():
    import argparse
    import requests
    import mock

    parser = argparse.ArgumentParser()
    parser.add_argument('callback')
    parser.add_argument('url')
    args = parser.parse_args()

    if not args.callback.startswith('cb_'):
        parser.error('callback name should start with cb_')

    callback = globals()[args.callback]
    text = requests.get(args.url).text.encode('utf-8')
    response = mock.Mock(url=args.url, body=text, selector=scrapy.Selector(text=text))
    for result in callback(response):
        print(result)


if __name__ == '__main__':
    main()
