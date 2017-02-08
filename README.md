Kraken
======

This application is used to parse emails from websites. It uses scrapy to crawl the site and then a bunch of custom
code to determine what is an email adddress from there.

Installation
============

    $ git clone
    $ cd kraken
    $ pip install -r pip-install-req.txt

Usage Instructions
==================

    $ scrapy runspider scrap_emails.py -a site=<site_url> -o output.csv

Examples from the requirements:

    $ scrapy runspider scrap_emails.py -a site=java.com -o jana.csv

    $ scrapy runspider scrap_emails.py -a site=mit.edu -o mit.csv

Configuration
=============

Mostly see Notes below. However, currently this application limits the parsing depth to 4 levels. To increase that,
open up 'scrap_emails.py' and modify the 'DEPTH_LIMIT' parameter.

Notes
=====

There are many issues with parsing a site like mit.edu. The most promonent is the heavy use of redirects: a link at the
bottom of [http://web.mit.edu/registrar/stats/index.html](http://web.mit.edu/registrar/stats/index.html) goes to [http://web.mit.edu/due/](http://web.mit.edu/due/) which is a valid domain at
first glance. However, once resolved, that turns out to actually be an invalid domain of: [http://due.mit.edu/](http://due.mit.edu/). So...
how does one handle this case? One could disable redirects but that would eliminate aliases that are correct under the
[http://web.mit.edu](http://web.mit.edu) domain. Furthermore, these redirects to another domain could still be argued valid since that
 content does virtually live under that original domain endpoint yet. For a temporary solution,
 I have added a command flag as "-a verify_endpoint" as to whether to verify the  end resulting redirection URL.
 A full code example to turn off the verification is:

    scrapy runspider scrap_emails.py -a site=mit.edu -a verify_endpoint=False -o mit.csv

It is also worth noting that one can disable redirects in the scrapy library that I attempted to make
a flag for but something seems to not be working correctly there. The best I was able to do was it correctly giving up
on ~80% of redirects when the redirect middleware was turned off in a settings.py file. There wasn't an obvious reason
as to why, say, some 301 redirects would go through while it would correctly not redirect on other 301 status codes. I'd
need to spend more time debugging for this option that would increase performance at the cost of less accuracy.

Another issue deals with just how many links are on their site. I have it parsing only four levels deep and that can take
10 minutes to run in a non-threaded manor. You can increase the number of levels at the top of the file with the
parameter "DEPTH_LIMIT". This limit is not only set but also hand-coded into the parse function since scrapy doesn't
seem to implement it correctly. It will refuse to add emails from a link that that is beyond that DEPTH_LIMIT... but it
still makes calls to those pages that keeps the crawling slow. A final note is that this setting is needed for the MIT
site as there is an endless loop that occurs with some bad coding on their end (essentially creating a longer and longer
relative url based on the previous url).

A further issue is my parsing of email addresses. For this excercise, I took an existing Regex, slightly modified it,
and that is essentially it. It works for cases like 'email at site.org' but won't work for 'email "at" site "dot" org'.
More testing is needed for that to catch more cases and to more nuanced false flags.





