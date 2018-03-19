# -*- coding: utf-8 -*-
import os.path as P

import mock
import pytest
import scrapy

from . import myspider


CURR_DIR = P.dirname(P.abspath(__file__))


TIK_NAMES = (
    'Александровск-Сахалинская',
    'Анивская',
    'Долинская',
    'Корсаковская',
    'Курильская',
    'Макаровская',
    'Невельская',
    'Ногликская',
    'Охинская',
    'Поронайская',
    'Северо-Курильская',
    'Смирныховская',
    'Томаринская',
    'Тымовская',
    'Углегорская',
    'Холмская',
    'Южно-Курильская',
    'Южно-Сахалинская городская',
    'Невельская судовая',
    'Холмская судовая'
)
assert len(TIK_NAMES) == 20

ROW_HEADERS = (
    'Сумма',
    'Число избирателей, включенных в список избирателей',
    'Число избирательных бюллетеней, полученных участковой избирательной комиссией',
    'Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно',
    'Число избирательных бюллетеней, выданных в помещении для голосования в день голосования',
    'Число избирательных бюллетеней, выданных вне помещения для голосования в день голосования',
    'Число погашенных избирательных бюллетеней',
    'Число избирательных бюллетеней в переносных ящиках для голосования',
    'Число бюллетеней в стационарных ящиках для голосования',
    'Число недействительных избирательных бюллетеней',
    'Число действительных избирательных бюллетеней',
    'Число утраченных избирательных бюллетеней',
    'Число избирательных бюллетеней, не учтенных при получении',
    '',
    'Бабурин Сергей Николаевич',
    'Грудинин Павел Николаевич',
    'Жириновский Владимир Вольфович',
    'Путин Владимир Владимирович',
    'Собчак Ксения Анатольевна',
    'Сурайкин Максим Александрович',
    'Титов Борис Юрьевич',
    'Явлинский Григорий Алексеевич',
)

UIK_NAMES = tuple("УИК №%d" % x for x in range(1, 15) if x != 4)


def mock_response(filename):
    """Let's pretend we have a scrapy Response object for testing."""
    response = mock.Mock()
    response.url = P.join(CURR_DIR, filename)
    with open(response.url, "rb") as fin:
        #
        # Downloading the files with wget serves them with their original encoding.
        # Downloading them with Scrapy yields UTF-8 files for some reason.
        # Make sure the result of this function is UTF-8.
        #
        body = fin.read().decode('cp1251').encode('utf-8')
        response.body = body
        response.selector = scrapy.Selector(text=response.body)
    return response


def test_parse_results_regional_ik():
    response = mock_response("regional_ik_results.html")

    result = myspider.parse_voting_summary_table(response, data_type=myspider.RESULTS_TIK)
    assert result["data_type"] == myspider.RESULTS_TIK
    assert result["url"] == response.url
    assert "timestamp" in result

    assert result["region"] == "Сахалинская область"

    expected_row_headers = list(ROW_HEADERS)
    expected_row_headers.pop(0)
    assert result['row_headers'] == expected_row_headers

    # Total value + a value for each
    column_headers = result["column_headers"]
    assert len(column_headers) == 9 + 1

    for i, _ in enumerate(row_headers):
        assert len(result["data"][i]) == len(column_headers)

    # Test some individual values
    assert result["data"][0][0] == 342734
    assert result["data"][0][1] == 12021


def test_parse_results_territorial_ik():
    response = mock_response("territorial_ik_results.html")
    result = myspider.parse_voting_summary_table(response, data_type=myspider.RESULTS_UIK)

    assert result["region"] == "Сахалинская область"
    assert result["territory"] == "Александровск-Сахалинская"

    expected_row_headers = list(ROW_HEADERS)
    expected_row_headers.pop(0)
    assert result["row_headers"] == expected_row_headers
    assert result["column_headers"] == expected


def test_parse_turnout_table():
    response = mock_response("regional_ik_turnout.html")
    result = myspider.parse_turnout_table(response, data_type=myspider.TURNOUT_TIK)
    print(result)

    assert result["region"] == "Сахалинская область"
    assert result["url"] == response.url
    assert result["data_type"] == myspider.TURNOUT_TIK

    row_headers = result["row_headers"]
    print(row_headers)
    assert len(row_headers) == 21

    col_headers = result["column_headers"]
    assert len(col_headers) == 4

    assert result["data"][0][0] == 11.52
    assert result["data"][1][1] == 27.70
    assert result["data"][2][2] == 53.39
    assert result["data"][3][3] == 49.95

    assert "md5" in result

    assert result["data_type"] == myspider.TURNOUT_TIK


def test_parse_turnout_table_uik():
    response = mock_response("territorial_ik_uik_turnout.html")
    result = myspider.parse_turnout_table(response, data_type=myspider.TURNOUT_UIK)
    print(result)

    assert result["region"] == "Сахалинская область"
    assert result["territory"] == "Александровск-Сахалинская"

    assert len(result["row_headers"]) == 14
    assert len(result["column_headers"]) == 4

    assert len(result["data"]) == len(result["row_headers"])
    assert len(result["data"][0]) == len(result["column_headers"])

    assert result["data_type"] == myspider.TURNOUT_UIK


