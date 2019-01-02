"""
Function AnalystenMeinungen(isin As String, zeile As Long, quellZeile As Long, shA As Worksheet, sh As Worksheet)
    'Holt die Anzahl der Analysten und deren Meinung, trägt sie ins Ziel-Bewertungsblatt in die Zeile zur ISIN ein.
    'benutzt dazu de.4-traders.com

    'Parameter:     isin    zu dieser ISIN werden die Daten geholt
    '               zeile   in diese Zeile des Bewertungsblattes werden die Daten geschrieben
    '               quellZeile  in dieser Zeile des Tabellenblattes "Aktien" stehen benötigte Hilfsdaten zur Aktie (URL-Teile für die Abfragen usw.)
    '               shA     Tabellenblatt "Aktien"
    '               sh      Ziel-Bewertungsblatt

    'wird verwendet in DatenZurISINHolen

    Const URL_ANFANG = "http://de.4-traders.com/"
    Const URL_ENDE = "/analystenerwartungen/"

    Call LeereZelle(sh, zeile, SPALTE_ANALYSTENANZAHL)
    Call LeereZelle(sh, zeile, SPALTE_ANALYSTENMEINUNG)

    'Internet-Seite laden
    urlTeil = shA.Cells(quellZeile, SPALTE_4TRADERS).Value   'URL-Teil für 4-traders
    If (Len(urlTeil) > 1) And (Right(urlTeil, 1) = "/") Then    'in früherer Aktienliste wurde diese Angabe mit / abgeschlossen, jetzt egal
        urlTeil = left(urlTeil, Len(urlTeil) - 1)
    End If
    If urlTeil = "" Then
        Exit Function
    End If
    url = URL_ANFANG + urlTeil + URL_ENDE

    If Not LadeURLHTTP(url, antwort, True, doc) Then

        Call StatusMeldung(zeile, sh, "Lade-F.", url, STATUS_FEHLER)

    Else

        ladezeit = Format(Now, "dd.mm.yyyy, hh:nn:ss")

        'Daten extrahieren und ins Ziel-Bewertungsblatt eintragen
        sh.Cells(zeile, SPALTE_ANALYSTENANZAHL).Value = 0

        Set tables = doc.getElementsByTagName("table")
        For Each table In tables
            If table.Rows.Length > 0 Then
                Set tabZeile = table.Rows(0)
                If tabZeile.Cells.Length > 0 Then
                    If Trim(tabZeile.Cells(0).innerText) = "Durchschnittl. Empfehlung" Then
                        If tabZeile.Cells.Length > 1 Then
                            inhalt = Trim(tabZeile.Cells(1).innerText)
                            Select Case inhalt
                                Case "KAUFEN": ergebnis = 1
                                Case "AUFSTOCKEN": ergebnis = 2
                                Case "HALTEN": ergebnis = 3
                                Case "REDUZIEREN": ergebnis = 4
                                Case "VERKAUFEN": ergebnis = 5
                            End Select
                            If ergebnis > 0 Then
                                sh.Cells(zeile, SPALTE_ANALYSTENMEINUNG).Value = ergebnis
                                Details = "Durchschnittl. Empfehlung: " & inhalt & Chr(10)
                                If table.Rows.Length > 1 Then
                                    Set tabZeile = table.Rows(1)
                                    If tabZeile.Cells.Length > 1 Then
                                        inhalt = Trim(tabZeile.Cells(1).innerText)
                                        If IsNumeric(inhalt) Then
                                            anzahl = CInt(inhalt)
                                            sh.Cells(zeile, SPALTE_ANALYSTENANZAHL).Value = anzahl
                                            Details = Details & "Anzahl Analysten: " & inhalt & Chr(10) & _
                                            "Quelle: de.4-traders.com " & ladezeit
                                            Call SetzeDetails(sh, zeile, SPALTE_ANALYSTENMEINUNG, Details)
                                        End If
                                    End If
                                End If
                            End If
                        End If
                        Set doc = Nothing
                        Exit Function
                    End If
                End If      'Tabellenzeile hat Zellen
            End If     'Tabelle hat Zeilen
        Next

        Set doc = Nothing

    End If

End Function

https://de.marketscreener.com/indexbasegauche.php?lien=recherche&mots=DE0007664005&noredirect=1&type_recherche=1

"""
import json
import locale
import logging

from stockanalyser.data_source import common

logger = logging.getLogger(__name__)


