#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author Jay Taylor <outtatime@gmail.com>

@date 2011-01-10

@description Automatically inlines all images and includes and optimizes CSS
resources into a single html file to the maximum extend possible.
"""

import base64
import inlinestyler.utils
import lxml
import optparse
from pyquery import PyQuery as pq
import re
import sys
import wget

import inlinestyler_monkey_patch
import httputils

inlinestyler_monkey_patch.patch()

FORBIDDEN_RESOURCES = [
    'https://www.google-analytics.com/analytics.js',
    'http://www.google-analytics.com/analytics.js',
    '//www.google-analytics.com/analytics.js',
    'https://www.google-analytics.com/ga.js',
    'http://www.google-analytics.com/ga.js',
    '//www.google-analytics.com/ga.js',
]

css_rule_re = re.compile(r'^(?P<specifiers>[^{]+)(?P<rule>.*)')
css_spec_cleaning_re = re.compile(r':(link|hover|active|visited|focus|before|after)', re.I)

class Options(object):
    def __init__(self, input=None, src_url=None, download=False, inline_css=False, inline_js=False):
        self.input = input
        self.src_url = src_url
        self.download = download
        self.inline_css = inline_css
        self.inline_js = inline_js

class WebPageArchiver(object):
    def __init__(self, options):
        """
        @param transforms is a sequence of functions conforming to `def foo(options, html)'.
        """
        self.options = options
        self._html = None
        self._d = None

    def html(self):
        if self._html is None:
            if self.options.download is True and self.options.input is not None:
                raise Exception('invalid flags combination: -d/--download cannot be used with -i/--input specification')
            if self.options.download is True and self.options.src_url is None:
                raise Exception('missing flag: -d/--download requires -s/--src-url')
            if self.options.src_url is not None:
                setattr(self.options, 'base_url', re.sub(r'^([^/]*//[^/]+).*$', r'\1', self.options.src_url))
                if self.options.src_url[0:7].lower() != 'http://' and self.options.src_url[0:8].lower() != 'https://':
                    self.options.src_url = 'http://%s' % self.options.src_url
            if self.options.download is True:
                response = httputils.get(self.options.src_url)
                self._html = response.content.decode('utf-8')
            elif options.input == None:
                # Read from stdin.
                self._html = sys.stdin.readlines()
            else:
                with open(self.options.input, 'r') as fh:
                    self._html = fh.read()
        return self._html

    def __str__(self):
        html = self.d().__html__().encode('utf-8')
        return html

    def apply_all(self):
        self.inline_favicon()
        self.inline_and_min_css()
        self.inline_js()
        return str(self)

    def d(self):
        if self._d is None:
            self._d = pq(self.html())
        return self._d

    def _gen_rel_url(self, fragment):
        url = gen_rel_url(self.options, fragment)
        return url

    def inline_favicon(self):
        for favicon in self.d()('link[rel="shortcut icon"],link[rel*="icon"]'):
            if 'href' in favicon.attrib:
                favicon_url = self._gen_rel_url(favicon.attrib['href'])
                response = httputils.get(favicon_url)
                if response.status_code / 100 != 2:
                    raise Exception('Got non-2xx status-code=%s for favicon from %s' % (response.status_code, favicon_url))
                favicon_bin = response.content
                favicon_b64 = base64.b64encode(favicon_bin)
                favicon_type = favicon.attrib.get('type', 'image/png')
                favicon.attrib['href'] = 'data:%s;base64,%s' % (favicon_type, favicon_b64)
                break

    def inline_and_min_css(self, force_include_bad_css=True):
        stylesheet_links = self.d()('link[rel="stylesheet"]')
        for link_ele in stylesheet_links:
            if 'href' in link_ele.attrib:
                resolved_url = self._gen_rel_url(link_ele.attrib['href'])
                response = httputils.get(resolved_url)
                stylesheet = response.content.decode('utf-8')
                pruned_stylesheet = ''
                for stmt in stylesheet.strip().split('}'):
                    if len(stmt) == 0:
                        continue
                    stmt = stmt.replace('\n', ' ').strip(' ') + '}'
                    match = css_rule_re.match(stmt)
                    if match:
                        specifiers = match.group('specifiers')
                        rule = match.group('rule')
                        include_specifiers = u''
                        #print specifiers, '///'
                        for specifier in specifiers.split(','):
                            clean_specifier = re.sub(css_spec_cleaning_re, r'', specifier)
                            # Interesting idea, but maybe not the best. -.v
                            #specifier = specifier.replace(' ', '>')
                            include_current = False
                            try:
                                matched_elements = self.d()(clean_specifier)
                                if len(matched_elements):
                                    # Then the element should be included.
                                    include_current = True
                                #else:
                                    # Otherwise it can be fairly safely omitted.
                                    #pass
                            except Exception, e:
                                # PQ can't handle it; it is likely bad CSS so omit it
                                # unless omit_bad_css suppression has been requested.
                                if force_include_bad_css:
                                    include_current = True
                            if include_current:
                                if len(include_specifiers):
                                    include_specifiers += ',' + specifier
                                else:
                                    include_specifiers = specifier
                        if len(include_specifiers) > 0:
                            # Then the rule is in-use, so include it.
                            pruned_stylesheet += u'%s %s\n' % (include_specifiers, rule)
                if len(pruned_stylesheet) > 0:
                    self.d()(link_ele).replaceWith(u'<style type="text/css">\n%s\n</style>' % pruned_stylesheet.strip())
                else:
                    self.d()(link_ele).replaceWith(u'')

    def inline_js(self):
        for script in self.d()('script'):
            if 'src' in script.attrib:
                if script.attrib['src'] in FORBIDDEN_RESOURCES:
                    self.d()(script).remove()
                else:
                    script_src = self._gen_rel_url(script.attrib['src'])
                    response = httputils.get(script_src)
                    if response.status_code / 100 != 2:
                        raise Exception('Got non-2xx status-code=%s while fetching %s' % (response.status_code, script_src))
                    else:
                        self.d()(script).replaceWith('<script>\n/* src: %s */\n%s;</script>' % (script_src, response.content.decode('utf-8').strip()))
            elif '"UA-' in script.text or "'UA-" in script.text:
                self.d()(script).remove()

def reduce_and_inline_css_js(options, html, omit_bad_css=True):
    """
    @param options optparse Options object.

    @param html string.  HTML document string.

    @param omit_bad_css boolean.  Defaults to True.  When True, erroneous CSS
    will simply be omitted.  When False, any questionable CSS will be included.
    """
    def inject_css(d):
        favicon = d('link[rel="shortcut icon"],link[rel*="icon"]')
        links_and_styles = d('link[rel="stylesheet"],style')
        stylesheets = []
        for link_or_style_ele in links_and_styles:
            if link_or_style_ele.tag == 'link':
                if 'rel' in link_or_style_ele.attrib and link_or_style_ele.attrib['rel'] == 'shortcut icon':
                    favicon = link_or_style_ele.attrib['href']
                    continue
                resolved_url = gen_rel_url(options, link_or_style_ele.attrib['href'])
                response = httputils.get(resolved_url)
                stylesheets.append(response.content.decode('utf-8'))
            elif link_or_style_ele.tag == 'style':
                stylesheets.append(str(link_or_style_ele))

        out = ''

        #print html
        for stylesheet in stylesheets:
            for stmt in stylesheet.split('}'):
                stmt = stmt.replace('\n', ' ').strip(' ') + '}'
                match = css_rule_re.match(stmt)
                if match:
                    specifiers = match.group('specifiers')
                    rule = match.group('rule')
                    include_specifiers = ''
                    #print specifiers, '///'
                    for specifier in specifiers.split(','):
                        clean_specifier = re.sub(css_spec_cleaning_re, '', specifier)
                        # Interesting idea, but maybe not the best. -.v
                        #specifier = specifier.replace(' ', '>')
                        include_current = False
                        try:
                            matched_elements = d(clean_specifier)
                            if len(matched_elements):
                                # Then the element should be included.
                                include_current = True
                            #else:
                                # Otherwise it can be fairly safely omitted.
                                #pass
                        except Exception, e:#lxml.cssselect.ExpressionError:
                            # PQ can't handle it; it is likely bad CSS so omit it
                            # unless omit_bad_css suppression has been requested.
                            if omit_bad_css:
                                include_current = True
                        if include_current:
                            if len(include_specifiers):
                                include_specifiers += ',' + specifier
                            else:
                                include_specifiers = specifier
                    if len(include_specifiers) > 0:
                        # Then this rule is used, so include it.
                        out += '%s %s\n' % (include_specifiers, rule)

        d('link,style').replaceWith('')
        d('head').append('<style type="text/css">%s</style>' % out) #.encode('utf-8'))

        if favicon:
            try:
                response = httputils.get(favicon[0].attrib['href'])
                if response.status_code / 100 != 2:
                    raise Exception('Got non-2xx status-code=%s for favicon from %s' % (response.status_code, favicon[0].attrib['href']))
                favicon_bin = response.content
                favicon_b64 = base64.b64encode(favicon_bin)
                favicon_type = favicon[0].attrib.get('type', 'image/png')
                d('head').append('<link id="favicon" rel="shortcut icon" type="%s" href="data:%s;base64,%s">' % (favicon_type, favicon_type, favicon_b64))
            except Exception as e:
                system.stderr.write('error: favicon integration failed, %s\n' % e)
                pass

    # Inline JS.
    def inject_js(d):
        scripts = []
        for script in d('script'):
            if 'src' in script.attrib:
                if not script.attrib['src'] in FORBIDDEN_RESOURCES:
                    script_src = gen_rel_url(options, script.attrib['src'])
                    response = httputils.get(script_src)
                    if response.status_code / 100 != 2:
                        sys.stderr.write('Got non-2xx status-code=%s while fetching %s' % (response.status_code, script_src))
                    else:
                        scripts.append(('/* src: %s */\n %s' % (script_src, response.content.decode('utf-8'))))
            else:
                if not '"UA-' in script.text and not "'UA-" in script.text:
                    scripts.append(script.text_content())
        d('script').replaceWith('')
        for script in scripts:
            d('head').append('<script type="text/javascript">%s;</script>' % script)

    d = pq(html)
    inject_css(d)
    inject_js(d)
    html = d('html').__html__().encode('utf-8')
    if options.inline_css:
        html = inlinestyler.utils.inline_css(html)
        d = pq(html)
        d('style').replaceWith('')
        html = d('html').__html__().encode('utf-8')
    return html

css_url_re = re.compile(r'''(?P<wholething>url\s*\(\s*['"]?(?P<url>[^\)'"]*)['"]?\s*\))''', re.I | re.M)
img_src_re = re.compile(r'''(?P<wholething><\s*img [^>]*src=['"](?P<url>[^'"]*)['"])''', re.I | re.M)

def inline_images(options, html):
    """
    @param options optparse Options object.

    @param html string.  HTML document string.
    """
    for m in css_url_re.finditer(html):
        url = gen_rel_url(options, m.group('url'))
        response = httputils.get(url)
        if response.status_code / 100 != 2:
            sys.stderr.write('Got non-2xx status-code=%s while fetching %s' % (response.status_code, url))
        else:
            b64_data = base64.b64encode(response.content)
            html = html.replace(m.group('wholething'), 'url(data:image/%s;base64,%s)' % (url[-3:], b64_data), 1)

    for m in img_src_re.finditer(html):
        url = gen_rel_url(options, m.group('url'))
        response = httputils.get(url)
        if response.status_code / 100 != 2:
            sys.stderr.write('Got non-2xx status-code=%s while fetching %s' % (response.status_code, url))
        else:
            b64_data = base64.b64encode(response.content)
            html = html.replace(m.group('wholething'), '<img src="data:image/%s;base64,%s"' % (url[-3:], b64_data), 1)

    return html

class OptionParser(optparse.OptionParser):
    def check_required(self, opt):
      option = self.get_option(opt)
      # Assumes the options 'default' is set to None.
      if getattr(self.values, option.dest) is None:
          self.error('%s parameter is required.  See --help for more information.' % option)

def error_exit(msg):
    #sys.stderr.write('%s\n' % msg)
    #sys.exit(1)
    raise Exception(msg)

def gen_rel_url(options, fragment):
    """Generate a complete URL from a fragment, even a relative (`../') one."""
    if fragment.lower().startswith('http://') or fragment.lower().startswith('https://'):
        pass
    elif fragment.startswith('../'):
        if options.src_url is None:
            error_exit('missing required -s/--src-url flag to archive this document.')
        fragment = '%s%s' % (re.sub(r'^(.*/).*$', r'\1', options.src_url), fragment)
        while '/../' in fragment:
            fragment = re.sub(r'^([^//]+//[^/]+/.*?)/?\.\./(.*)$', r'\1\2', fragment)
    elif fragment.startswith('//'):
        fragment = 'http:%s' % fragment
    else:
        if not hasattr(options, 'base_url'):
            error_exit('missing required -s/--src-url flag to inlineify this document.')
        fragment = '%s/%s' % (options.base_url, fragment.lstrip('/'))
    return fragment

