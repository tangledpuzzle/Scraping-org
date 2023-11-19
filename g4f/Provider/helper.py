from __future__ import annotations

import sys
import asyncio
import webbrowser
import random
import string
import secrets
import time
from os              import path
from asyncio         import AbstractEventLoop
from platformdirs    import user_config_dir
from browser_cookie3 import (
    chrome,
    chromium,
    opera,
    opera_gx,
    brave,
    edge,
    vivaldi,
    firefox,
    BrowserCookieError
)
try: 
    from selenium.webdriver.remote.webdriver import WebDriver 
except ImportError: 
    class WebDriver(): 
        pass
try:
    from undetected_chromedriver import Chrome, ChromeOptions
except ImportError:
    class Chrome():
        def __init__():
            raise RuntimeError('Please install the "undetected_chromedriver" package')
    class ChromeOptions():
        def add_argument():
            pass
try:
    from pyvirtualdisplay import Display
except ImportError:
    pass

from ..typing import Dict, Messages, Union, Tuple
from .. import debug

# Change event loop policy on windows
if sys.platform == 'win32':
    if isinstance(
        asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Local Cookie Storage
_cookies: Dict[str, Dict[str, str]] = {}

# If event loop is already running, handle nested event loops
# If "nest_asyncio" is installed, patch the event loop.
def get_event_loop() -> AbstractEventLoop:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
            return asyncio.get_event_loop()
    try:
        event_loop = asyncio.get_event_loop()
        if not hasattr(event_loop.__class__, "_nest_patched"):
            import nest_asyncio
            nest_asyncio.apply(event_loop)
        return event_loop
    except ImportError:
        raise RuntimeError(
            'Use "create_async" instead of "create" function in a running event loop. Or install the "nest_asyncio" package.'
        )

def init_cookies():
    urls = [
        'https://chat-gpt.org',
        'https://www.aitianhu.com',
        'https://chatgptfree.ai',
        'https://gptchatly.com',
        'https://bard.google.com',
        'https://huggingface.co/chat',
        'https://open-assistant.io/chat'
    ]

    browsers = ['google-chrome', 'chrome', 'firefox', 'safari']

    def open_urls_in_browser(browser):
        b = webbrowser.get(browser)
        for url in urls:
            b.open(url, new=0, autoraise=True)

    for browser in browsers:
        try:
            open_urls_in_browser(browser)
            break 
        except webbrowser.Error:
            continue

# Load cookies for a domain from all supported browsers.
# Cache the results in the "_cookies" variable.
def get_cookies(domain_name=''):
    if domain_name in _cookies:
        return _cookies[domain_name]
    def g4f(domain_name):
        user_data_dir = user_config_dir("g4f")
        cookie_file = path.join(user_data_dir, "Default", "Cookies")
        return [] if not path.exists(cookie_file) else chrome(cookie_file, domain_name)

    cookies = {}
    for cookie_fn in [g4f, chrome, chromium, opera, opera_gx, brave, edge, vivaldi, firefox]:
        try:
            cookie_jar = cookie_fn(domain_name=domain_name)
            if len(cookie_jar) and debug.logging:
                print(f"Read cookies from {cookie_fn.__name__} for {domain_name}")
            for cookie in cookie_jar:
                if cookie.name not in cookies:
                    cookies[cookie.name] = cookie.value
        except BrowserCookieError as e:
            pass
    _cookies[domain_name] = cookies
    return _cookies[domain_name]


def format_prompt(messages: Messages, add_special_tokens=False) -> str:
    if not add_special_tokens and len(messages) <= 1:
        return messages[0]["content"]
    formatted = "\n".join([
        f'{message["role"].capitalize()}: {message["content"]}'
        for message in messages
    ])
    return f"{formatted}\nAssistant:"


def get_browser(
    user_data_dir: str = None,
    headless: bool = False,
    proxy: str = None,
    options: ChromeOptions = None
) -> Chrome:
    if user_data_dir == None:
        user_data_dir = user_config_dir("g4f")
    if proxy:
        if not options:
            options = ChromeOptions()
        options.add_argument(f'--proxy-server={proxy}')
    return Chrome(options=options, user_data_dir=user_data_dir, headless=headless)

class WebDriverSession():
    def __init__(
        self,
        web_driver: WebDriver = None,
        user_data_dir: str = None,
        headless: bool = False,
        virtual_display: bool = False,
        proxy: str = None,
        options: ChromeOptions = None
    ):
        self.web_driver = web_driver
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.virtual_display = virtual_display
        self.proxy = proxy
        self.options = options
    
    def reopen(
        self,
        user_data_dir: str = None,
        headless: bool = False,
        virtual_display: bool = False
    ) -> WebDriver:
        if user_data_dir == None:
            user_data_dir = self.user_data_dir
        self.default_driver.quit()
        if not virtual_display and self.virtual_display:
            self.virtual_display.stop()
        self.default_driver = get_browser(user_data_dir, headless, self.proxy)
        return self.default_driver

    def __enter__(self) -> WebDriver:
        if self.web_driver:
            return self.web_driver
        if self.virtual_display == True:
            self.virtual_display = Display(size=(1920,1080))
            self.virtual_display.start()
        self.default_driver = get_browser(self.user_data_dir, self.headless, self.proxy, self.options)
        return self.default_driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.default_driver:
            self.default_driver.close()
            time.sleep(0.1)
            self.default_driver.quit()
        if self.virtual_display:
            self.virtual_display.stop()

def get_random_string(length: int = 10) -> str:
    return ''.join(
        random.choice(string.ascii_lowercase + string.digits)
        for _ in range(length)
    )


def get_random_hex() -> str:
    return secrets.token_hex(16).zfill(32)