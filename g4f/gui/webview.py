import webview
try:
    from platformdirs import user_config_dir
    has_platformdirs = True
except ImportError:
    has_platformdirs = False

from g4f.gui.run import gui_parser
from g4f.gui.server.api import Api
import g4f.version
import g4f.debug

def run_webview(
    debug: bool = False,
    storage_path: str = None
):
    webview.create_window(
        f"g4f - {g4f.version.utils.current_version}",
        "client/index.html",
        text_select=True,
        js_api=Api(),
    )
    if has_platformdirs and storage_path is None:
        storage_path = user_config_dir("g4f-webview")
    webview.start(
        private_mode=False,
        storage_path=storage_path,
        debug=debug,
        ssl=True
    )

if __name__ == "__main__":
    parser = gui_parser()
    args = parser.parse_args()
    if args.debug:
        g4f.debug.logging = True
    run_webview(args.debug)