def archiveify(options):
    if options.download is True and options.input is not None:
        parser.error('invalid flags combination: -d/--download cannot be used with -i/--input specification.')
    if options.download is True and options.src_url is None:
        parser.error('missing flag: -d/--download requires -s/--src-url.')
    if options.src_url is not None:
        setattr(options, 'base_url', re.sub(r'^([^/]*//[^/]+).*$', r'\1', options.src_url)) #[0:8] + options.src_url[8:].index('/')
        if options.src_url[0:7].lower() != 'http://' and options.src_url[0:8].lower() != 'https://':
            options.src_url = 'http://%s' % options.src_url

    if options.download is True:
        html = wget.wget(options.src_url)
    elif options.input == None:
        # Read from stdin.
        html = sys.stdin.readlines()
    else:
        with open(options.input, 'r') as fh:
            html = fh.read()

    html = reduce_and_inline_css_js(options, html)
    html = inline_images(options, html)
    return html

if __name__ == '__main__':
    parser = OptionParser()
    error_exit = parser.error
    parser.add_option('-c', '--inline-css', dest='inline_css', action='store_true', help='Enable CSS attribute inlining', metavar='INLINE_CSS')
    parser.add_option('-d', '--download', dest='download', action='store_true', help='Download the source HTML document and use that as input.', metavar='DOWNLOAD')
    parser.add_option('-i', '--input', dest='input', default=None, help='Path to HTML document to generate an inline version of.  If omitted, stdin will be used.', metavar='INPUT')
    parser.add_option('-s', '--src-url', dest='src_url', default=None, help='Original source URL', metavar='SRC_URL')
    (options, args) = parser.parse_args()

    html = archiveify(options) #.encode('utf-8')
    print(html)


