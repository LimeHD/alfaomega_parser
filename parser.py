import asyncio
import argparse
import csv
import pathlib
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urljoin

import aiohttp
import lxml.html
import pytz

__version__ = '1.1.0'
URL = 'https://alfaomega.tv/canal-tv/programul-tv'
timezone = pytz.timezone('Europe/Bucharest')


async def fetch(session, url) -> str:
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.text()


async def main(file, delay):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit_per_host=3)) as session:
        html = await fetch(session, URL)

        dom = lxml.html.fromstring(html)
        logo_path = dom.xpath('.//a[@class="tm-logo"]/img/@src')[0]
        channel_logo_url = urljoin(URL, logo_path)

        other_pages = [urljoin(URL, path) for path in dom.xpath('.//a[contains(@class, "ProductNav")]/@href')]
        htmls = []
        for url in other_pages:
            try:
                await asyncio.sleep(delay)
                htmls.append(await fetch(session, url))
            except Exception as exc:
                print(exc)

    data = []
    for html in htmls:

        dom = lxml.html.fromstring(html)

        day_value = dom.xpath('.//option[@selected]/@value')[0]
        query = parse_qs(urlparse(day_value).query)
        current_day = datetime.strptime(query['zi'][0], '%Y-%m-%d')

        for i, el in enumerate(dom.xpath('.//div[starts-with(@id, "dialog_")]')):

            _time = el.get('id').lstrip('dialog_')
            _date = current_day + timedelta(hours=int(_time[:2]), minutes=int(_time[2:]))
            datetime_start = timezone.localize(_date).isoformat()

            if i > 0:
                data[-1]['datetime_finish'] = datetime_start

            data.append({
                'datetime_start': datetime_start,
                'datetime_finish': None,
                'channel': 'Alfa Omega TV',
                'title': el.xpath('./h2/text()')[0],
                'channel_logo_url': channel_logo_url,
                'description': el.xpath('./p/text()')[0],
            })

    with open(file, mode='w', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, data[0].keys(), delimiter='\t')
        writer.writeheader()
        writer.writerows(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=str)
    parser.add_argument('--delay', required=False, type=int, default=0)
    args = parser.parse_args()

    file = pathlib.Path(args.output)

    print(f'Парсер "alfaomega" версии {__version__} выкачивает список программ с "{URL}" в файл "{file}"')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(file, int(args.delay)))
