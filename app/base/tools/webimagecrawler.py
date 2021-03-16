import html
import re
from typing import Tuple, List

import demjson
from bs4 import BeautifulSoup
from icrawler import ImageDownloader
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler, six, BingParser, GoogleParser


class CustomLinkPrinter(ImageDownloader):
    file_urls = []

    def get_filename(self, task, default_ext):
        file_idx = self.fetched_num + self.file_idx_offset
        return '{:04d}.{}'.format(file_idx, default_ext)

    def download(self, task, default_ext, timeout=5, max_retry=3, overwrite=False, **kwargs):
        file_url = task['file_url']
        filename = self.get_filename(task, default_ext)

        task['success'] = True
        task['filename'] = filename

        if not self.signal.get('reach_max_num'):
            self.file_urls.append(file_url)

        self.fetched_num += 1

        if self.reach_max_num():
            self.signal.set(reach_max_num=True)

        return


class OnlyImageGoogleParser(GoogleParser):

    def parse(self, response):
        soup = BeautifulSoup(response.content.decode('utf-8', 'ignore'), 'lxml')
        image_divs = soup.find_all('script')
        for div in image_divs:
            # TODO: reintegrate the constraints?
            # meta = json.loads(div.text)
            # if 'ou' in meta and 'ity' in meta and meta['ity'] is not "" and "lookaside.fbsbx.com" not in meta['ou']:
            #     yield dict(file_url=meta['ou'])

            txt = div.string
            if txt is None or not txt.startswith('AF_initDataCallback'):
                continue
            if 'ds:1' not in txt:
                continue
            txt = re.sub(r"^AF_initDataCallback\(({.*key: 'ds:\d',.+, data:.+})\);$",
                         "\\1", txt, 0, re.DOTALL)

            meta = demjson.decode(txt)['data']
            data = meta[31][0][12][2]

            uris = [img[1][3][0] for img in data if img[0] == 1]
            return [{'file_url': uri} for uri in uris]


class OnlyImageBingParser(BingParser):

    def parse(self, response):
        uris = []
        soup = BeautifulSoup(
            response.content.decode('utf-8', 'ignore'), 'lxml')
        image_divs = soup.find_all('div', class_='imgpt')
        # TODO: Take suffixes other than jpg into account
        pattern = re.compile(r'murl\":\"(.*?)\.jpg')
        for div in image_divs:
            href_str = html.unescape(div.a['m'])
            match = pattern.search(href_str)
            if match:
                name = (match.group(1) if six.PY3 else match.group(1).encode('utf-8'))
                img_url = '{}.jpg'.format(name)
                uris.append(img_url)
        return [{'file_url': uri} for uri in uris]


class CustomGoogleImageUserAgentCrawler(GoogleImageCrawler):

    def __init__(self, user_agent: str, *args, **kwargs):
        self._user_agent = user_agent
        super(CustomGoogleImageUserAgentCrawler, self).__init__(*args, **kwargs)

    def set_session(self, header=None):
        super(CustomGoogleImageUserAgentCrawler, self).set_session({'User-Agent': self._user_agent})


class CustomBingImageUserAgentCrawler(BingImageCrawler):

    def __init__(self, user_agent: str, *args, **kwargs):
        self._user_agent = user_agent
        super(CustomBingImageUserAgentCrawler, self).__init__(*args, **kwargs)

    def set_session(self, header=None):
        super(CustomBingImageUserAgentCrawler, self).set_session({'User-Agent': self._user_agent})


def crawl(user_agent: str, keyword: str, max_num: int, image_search_type: str,
          image_license: str) -> Tuple[List[str], str]:
    params = {
        'max_num': max_num,
        'min_size': (224, 224),
    }

    filters = {}
    if image_search_type != "default":
        filters.update({'type': image_search_type})
    if image_license != "default":
        filters.update({'license': image_license})
    params.update({'filters': filters})

    init_params = {
        'parser_threads': 1,
        'downloader_threads': 1,
        'downloader_cls': CustomLinkPrinter,
    }

    try:
        init_params['parser_cls'] = OnlyImageGoogleParser
        google_crawler = CustomGoogleImageUserAgentCrawler(user_agent=user_agent, **init_params)
        google_crawler.downloader.file_urls = []
        google_crawler.crawl(keyword=keyword, **params)
        if len(google_crawler.downloader.file_urls) != 0:
            return google_crawler.downloader.file_urls, "Google"
    except Exception:
        pass
    try:
        # Note that there is no 'face' filter option in Bing. Falling back to default.
        # Results seem to be the same for default and 'face'. Maybe this needs revision.
        if image_search_type == "face":
            del params['filters']
        init_params['parser_cls'] = OnlyImageBingParser
        bing_crawler = CustomBingImageUserAgentCrawler(user_agent=user_agent, **init_params)
        bing_crawler.downloader.file_urls = []
        bing_crawler.crawl(keyword=keyword, **params)
        return bing_crawler.downloader.file_urls, "Bing"
    except Exception:
        return [], "None"
