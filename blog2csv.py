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
from sys import stdout

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


def parse_previous_link(root, special):
    """Parse the link to the chronologically previous blog entry."""
    if special is True:
        # span class="entry-linkbar-inner">
        string = str(root.find('span', attrs={'class' : "entry-linkbar-inner"}))
        string = string[string.find('<a href="') + len('<a href="'):string.find('"><img')]
    else:
        string = str(root.find('a', attrs={'class' : 'b-controls b-controls-prev'})['href'])
    return string


def parse_title(root):
    """Parse the title of a LiveJournal entry."""
    title = str(root.find(attrs={"property" : "og:title"})).split('>')[0]
    title = title[title.find('content="') + len('content="'):title.find('" property')]
    return title


def parse_entry_text(root,special):
    """Parse the actual entry text of a LiveJournal entry.
    Returns a UTF-8 encoded byte string."""
    #
    # Here we only grab the HTML fragment that corresponds to the entry
    # context.
    # Throw everything else away.
    text = None
    if special is True:
        text = str(root.find_all('div', attrs={'class' : 'entry-content'})[0].text)
        text = text[:text.find('Tags')]
    else:
        text = root.find('article', attrs={'class' : ' b-singlepost-body entry-content e-content '})
    return text


def parse_and_remove_tags(root):
    """Returns the tags for a LiveJournalEntry.
    As a side effect, destroy the tags element of the entry."""
    tags = str(root.find('a', attrs={'class' : "b-controls b-controls-share js-lj-share"}))
    tags = tags[tags.find('data-hashtags=') + len('data-hashtags="'):tags.find('" data-title="')]
    return tags.split(',')


class Entry:
    """Represents a single LiveJournal entry.
    Includes functions for downloading an entry from a known URL."""

    def __init__(self, title, text, prev_entry_url, tags, special):
        self.title = title
        self.text = text
        self.prev_entry_url = prev_entry_url
        self.tags = tags
        self.special = special

    def update_df(self, username):
        """Save the entry to the specified directory.
        The filename of the entry will be determined from its title and update
        time.
        The entry will contain a Jekyll header with a HTML fragment
        representing the content."""
        if self.special is False:
            self.text = str(self.text.text)

        text = self.text.replace(u'\xa0', u' ')
        tags = '||'.join(self.tags)
        title = str(self.title)

        item = {'title' : title, 'text' : text, 'tags' : tags}
        return item

    @staticmethod
    def download(url):
        """Download an entry from a URL and parse it."""
        if 'format=light' not in url:
            url = '{}{}format=light'.format(url, '&' if '?' in url else '?')
        special = False
        if 'dir=prev' in url:
            special = True

        html_doc = urllib.request.urlopen(url).read()
        root = bs4.BeautifulSoup(html_doc, 'html.parser')

        # root = lxml.html.document_fromstring(r.text)
        title = parse_title(root)
        tags = parse_and_remove_tags(root)
        entry_text = parse_entry_text(root, special)
        prev_entry_url = parse_previous_link(root, special)

        return Entry(title, entry_text, prev_entry_url, tags, special)


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
        default=os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'blogs'),
        help="Set destination directory")
    p.add_option(
        "-f",
        "--force-overwrite",
        dest="overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing files")
    p.add_option(
        '--max_posts',
        dest="max_posts",
        default=500,
        help="Count of max posts per blog"
    )
    return p


def main():
    global DEBUG
    p = create_parser()
    options, args = p.parse_args()
    DEBUG = options.debug

    df = pd.DataFrame(columns=['title', 'text', 'tags'])
    next_url = args[0]
    username = args[0]
    username = username[username.find('//') + 2:username.find('.live')]
    
    args = p.parse_args()
    directory = args[0].destination
    max_posts = int(args[0].max_posts)

    if not os.path.exists(directory):
        os.makedirs(directory)

    cnt = 0
    try:
        while next_url is not None:
            if cnt == max_posts:
                break
            print(next_url)
            entry = Entry.download(next_url)
            df = df.append(entry.update_df(username), ignore_index=True)
            next_url = entry.prev_entry_url
            cnt += 1
    except AssertionError:
        pass
    except KeyboardInterrupt:
        pass
    except TypeError:
        pass

    if DEBUG:
        print(df)

    df.to_csv(os.path.join(directory, f'{username}_lj_blog.csv'))

if __name__ == "__main__":
    main()
