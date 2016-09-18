#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import BaseHTTPServer
import os
import SimpleHTTPServer
import SocketServer
import threading
import unittest

from ..archiveify import httputils
from ..archiveify import WebPageArchiver, Options

HTTP_SERVER_INTERFACE = '127.0.0.1'

def http_serve_once(body='hello world', status_code=200, content_type='text/plain'):
    """@return URL to fetch."""
    class TestHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(int(status_code))
            self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(body)

    httpd = SocketServer.TCPServer((HTTP_SERVER_INTERFACE, 0), TestHTTPRequestHandler)
    thread = threading.Thread(target=httpd.handle_request)
    thread.start()
    return 'http://%s:%s/' % httpd.socket.getsockname()

def http_serve_path(path):
    if not path.endswith('/'):
        path += '/'
    prev_cwd = os.getcwd()
    os.chdir(path)
    httpd = SocketServer.TCPServer((HTTP_SERVER_INTERFACE, 0), SimpleHTTPServer.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    return 'http://%s:%s/' % httpd.socket.getsockname()

class TestHTTPServers(unittest.TestCase):
    def test_http_serve_once(self):
        args = ('this is a test', 403)
        url = http_serve_once(*args)
        response = httputils.get(url)
        self.assertEqual(args, (response.text, response.status_code))

    def test_http_serve_path(self):
        html_filepath = 'techblog.netflix.com/2015/07/java-in-flames.html'
        base_path = os.path.dirname(os.path.abspath(__file__))
        with codecs.open('%s/test-data/%s' % (base_path, html_filepath), 'r', encoding='utf-8') as fh:
            expected_body = fh.read()
        base_url = http_serve_path('%s/test-data/' % base_path)
        response = httputils.get('%s%s' % (base_url, html_filepath))
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected_body, response.content.decode('utf-8'))

class TestInlineifier(unittest.TestCase):
    def test_basic_site_index(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_url = http_serve_path('%s/test-data/basic-site.tld/' % base_path)
        response = httputils.get('%s%s' % (base_url, 'index.html'))
        self.assertEqual(200, response.status_code)

    def test_favicon_inlining(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_url = http_serve_path('%s/test-data/basic-site.tld/' % base_path)
        wpa = WebPageArchiver(Options(src_url='%s%s' % (base_url, 'index.html'), download=True))
        wpa.inline_favicon()
        self.assertTrue(';base64,' in str(wpa), 'string ";base64," not found in HTML output:\n%s' % wpa)

    def test_css_inlining_and_minimization(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_url = http_serve_path('%s/test-data/basic-site.tld/' % base_path)
        wpa = WebPageArchiver(Options(src_url='%s%s' % (base_url, 'index.html'), download=True))
        wpa.inline_and_min_css()
        self.assertTrue('background-color: #000' in str(wpa), '<body> style "background-color: #000" not found in HTML output:\n%s' % wpa)
        self.assertFalse('background-color: teal' in str(wpa), '<span> style "background-color: teal" found in HTML output:\n%s' % wpa)

    def test_js_inlining(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        base_url = http_serve_path('%s/test-data/basic-site.tld/' % base_path)
        wpa = WebPageArchiver(Options(src_url='%s%s' % (base_url, 'index.html'), download=True))
        wpa.inline_js()
        self.assertTrue('console.log("hello js world");' in str(wpa), 'JS content not found in HTML output:\n%s' % wpa)

#        with open('test-data/smithsonian-clock.html', 'rb') as fh:
#        args = ('this is a test', '403')
#        url = http_serve_once()
#        pass
#        self.assertEqual(httputils.get(url)
        #print wget.wget('http://%s:%s/' % (HTTP_SERVER_INTERFACE, port))

        #import sys
        #sys.stdout.write('%s\n' % str(wpa))

if __name__ == '__main__':
    unittest.main()

