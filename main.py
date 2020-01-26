#!/usr/bin/env python
import os
import os.path as P
import requests
import lxml.html
import lxml.etree
import urllib.parse
import codecs
import datetime
import unidecode
import bs4
import urllib.request
import urllib.parse
import sys
import urllib.error
import urllib
from bs4 import BeautifulSoup
import pandas as pd
import re

DEBUG = 0

"""The headers to write for each post."""
HEADERS = ["categories: blog", "layout: post"]


def encode_title(title):
    """Jekyll posts are stored as individual files.
    It makes sense to name each file with the title of the post.
    However, Jekyll doesn't seem to handle file names with spaces or
    non-latin characters. It picks them up when building the site, but the
    actual links will be broken. This function encodes the title in such a way
    that it can be used as a filename for Jekyll posts."""
    #
    # You probably don't need the line below if your posts are in English
    #
    latin_title = unidecode.unidecode(title)
    encoded_title = urllib.parse.quote_plus(latin_title.replace(" ", "-"))
    return encoded_title


def parse_previous_link(root):
    """Parse the link to the chronologically previous blog entry."""
    prev_entry_url = None
    links = root.cssselect("a.b-controls-prev")

    if links:
        prev_entry_url = links[0].get("href")

    html_doc = urllib.request.urlopen(prev_entry_url).read()
    soup = bs4.BeautifulSoup(html_doc, 'html.parser')
    string = ''
    for i in soup.find_all('meta')[1:]:
        if 'og:url' in str(i):
            string = str(i)
    string = string[string.find('<meta content="') + len('<meta content="'):string.find('" property')]
    prev_entry_url = string
    return prev_entry_url


def parse_title(root):
    """Parse the title of a LiveJournal entry."""
    title = None
    h1 = root.cssselect('h1.entry-title')
    if h1:
        title = h1[0].text
    if DEBUG:
        print(title)
    assert title
    return title


def parse_timestamp(root):
    """Parse the timestamp of a LiveJournal entry.
    Returns a datetime.datetime instance."""
    timestamp = None
    published = root.cssselect("time.dt-published")
    if published:
        # 2013-12-13 20:59:00
        timestamp = datetime.datetime.strptime(
            published[0].text_content(), "%Y-%m-%d %H:%M:%S")
    if DEBUG:
        print(timestamp)
    assert timestamp
    return timestamp


def parse_entry_text(root):
    """Parse the actual entry text of a LiveJournal entry.
    Returns a UTF-8 encoded byte string."""
    #
    # Here we only grab the HTML fragment that corresponds to the entry
    # context.
    # Throw everything else away.
    #
    entry_text = None
    article = root.cssselect("article.entry-content")
    if article:
        entry_text = lxml.etree.tostring(
            article[0], pretty_print=True, encoding="utf-8")
    if DEBUG:
        print(entry_text)
    assert entry_text
    return entry_text


def parse_and_remove_tags(root):
    """Returns the tags for a LiveJournalEntry.
    As a side effect, destroy the tags element of the entry."""
    tags = []
    a = root.cssselect("div.ljtags a")
    if a:
        tags = [aa.text for aa in a]
    ljtags = root.cssselect("div.ljtags")
    if ljtags:
        ljtags[0].getparent().remove(ljtags[0])
    return tags


class Entry:
    """Represents a single LiveJournal entry.
    Includes functions for downloading an entry from a known URL."""

    def __init__(self, title, text, updated, prev_entry_url, tags):
        self.title = title
        self.text = text
        self.updated = updated
        self.prev_entry_url = prev_entry_url
        self.tags = tags

    def update_df(self, username):
        """Save the entry to the specified directory.
        The filename of the entry will be determined from its title and update
        time.
        The entry will contain a Jekyll header with a HTML fragment
        representing the content."""

        data = bs4.BeautifulSoup(self.text, "lxml").findAll(text=True)
        def visible(element):
            if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
                return False
            elif re.match('<!--.*-->', str(element.encode('utf-8'))):
                return False
            return True

        text = ' '.join(list(filter(visible, data))[:-2]).replace(u'\xa0', u' ')
        tags = '||'.join(self.tags)
        title = str(self.title)

        item = {'title' : title, 'text' : text, 'tags' : tags}
        return item

    @staticmethod
    def download(url):
        """Download an entry from a URL and parse it."""
        if 'format=light' not in url:
            url = '{}{}format=light'.format(url, '&' if '?' in url else '?')
        r = requests.get(url)
        assert r.status_code == 200

        root = lxml.html.document_fromstring(r.text)
        title = parse_title(root)
        tags = parse_and_remove_tags(root)
        entry_text = parse_entry_text(root)
        timestamp = parse_timestamp(root)
        prev_entry_url = parse_previous_link(root)

        return Entry(title, entry_text, timestamp, prev_entry_url, tags)


def create_parser():
    from optparse import OptionParser
    p = OptionParser(
        "usage: %prog http://yourusername.livejournal.com/most-recent-entry.html")  # noqa
    p.add_option(
        "-d",
        "--debug",
        dest="debug",
        type="int",
        default="0",
        help="Set debugging level")
    p.add_option(
        "",
        "--destination",
        dest="destination",
        type="string",
        default="",
        help="Set destination directory")
    p.add_option(
        "-f",
        "--force-overwrite",
        dest="overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing files")
    return p


def main():
    global DEBUG
    p = create_parser()
    options, args = p.parse_args()
    DEBUG = options.debug

    df = pd.DataFrame(columns=['title', 'text', 'tags'])
    username = args[0]
    username = username[username.find('//') + 2:username.find('.live')]

    if len(args) != 1:
        p.error("invalid number of arguments")

    next_url = args[0]

    try:
        while next_url is not None:
            print(next_url)
            entry = Entry.download(next_url)
            # print(entry.update_df(username)['tags'])
            df = df.append(entry.update_df(username), ignore_index=True)
            next_url = entry.prev_entry_url
    except:
        df.to_csv(f'{username}_lj_blog.csv')

    print(df)
    df.to_csv(f'{username}_lj_blog.csv')

if __name__ == "__main__":
    main()
