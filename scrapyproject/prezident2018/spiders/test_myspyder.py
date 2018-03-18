# -*- coding: utf-8 -*-
import os.path as P

import mock
import pytest
import scrapy

from . import myspider


CURR_DIR = P.dirname(P.abspath(__file__))


TIK_NAMES = [
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
]

ROW_HEADERS = [
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
    'Число полученных открепительных  удостоверений',
    'Число открепительных удостоверений, выданных избирателям на избирательном участке',
    'Число избирателей, проголосовавших по открепительным удостоверениям',
    'Число неиспользованных открепительных удостоверений',
    'Число открепительных удостоверений, выданных избирателям ТИК',
    'Число утраченных открепительных удостоверений',
    'Число утраченных избирательных бюллетеней',
    'Число избирательных бюллетеней, не учтенных при получении',
    '',
    'Жириновский Владимир Вольфович',
    'Зюганов Геннадий Андреевич',
    'Миронов Сергей Михайлович',
    'Прохоров Михаил Дмитриевич',
    'Путин Владимир Владимирович',
]

UIK_NAMES = ["УИК №%d" % x for x in range(1, 15) if x != 4]


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


@pytest.mark.skip(reason='results not available yet')
def test_parse_results_regional_ik():
    response = mock_response("regional_ik_results.html")

    result = myspider.parse_voting_summary_table(response, data_type=myspider.RESULTS_TIK)
    print(result)
    assert result["data_type"] == myspider.RESULTS_TIK
    assert result["url"] == response.url
    assert "timestamp" in result

    assert result["region"] == "Республика Адыгея (Адыгея)"
    #
    # Not available anymore?  We don't really need it anyway
    #
    # assert result["region_ik"] == "ОИК №1"
    # assert result["region_ik_long"] == "Республика Адыгея (Адыгея) - Адыгейский"
    assert result["region_ik_long"] == "Республика Адыгея (Адыгея)"

    #
    # 18 stats in total, 14 federal party candidates
    #
    # noqa Число избирательных бюллетеней, полученных участковой избирательной комиссией
    # noqa Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно
    # noqa Число избирательных бюллетеней, выданных в помещении для голосования в день голосования
    # noqa Число избирательных бюллетеней, выданных вне помещения для голосования в день голосования
    # noqa Число погашенных избирательных бюллетеней
    # noqa Число избирательных бюллетеней, содержащихся в переносных ящиках для голосования
    # noqa Число избирательных бюллетеней, содержащихся в стационарных ящиках для голосования
    # noqa Число недействительных избирательных бюллетеней
    # noqa Число действительных избирательных бюллетеней
    # noqa Число открепительных удостоверений, полученных участковой избирательной комиссией
    # noqa Число открепительных удостоверений, выданных на избирательном участке до дня голосования
    # noqa Число избирателей, проголосовавших по открепительным удостоверениям на избирательном участке
    # noqa Число погашенных неиспользованных открепительных удостоверений
    # noqa Число открепительных удостоверений, выданных избирателям территориальной избирательной комиссией
    # noqa Число утраченных открепительных удостоверений
    # noqa Число утраченных избирательных бюллетеней
    # noqa Число избирательных бюллетеней, не учтенных при получении
    #
    row_headers = result["row_headers"]
    assert len(row_headers) == 23

    # Total value + a value for each
    column_headers = result["column_headers"]
    assert len(column_headers) == 9 + 1

    for i, _ in enumerate(row_headers):
        assert len(result["data"][i]) == len(column_headers)

    # Test some individual values
    assert result["data"][0][0] == 342734
    assert result["data"][0][1] == 12021


@pytest.mark.skip(reason='results not available yet')
def test_parse_results_territorial_ik():
    response = mock_response("territorial_ik_results.html")
    result = myspider.parse_voting_summary_table(response, data_type=myspider.RESULTS_UIK)

    assert result["region"] == "Республика Адыгея (Адыгея)"
    # assert result["region_ik"] == "ОИК №1"
    assert result["region_ik"] == "Адыгейская"
    # assert result["territory_ik"] == "Адыгейская"

    assert len(result["row_headers"]) == 23

    expected = ['Сумма', 'УИК №1', 'УИК №2', 'УИК №3', 'УИК №4', 'УИК №5', 'УИК №6']
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

    assert result["data"][0][0] == 12.01
    assert result["data"][1][1] == None
    assert result["data"][2][2] == None
    assert result["data"][3][3] == None

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
    assert tik_names == TIK_NAMES


@pytest.mark.skip(reason='results not available yet')
def test_xpaths_tik_names():
    response = mock_response("regional_ik_results.html")
    tik_links = response.selector.xpath(myspider.TIK_XPATH)
    tik_names = [myspider.join(tl.xpath(".//text()").extract()) for tl in tik_links]
    assert tik_names == TIK_NAMES


@pytest.mark.skip(reason='results not available yet')
def test_xpaths_results_tik():
    """Are the xpaths for the regional IK results page specified correctly?"""
    response = mock_response('regional_ik_results.html')
    root = response.selector

    expected_row_headers = ROW_HEADERS
    expected_column_headers = TIK_NAMES

    xpaths = myspider.XPATHS[myspider.RESULTS_TIK]
    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    column_headers = myspider.parse_table_headers(root, xpaths["col_header"])

    total = myspider.parse_table_cell(root, xpaths['total'], 1, 3)
    cell = myspider.parse_table_cell(root, xpaths['cell'], 1, 1)

    assert row_headers == expected_row_headers
    assert column_headers == expected_column_headers
    assert total == '342734'
    assert cell == '12021'


@pytest.mark.skip(reason='results not available yet')
def test_xpaths_result_territorial():
    """Are the xpaths for the territorial IK results page specified correctly?"""
    response = mock_response('territorial_ik_results.html')
    root = response.selector

    expected_row_headers = ROW_HEADERS
    expected_column_headers = UIK_NAMES

    xpaths = myspider.XPATHS[myspider.RESULTS_UIK]

    row_headers = myspider.parse_table_headers(root, xpaths["row_header"])
    column_headers = myspider.parse_table_headers(root, xpaths["col_header"])

    total = myspider.parse_table_cell(root, xpaths['total'], 1, 3)
    cell = myspider.parse_table_cell(root, xpaths['cell'], 1, 1)

    assert row_headers == expected_row_headers
    assert column_headers == expected_column_headers
    assert total == '12021'
    assert cell == '2383'


def test_xpaths_turnout_regional():
    """Are the xpaths for the regional IK turnout page specified correctly?"""
    response = mock_response('regional_ik_turnout.html')
    root = response.selector

    expected_row_headers = TIK_NAMES
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
    assert len(things) == 10
    assert [thing.method for thing in things[:-1]] == ['GET'] * 9
    assert 'column_headers' in things[-1]


def test_cb_intermediate_page_results():
    pass
