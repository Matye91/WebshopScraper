# speed test mode (runs the program for the given minutes and stops after, while also prompting the Average CPU and Max Memory Usafe)
SPEED_TEST_MODE = False
SPEED_TEST_DURATION = 5 * 60

# set the quantity of simultaneous scraping tasks (depending on your CPU power and the target website server)
SIMULTANEOUS_SCRAPS = 50

# set the timeout for the response of the session.get call to the target website [s]
RESPONSE_TIMEOUT = 20

# set the retries of the same URL after timeout#
RESPONSE_RETRY = 3

# General blacklist components
GENERAL_BLACKLIST = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com", "pinterest.com", "mailto", "tel"]

# general blacklist file extentions
EXCLUDED_EXTENSIONS = ('.pdf', '.PDF', '.jpg', '.png', '.zip', '.docx')

# Default blacklist components (needs to be separated with line-breaks or will show wrong in GUI)
DEFAULT_BLACKLIST = """/account
/agbs
/agb
/cart
/impressum
/kontakt
/contact
/datenschutz
/über-uns
/ueber-uns
/de/de/
/en"""