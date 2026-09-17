"""Start the locally installed Folio desktop window on an available port."""

import socket
import sys

if sys.platform == 'darwin':
    from Foundation import NSBundle, NSProcessInfo

    bundle = NSBundle.mainBundle()
    for info in (bundle.infoDictionary(), bundle.localizedInfoDictionary()):
        if info is not None:
            info['CFBundleName'] = 'Folio'
            info['CFBundleDisplayName'] = 'Folio'
    NSProcessInfo.processInfo().setProcessName_('Folio')

from nicegui_app import main


if __name__ == '__main__':
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    sys.argv = [sys.argv[0], '--native', '--port', str(port)]
    main()
