import scrapy
import re
import mimetypes
import requests
import urlparse

class EmailSpider(scrapy.Spider):
    name = 'email'

    start_urls = []

    # A list of already visited urls to skip for further processing
    existing_visited = []

    # List of found emails to dedup on
    matched_emails = []

    verify_redirect_endpoint = True

    # Don't parse more than 4 levels deep for this example.
    # TODO: Make this configurable
    custom_settings = {
        'DEPTH_LIMIT': 4
    }


    # The email regex. Taken from: https://gist.github.com/dideler/5219706
    # Removed "/" as part of the match because of too many false positives.
    # Sample of: /people/faculty/recohen@mit.edu for the removal
    regex = re.compile(("([a-z0-9!#$%&'*+=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+=?^_`"
                        "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))


    def __init__(self, site='', verify_endpoint=True, *args, **kwargs):
        """Initializer for the spider that sets up the sites to parse. First uses Request to get the correct base url
        for a passed site. Then sets any other passed parameters this may choose to implement.

        Args:
            site: A site to get emails from. In the future, this could be made into a list.

            verify_endpoint: Whether to verify that a redirected link is still under the initial url domain..
        """

        if not site.startswith('http'):
            site = 'http://' + site

        r = requests.get(site)
        if r.status_code == 200:
            self.start_urls.append(urlparse.urljoin(r.url, '/')[0:-1])
            self.existing_visited.append(urlparse.urljoin(r.url, '/')[0:-1])
        else:
            raise requests.RequestException('Site %s could not be resolved to a HTTP 200 status code' % site)

        # FIXME: Doesn't seem like one can pass a boolean from the command line. Could do like --no-verify as an argument
        # but easier for now to keep this syntax.
        if verify_endpoint == "False":
            self.verify_redirect_endpoint = False
        else:
            self.verify_redirect_endpoint = True

        super(EmailSpider, self).__init__(*args, **kwargs)


    def parse(self, response):
        """The main parsing logic of this crawler.

        Args:
            response: The response from resolving a remote url.

        Returns:
            A hash of {email: email_value} that is aggregated into an end output.
        """

        if self.verify_redirect_endpoint and not response.url.startswith(tuple(self.start_urls)):
            return

        for email in self.get_emails(response.text):
            yield {'email': email}
        for link in response.css('a::attr(href)').extract():
            link = response.urljoin(link)

            #yield {'link': link, 'start_url': self.start_urls[0]}

            # First check as the setting doesn't seem to work as expected in scrapy. Will keep trying to load links after
            # MAX_DEPTH even if it isn't actually allowing them to process further.
            if response.meta["depth"] < self.custom_settings['DEPTH_LIMIT'] and self.is_valid_link(link) is True:

                # Add this url to the visited list. Exclude any trailing slash marks for consistency.
                self.existing_visited.append(re.sub(r'\/$', '', link))
                yield scrapy.Request(link, callback=self.parse,)


    def is_valid_link(self, l):
        guessed_type = mimetypes.guess_type(l.split('?')[0])
        # Ensure that we don't parse things like images or pdfs
        if guessed_type[0] is None or guessed_type[0].startswith('text'):
            # Ensure that we stick only to this domain.
            # FIXME: There is an issue with http vs https in this sample application. Also with www vs non-www.
            if l.startswith(tuple(self.start_urls)):
                # Exclude sites we have already visited
                if l not in self.existing_visited:
                    return True

        return False


    def get_emails(self, s):
        """Returns an iterator of matched emails found in string s."""
        # Removing lines that start with '//' because the regular expression
        # mistakenly matches patterns like 'http://foo@bar.com' as '//foo@bar.com'.
        # Additionally, remove things that match a mimetype since that is generally an image link that looks like an email.
        # Do some cleaning of the returned email. In this example case, only swap " at " for "@".
        # Final check to not at some numbers that were matching the pattern.
        return_emails = []
        for email in re.findall(self.regex, s):
            if email[0] not in self.matched_emails:
                if not email[0].startswith('//'):
                    if  mimetypes.guess_type(email[0])[0] is None or (not mimetypes.guess_type(email[0])[0].startswith('image') and not mimetypes.guess_type(email[0])[0].startswith('video')):
                        cleaned_email = re.sub(r'\sat\s', '@', email[0])
                        if not re.match(r'.+@[\d\.]+$', cleaned_email):
                            self.matched_emails.append(cleaned_email)
                            return_emails.append(cleaned_email)

        return return_emails