def test_regex_final():
    text = "Сводная таблица итогов голосования по федеральному избирательному округу"
    assert myspider.RESULTS_REGEX.search(text) is not None


def test_regex_preliminary():
    text = "Сводная таблица предварительных итогов голосования по федеральному избирательному округу"  # noqa
    assert myspider.RESULTS_REGEX.search(text) is not None


def test_regex_turnout():
    text = "Предварительные сведения об участии избирателей в выборах"
    assert myspider.TURNOUT_REGEX.search(text) is not None


def test_get_uik_link():
    response = mock_response("territorial_ik_intermediate.html")
    uik_link = myspider.get_uik_link(response.selector)
    assert uik_link is not None


def test_xpaths_turnout_tik():
    response = mock_response("regional_ik_turnout.html")
    tik_links = response.selector.xpath(myspider.TURNOUT_TIK_XPATH)
    tik_names = [myspider.join(tl.xpath(".//text()").extract()) for tl in tik_links]
    assert tik_names == list(TIK_NAMES)


def test_xpaths_tik_names():
    response = mock_response("regional_ik_results.html")
    tik_links = response.selector.xpath(myspider.TIK_XPATH)
    tik_names = [myspider.join(tl.xpath(".//text()").extract()) for tl in tik_links]
    assert tik_names == list(TIK_NAMES)


def test_xpaths_results_tik():
    """Are the xpaths for the regional IK results page specified correctly?"""
    response = mock_response('regional_ik_results.html')
    root = response.selector

    expected_row_headers = list(ROW_HEADERS)
    expected_column_headers = list(TIK_NAMES)

    xpaths = myspider.XPATHS[myspider.RESULTS_TIK]
    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    column_headers = myspider.parse_table_headers(root, xpaths["col_header"])

    total = myspider.parse_table_cell(root, xpaths['total'], 1, 3)
    cell = myspider.parse_table_cell(root, xpaths['cell'], 1, 1)

    assert row_headers == expected_row_headers
    assert column_headers == expected_column_headers
    assert total == '374297'
    assert cell == '9051'


def test_xpaths_result_territorial():
    """Are the xpaths for the territorial IK results page specified correctly?"""
    response = mock_response('territorial_ik_results.html')
    root = response.selector

    expected_row_headers = list(ROW_HEADERS)
    expected_column_headers = list(UIK_NAMES)

    xpaths = myspider.XPATHS[myspider.RESULTS_UIK]

    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    column_headers = myspider.parse_table_headers(root, xpaths["col_header"])

    total = myspider.parse_table_cell(root, xpaths['total'], 1, 3)
    cell = myspider.parse_table_cell(root, xpaths['cell'], 1, 1)

    assert row_headers == expected_row_headers
    assert column_headers == expected_column_headers
    assert total == '9051'
    assert cell == '173'


def test_xpaths_turnout_regional():
    """Are the xpaths for the regional IK turnout page specified correctly?"""
    response = mock_response('regional_ik_turnout.html')
    root = response.selector

    expected_row_headers = list(TIK_NAMES)
    expected_row_headers.insert(0, 'Наименование ИК')
    expected_row_headers.insert(1, '10.00')
    expected_row_headers.insert(2, 'ВСЕГО, в том числе')

    xpaths = myspider.XPATHS[myspider.TURNOUT_TIK]

    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    # column_headers = myspider.parse_table_headers(root, xpaths["col_header"])
    cell = myspider.parse_table_cell(root, xpaths['cell'], 3, 3)

    assert row_headers == expected_row_headers
    # assert column_headers == expected_column_headers
    assert cell == '9.57%'


def test_xpaths_turnout_territorial():
    """Are the xpaths for the territorial IK turnout page specified correctly?"""
    response = mock_response('territorial_ik_turnout.html')
    root = response.selector

    expected_row_headers = ['Наименование ИК', '10.00', 'ВСЕГО, в том числе']
    expected_row_headers += UIK_NAMES

    xpaths = myspider.XPATHS[myspider.TURNOUT_UIK]

    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    # column_headers = myspider.parse_table_headers(root, xpaths["col_header"])
    cell = myspider.parse_table_cell(root, xpaths['cell'], 3, 3)

    assert row_headers == expected_row_headers
    # assert column_headers == expected_column_headers
    assert cell == '49.71%'


def test_cb_central_ik_home():
    """Should parse a link to each regional IK."""
    response = mock_response('central_ik_home.html')
    things = list(myspider.cb_central_ik_home(response))

    if myspider.TEST:
        first = things[0]
        assert first.method == 'GET'
    else:
        assert len(things) == 87
        assert things[0].method == 'GET'


def test_cb_region_ik_home():
    """Should parse two links: turnout and election results."""
    response = mock_response('regional_ik_home.html')
    things = list(myspider.cb_region_ik_home(response))
    assert len(things) == 2
    assert [thing.method for thing in things] == ['GET', 'GET']


def test_cb_region_ik_results():
    """Should parse multiple links and summary."""
    response = mock_response('regional_ik_results.html')
    things = list(myspider.cb_region_ik_results(response))
    #
    # The extra +1 is for the results extracted from the page
    #
    assert len(things) == 1 + len(TIK_NAMES)
    assert [thing.method for thing in things[:-1]] == ['GET'] * len(TIK_NAMES)
    assert 'column_headers' in things[-1]
