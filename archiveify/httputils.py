# -*- coding: utf-8 -*-

import os
import requests

DEFAULT_TIMEOUT = 10

DEFAULT_USER_AGENT = os.environ.get('DEFAULT_USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36')
# Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10)
# Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36
# Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)

def get(url):
    headers = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Pragma': 'no-cache',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'no-cache',
    }
    response = requests.get(url, headers=headers, allow_redirects=True, timeout=DEFAULT_TIMEOUT)
    #print response
    #print dir(response)
    return response #.text, response.status_code)

