# -*- coding: utf-8 -*-

def patch():
	"""
	Monkey patch for inlinestyler to support:
		- root css selector.
	"""
	from inlinestyler import cssselect
	cssselect.Pseudo._xpath_root = lambda self, xpath: xpath

