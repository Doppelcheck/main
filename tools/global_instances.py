import httpx
import wikipedia
from lingua import lingua

from tools.browser import PlaywrightBrowser

BROWSER_INSTANCE = PlaywrightBrowser()
HTTPX_SESSION = httpx.AsyncClient()

detector = lingua.LanguageDetectorBuilder.from_all_languages()
DETECTOR_BUILT = detector.build()

WIKIPEDIA_LANGUAGES = wikipedia.languages()
