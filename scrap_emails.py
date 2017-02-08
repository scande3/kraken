import scrapy
import re
import mimetypes
import requests
import urlparse

class EmailSpider(scrapy.Spider):
    name = 'email'

    # Used by scrapy for the initial starting query points
    start_urls = []

    # The same as start_urls but without the 'http://' or 'https://'
    httpless_start_urls = set([])


    # A set of already visited urls to skip for further processing
    existing_visited = set([])

    # Set of found emails to dedup on
    matched_emails = set([])

    verify_redirect_endpoint = True

    # Don't parse more than 4 levels deep for this example.
    # TODO: Make this configurable
    custom_settings = {
        'DEPTH_LIMIT': 4
    }


    # The email regex. Taken from: https://gist.github.com/dideler/5219706
    # Removed "/" as part of the match because of too many false positives.
    # Sample of: /people/faculty/recohen@mit.edu for the removal
    # Modified to force at least two characters in the domain. Case of <email>@c.e.r.n.
    regex = re.compile(("([a-z0-9!#$%&'*+=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+=?^_`"
                        "{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                        "\sdot\s))+[a-z0-9][a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))


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
            self.existing_visited.add(urlparse.urljoin(r.url, '/')[0:-1])
            self.httpless_start_urls.add(re.sub(r'http[s]*\:\/\/', '', urlparse.urljoin(r.url, '/')[0:-1]))
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

        if self.verify_redirect_endpoint and not self.httpsless(response.url).startswith(tuple(self.httpless_start_urls)):
            return

        for email in self.get_emails(response.text):
            yield {'email': email}
            #yield {'email': email, 'link': response.url}
        for link in response.css('a::attr(href)').extract():
            link = response.urljoin(link)

            # First check as the setting doesn't seem to work as expected in scrapy. Will keep trying to load links after
            # MAX_DEPTH even if it isn't actually allowing them to process further.
            if response.meta["depth"] < self.custom_settings['DEPTH_LIMIT'] and self.is_valid_link(link) is True:

                # Add this httpless url to the visited list. Exclude any trailing slash marks for consistency.
                self.existing_visited.add(re.sub(r'\/$', '', self.httpsless(link)))

                # Return this link to parse
                yield scrapy.Request(link, callback=self.parse,)


    def is_valid_link(self, l):
        # Get the httpless version of the url so that http and https are treated the same.
        l = self.httpsless(l)

        guessed_type = mimetypes.guess_type(l.split('?')[0])
        # Ensure that we don't parse things like images or pdfs
        if guessed_type[0] is None or guessed_type[0].startswith('text'):
            # Ensure that we stick only to this domain.
            if l.startswith(tuple(self.httpless_start_urls)):
                # Exclude sites we have already visited
                if l not in self.existing_visited:
                    return True

        return False

    def httpsless(self, l):
        """Returns a httpless version of the url. """
        return re.sub(r'http[s]*\:\/\/', '', l)

    def get_emails(self, s):
        """Returns an iterator of matched emails found in string s. """

        for email in re.findall(self.regex, s):
            cleaned_email = self.clean_email(email[0])
            if cleaned_email not in self.matched_emails:
                if self.is_email(cleaned_email):
                    self.matched_emails.add(cleaned_email)
                    yield cleaned_email


    def is_email(self, email):
        """Holds tests to determine whether a matched email really is an email.

        Returns False or True.
        """

        # Determine that this wasn't some weirdly named file that matched the regex. Ex: pic@me.jpg
        if mimetypes.guess_type(email)[0] is not None and mimetypes.guess_type(email)[0].startswith(('image', 'video')):
            return False

        # Determine that it isn't a phone number. Ex: me@999.999.9999
        if re.match(r'.+@[\d\.]+$', email):
            return False

        return True


    def clean_email(self, email):
        """Holds functions to clean the email to a single format. For now, this just takes " at " and replaces it with
        "@". and " dot " with ".". Additionally, some emails had a url encoded space before them that I am removing.
        In the future, more logic to standardize the email response should be added here as additional email detection
        cases are discovered.

        Returns a String that is the cleaned email with replacements done.
        """

        replacements = {
            r'\sat\s': "@",
            r'\sdot\s': ".",
            r'^%20': ''
        }
        for find_match, replace_match in replacements.items():
            email = re.sub(find_match, replace_match, email)

        return email