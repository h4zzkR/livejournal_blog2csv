livejournal_blog2csv
===========

This script downloads LiveJournal articles and saves extracted information as pandas csv dataset.
Given the URL of the most recent entry in a journal, the script iteratively fetches entries until it gets to the oldest entry.
For each entry, it extracts the entry title, tags and actual entry content (text).
If LJ changes the page layout significantly in the future, then these queries may no longer work.

Pre-requisites
--------------

* requests - for downloading the HTML
* lxml - for parsing the HTML
* cssselect - to get rid of .xpath("//a[contains(@class, 'b-controls-prev')]") constructions
* beautifulsoup4 - for pretty-printing the HTML (I couldn't get lxml to do this for me)
* unidecode - for transliteration of the title (you don't need this if your blog is in English

Running Example
-------

    ./main.py http://kogumamisha.livejournal.com/20145.html

This will download blog into the html subdirectory.
