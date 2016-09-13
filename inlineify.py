#!/usr/bin/env python

"""
@author Jay Taylor <outtatime@gmail.com>

@date 2011-01-10

@description Automatically inlines all images and includes and optimizes CSS
resources into a single html file to the maximum extend possible.
"""

import base64
import lxml
import optparse
import pyquery
import re
import sys
import wget

css_rule_re = re.compile(r'^(?P<specifiers>[^{]+)(?P<rule>.*)')
css_spec_cleaning_re = re.compile(r':(link|hover|active|visited|focus|before|after)', re.I)

def include_bare_minimum_css(options, html, omit_bad_css=True):
    """
    @param options optparse Options object.

    @param html string.  HTML document string.

    @param omit_bad_css boolean.  Defaults to True.  When True, erroneous CSS
    will simply be omitted.  When False, any questionable CSS will be included.
    """
    d = pyquery.PyQuery(html)
    links_and_styles = d('link,style')
    favicon = None
    stylesheets = []
    for link_or_style_ele in links_and_styles:
        if link_or_style_ele.tag == 'link':
            if 'rel' in link_or_style_ele.attrib and link_or_style_ele.attrib['rel'] == 'shortcut icon':
                favicon = link_or_style_ele.attrib['href']
                continue
            stylesheets.append(wget.wget(gen_rel_url(options, link_or_style_ele.attrib['href'])))
        elif link_or_style_ele.tag == 'style':
            stylesheets.append(str(link_or_style_ele))

    out = ''

    for stylesheet in stylesheets:
        for stmt in stylesheet.split('}'):
            stmt = stmt.replace('\n', ' ').strip(' ') + '}'
            match = css_rule_re.match(stmt)
            if match:
                specifiers = match.group('specifiers')
                rule = match.group('rule')
                include_specifiers = ''
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
                if len(include_specifiers):
                    # Then this rule is used, so include it.
                    out += '%s %s\n' % (include_specifiers, rule)

    d('link,style').replaceWith('')
    d('head').append('<style type="text/css">%s</style>' % out)

    if favicon is not None:
        try:
            favicon_bin = wget.wget(favicon)
            favicon_b64 = base64.b64encode(favicon_bin)
            d('head').append('<link id="favicon" rel="shortcut icon" type="image/png" href="data:image/png;base64,%s">' % favicon_b64)
        except Exception, e:
            #print 'error: favicon integration failed'
            pass
    return str(d)

css_url_re = re.compile(r'''(?P<wholething>url\s*\(\s*['"]?(?P<url>[^\)'"]*)['"]?\s*\))''', re.I | re.M)
img_src_re = re.compile(r'''(?P<wholething><\s*img [^>]*src=['"](?P<url>[^'"]*)['"])''', re.I | re.M)

def inline_images(options, html):
    """
    @param options optparse Options object.

    @param html string.  HTML document string.
    """
    for m in css_url_re.finditer(html):
        url = gen_rel_url(options, m.group('url'))
        data = wget.wget(url)
        b64_data = base64.b64encode(data)
        html = html.replace(m.group('wholething'), 'url(data:image/%s;base64,%s)' % (url[-3:], b64_data), 1)
    for m in img_src_re.finditer(html):
        url = gen_rel_url(options, m.group('url'))
        data = wget.wget(url)
        b64_data = base64.b64encode(data)
        html = html.replace(m.group('wholething'), '<img src="data:image/%s;base64,%s"' % (url[-3:], b64_data), 1)
    return html

class OptionParser(optparse.OptionParser):
    def check_required(self, opt):
      option = self.get_option(opt)
      # Assumes the options 'default' is set to None.
      if getattr(self.values, option.dest) is None:
          self.error('%s parameter is required.  See --help for more information.' % option)

def error_exit(msg):
    sys.stderr.write('%s\n' % msg)
    sys.exit(1)

def gen_rel_url(options, fragment):
    """Generate a complete URL from a fragment, even a relative (`../') one."""
    if fragment.lower().startswith('http://') or fragment.lower().startswith('https://'):
        pass
    elif fragment.startswith('../'):
        if options.src_url is None:
            error_exit('missing required -s/--src-url flag to inlineify this document.')
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


if __name__ == '__main__':
    parser = OptionParser()
    error_exit = parser.error
    parser.add_option('-d', '--download', dest='download', action='store_true', help='Download the source HTML document and use that as input.', metavar='DOWNLOAD')
    parser.add_option('-i', '--input', dest='input', default=None, help='Path to HTML document to generate an inline version of.  If omitted, stdin will be used.', metavar='INPUT')
    parser.add_option('-s', '--src-url', dest='src_url', default=None, help='Original source URL', metavar='SRC_URL')
    # Not yet implemented.
    #parser.add_option('-s', '--strict-css', dest='strict_css', default=None, help='Should we choke on .', metavar='STRICT_CSS')
    (options, args) = parser.parse_args()
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


    html = include_bare_minimum_css(options, html)
    html = inline_images(options, html)
    print html

