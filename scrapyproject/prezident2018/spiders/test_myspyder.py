# -*- coding: utf-8 -*-
import unittest
import os.path as P

import mock
import scrapy

from . import myspider


CURR_DIR = P.dirname(P.abspath(__file__))


def mock_response(filename):
    """Let's pretend we have a scrapy Response object for testing."""
    response = mock.Mock()
    response.url = P.join(CURR_DIR, filename)
    with open(response.url, "rb") as fin:
        response.body = fin.read()
        response.selector = scrapy.Selector(text=response.body)
    return response


class ParseTest(unittest.TestCase):

    def test_federal_table(self):
        """Federal results should be parsed correctly."""
        response = mock_response("test_parse.html")

        result = myspider.parse_voting_summary_table(response)
        self.assertEquals(result["data_type"], "federal")
        self.assertEquals(result["url"], response.url)
        self.assertTrue("timestamp" in result)

        self.assertEquals(result["region"], "Республика Адыгея (Адыгея)")
        self.assertEquals(result["area_ik"], "ОИК №1")
        self.assertEquals(
            result["area_ik_long"], "Республика Адыгея (Адыгея) - Адыгейский"
        )
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
        self.assertEquals(len(row_headers), 32)

        # Total value + a value for each station
        column_headers = result["column_headers"]
        self.assertEquals(len(column_headers), 9 + 1)

        for i, _ in enumerate(row_headers):
            self.assertEquals(len(result["data"][i]), len(column_headers))

        # Test some individual values
        self.assertEquals(result["data"][0][0], 339685)
        self.assertEquals(result["data"][0][1], 11932)

    def test_federal_uik(self):
        response = mock_response("test_parse_federal_uik.html")
        result = myspider.parse_voting_summary_table(response, "federal_uik")

        self.assertEquals(result["region"], "Республика Адыгея (Адыгея)")
        self.assertEquals(result["area_ik"], "ОИК №1")
        self.assertEquals(result["territory_ik"], "Адыгейская")

        self.assertEqual(len(result["row_headers"]), 32)
        self.assertEqual(
            result["column_headers"],
            [
                'Сумма', 'УИК №1', 'УИК №2', 'УИК №3', 'УИК №4',
                'УИК №5', 'УИК №6'
            ]
        )

    def test_single_table(self):
        """Single-mandate results should be parsed correctly."""
        response = mock_response("test_parse_single.html")

        result = myspider.parse_voting_summary_table(response, "single")

        self.assertEquals(result["region"], "Республика Адыгея (Адыгея)")
        self.assertEquals(result["area_ik"], "ОИК №1")
        self.assertEquals(
            result["area_ik_long"], "Республика Адыгея (Адыгея) - Адыгейский"
        )

        self.assertEquals(result["data_type"], "single")
        self.assertEquals(result["url"], response.url)

        row_headers = result["row_headers"]
        self.assertEquals(len(row_headers), 25)

        # Total value + a value for each station
        column_headers = result["column_headers"]
        self.assertEquals(len(column_headers), 9 + 1)

        for i, _ in enumerate(row_headers):
            self.assertEquals(len(result["data"][i]), len(column_headers))

        # Test some individual values
        self.assertEquals(result["data"][0][0], 339544)
        self.assertEquals(result["data"][0][1], 11932)

        self.assertTrue("md5" in result)


class ParseTurnoutTableTest(unittest.TestCase):

    def test(self):
        """Turnout results should be parsed correctly."""
        response = mock_response("test_parse_turnout.html")
        result = myspider.parse_turnout_table(response)

        self.assertEquals(result["region"], "Республика Адыгея (Адыгея)")
        #
        # The turnout pages don't contain the full station name, just the
        # number
        #
        self.assertEquals(result["area_ik"], "ОИК №1")
        self.assertEqual(result["url"], response.url)
        self.assertEqual(result["data_type"], "turnout")

        row_headers = result["row_headers"]
        print(row_headers)
        self.assertEqual(len(row_headers), 10)

        col_headers = result["column_headers"]
        self.assertEqual(len(col_headers), 4)

        self.assertEqual(result["data"][0][0], 7.04)
        self.assertEqual(result["data"][1][1], 16.64)
        self.assertEqual(result["data"][2][2], 29.56)
        self.assertEqual(result["data"][3][3], 60.29)

        self.assertTrue("md5" in result)

        self.assertEqual(result["data_type"], "turnout")

    def test_uik(self):
        response = mock_response("test_parse_turnout_uik.html")
        result = myspider.parse_turnout_table(response, "turnout_uik")

        self.assertEquals(result["region"], "город Москва")
        self.assertEquals(result["area_ik"], "ОИК №196")
        self.assertEquals(result["territory_ik"], "район Богородское")

        self.assertEqual(len(result["row_headers"]), 34)
        self.assertEqual(len(result["column_headers"]), 4)

        self.assertEqual(len(result["data"]), len(result["row_headers"]))
        self.assertEqual(len(result["data"][0]), len(result["column_headers"]))

        self.assertEqual(result["data_type"], "turnout_uik")

    def test_uik2(self):
        response = mock_response("test_parse_turnout_uik2.html")
        result = myspider.parse_turnout_table(response, "turnout_uik")

        self.assertEquals(result["region"], "Республика Адыгея (Адыгея)")
        self.assertEquals(result["area_ik"], "ОИК №1")

        self.assertEqual(len(result["row_headers"]), 7)
        self.assertEqual(len(result["column_headers"]), 4)

        self.assertEqual(len(result["data"]), len(result["row_headers"]))
        self.assertEqual(len(result["data"][0]), len(result["column_headers"]))

        self.assertEqual(result["data_type"], "turnout_uik")


class RegexTest(unittest.TestCase):

    def test_final(self):
        text = "Сводная таблица итогов голосования по федеральному \
избирательному округу"
        self.assertIsNotNone(myspider.FEDERAL_RESULTS_REGEX.search(text))

    def test_preliminary(self):
        text = "Сводная таблица предварительных итогов голосования \
по федеральному избирательному округу"
        self.assertIsNotNone(myspider.FEDERAL_RESULTS_REGEX.search(text))

    def test_single(self):
        text = "Сводная таблица результатов выборов по одномандатному \
избирательному округу"
        self.assertIsNotNone(myspider.SINGLE_RESULTS_REGEX.search(text))

    def test_turnout(self):
        text = "Предварительные сведения об участии избирателей в выборах"
        self.assertIsNotNone(myspider.TURNOUT_REGEX.search(text))


_TIK_NAMES = [
    "Адыгейская", "Гиагинская", "Кошехабльская",
    "Красногвардейская", "Майкопская", "Майкопская городская",
    "Тахтамукайская", "Теучежская", "Шовгеновская"
]


class XpathTest(unittest.TestCase):

    def test_tik(self):
        response = mock_response("test_parse.html")
        tik_links = response.selector.xpath(myspider.TIK_XPATH)
        tik_names = [myspider.join(tl.xpath(".//text()").extract()) for tl in tik_links]
        self.assertEqual(tik_names, _TIK_NAMES)

    def test_uik(self):
        response = mock_response("test_parse_tik.html")
        uik_link = myspider.get_uik_link(response.selector)
        self.assertIsNotNone(uik_link)

    def test_turnout_tik(self):
        response = mock_response("test_parse_turnout.html")
        tik_links = response.selector.xpath(myspider.TURNOUT_TIK_XPATH)
        tik_names = [myspider.join(tl.xpath(".//text()").extract()) for tl in tik_links]
        self.assertEqual(tik_names, _TIK_NAMES)
