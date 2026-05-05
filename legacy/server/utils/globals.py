from server.utils.browser import PlaywrightBrowser
import stanza

BROWSER = PlaywrightBrowser()
# NLP = stanza.Pipeline('multilingual')
NLP = stanza.Pipeline('de')