class MarketScreenerScraper(object):
    def __init__(self, isin=None, name=None, exchange=None, url=None):
        self.ISIN = isin
        self.name = name

        self.exchange = exchange
        if not self.exchange:
            self.exchange = "Deutsche Boerse AG"

        self.BASE_SEARCH_URL = "https://de.marketscreener.com/indexbasegauche.php?lien=recherche&type_recherche=1&mots="
        self.URL = url
        if not self.URL:
            self.URL = self.lookup_url()

        self.URL_consensus = self.URL + "analystenerwartungen/"
        self.data_consensus = {}
        self.URL_revisions = self.URL + "reviews-revisions/"
        self.id = self.lookup_id()
        self.data_revision_cy = {}
        self.data_revision_ny = {}

    def lookup_url(self):
        xpath = '//*[@id="ALNI1"]/tr'
        if self.ISIN:
            url = self.BASE_SEARCH_URL + self.ISIN
        else:
            url = self.BASE_SEARCH_URL + self.name
        lxml_html = common.url_to_etree(url)
        for elem in lxml_html.xpath(xpath)[1:]:
            # Name from marketscraper.net website
            # symb = elem.xpath('./td[1]')[0].text_content().encode("utf-8").decode("utf-8")
            # country = elem.xpath('./td[2]/img/@title')[0].encode("utf-8").decode("utf-8")
            href = "https://de.marketscreener.com" + elem.xpath('./td[3]/a/@href')[0].encode("utf-8").decode("utf-8")
            exchange = elem.xpath('./td[7]')[0].text_content().encode("utf-8").decode("utf-8")
            if exchange in self.exchange:
                logger.debug("Got URL: {}!".format(href))
                return href

    def lookup_id(self):
        xpath = '//*[@id="zbCenter"]/div/span/table[4]/tr/td[1]/table[1]/tr[2]/td/div[2]/a/@href'
        url = self.URL_revisions
        lxml_html = common.url_to_etree(url)
        link = lxml_html.xpath(xpath)[0]
        id = link.split("&")[1][-5:]
        return id

    def get_revison(self):
        url = "https://de.marketscreener.com//reuters_charts/afDataFeed.php?repNo={}&codeZB=&t=rev&sub_t=bna&iLang=1".format(self.id)
        data = json.loads(common.url_to_str(url))
        eps_four_weeks_cy = data[0][0][-3][1]
        date_four_weeks_cy = data[0][0][-3][0]
        locale.setlocale(locale.LC_ALL, "de_DE.utf8")
        date_four_weeks_cy = common.german_date_to_normal(date_four_weeks_cy, "%b %Y")

        eps_today_cy = data[0][0][-1][1]
        date_today_cy = data[0][0][-1][0]
        date_today_cy = common.german_date_to_normal(date_today_cy, "%d.%m.%Y")
        change_cy = (eps_today_cy / eps_four_weeks_cy) * 100 - 100

        eps_four_weeks_ny = data[0][1][-3][1]
        date_four_weeks_ny = data[0][1][-3][0]
        date_four_weeks_ny = common.german_date_to_normal(date_four_weeks_ny, "%b %Y")

        eps_today_ny = data[0][1][-1][1]
        date_today_ny = data[0][0][-1][0]
        date_today_ny = common.german_date_to_normal(date_today_ny, "%d.%m.%Y")

        change_ny = (eps_today_ny / eps_four_weeks_ny) * 100 - 100

        self.data_revision_cy[date_today_cy] = eps_today_cy
        self.data_revision_cy[date_four_weeks_cy] = eps_four_weeks_cy
        self.data_revision_cy["Change current Year"] = change_cy
        self.data_revision_ny[date_today_ny] = eps_today_ny
        self.data_revision_ny[date_four_weeks_ny] = eps_four_weeks_ny
        self.data_revision_ny["Change next Year"] = change_ny
        return self.data_revision_cy, self.data_revision_ny

    def get_consensus(self):
        xpath = '//*[@id="zbCenter"]/div/span/table[4]/tr/td[3]/div[2]/div[2]/table/tr'
        url_resonse = common.url_to_etree(self.URL_consensus)
        self.data_consensus["consensus"] = url_resonse.xpath(xpath + "[1]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "")
        self.data_consensus["n_of_analysts"] = url_resonse.xpath(xpath + "[2]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "")
        self.data_consensus["price_target_average"] = url_resonse.xpath(xpath + "[3]/td[2]")[0].text_content().replace(" ", "").replace("\n", "").replace("\r", "").strip("€")
        return self.data_consensus


if __name__ == '__main__':
    ms = MarketScreenerScraper(isin="DE0007664005")
    print(ms.get_revison())
    # print(ms.URL)
    # ms.get_consensus()
    # print(ms.data_consensus)
    # for x, y in ms.data_consensus.items():
    #     print(x)
    #     print(y)
