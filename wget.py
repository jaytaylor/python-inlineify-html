import urllib2
import hashlib

USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10)'

class WgetError(Exception):
    pass


def wget(url, referer='', num_tries=1):
    """
    @param referer Defaults to ''.  If you pass None, it will be the same as
        the target URL.
    """
    hash = hashlib.md5(url).hexdigest()
    #try:
    #    with open('cache/%s' % hash, 'r') as f:
    #        return f.read()
    #except IOError:
    #    pass
    if referer == None:
        referer = url
    opener = urllib2.build_opener()
    opener.addheaders = [
        ('User-agent', USER_AGENT),
        ('Referer', referer),
    ]
    try:
        data = opener.open(url).read()
    #    with open('cache/%s' % hash, 'w') as f:
    #        f.write(data)
        return data
    #except IOError:
    #    raise WgetError('failed to cache url: %s, check cache dir permissions' % url)
    except urllib2.URLError, e:
        if num_tries > 1:
            return wget(url, referer, num_tries - 1)
        raise WgetError(url + ' failed, ' + str(e))

def resolve_link(url, attempt=1):
    opener = urllib2.build_opener()
    opener.addheaders = [
        ('User-agent', USER_AGENT),
        ('Referer', url),
    ]
    try:
        response = opener.open(url)
        url_destination = response.url
        return url_destination.replace('?from=rss', '')
    except Exception, e:
        if attempt < 10:
            attempt += 1
            return resolve_link(url, attempt)
        raise e

