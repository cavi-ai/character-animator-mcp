# Version and support

This documentation is for `cavi-character-animator-mcp` {{PRODUCT_VERSION}}, released as
`{{RELEASE_TAG}}` from commit `{{RELEASE_COMMIT}}`.

Versions follow Semantic Versioning and come from git tags. Before 1.0, the tool surface and result fields can
still change, and security fixes go to the latest minor release and `main`. Every change is recorded in the
repository [CHANGELOG.md](https://github.com/cavi-ai/character-animator-mcp/blob/main/CHANGELOG.md).

## What was checked

The unit tests use a scripted native bridge and synthetic export files, and the protocol and simulated evaluations
never start Character Animator, so none of them establishes the application's own behavior. The helper's menu and
chooser handling is tried in Character Animator when `character_native.swift` changes; the `native-background`
evaluation reads `character_status` and `inspect` from a running application. No Character Animator version is
recorded as checked: every result reports what the application showed, and every dispatched command is reported as
unverified until you check it. A tool that fails in your install is a bug
to report at
[the issue tracker](https://github.com/cavi-ai/character-animator-mcp/issues).

Requires Python 3.15 or newer. Only macOS is supported, because the server controls the application through the
macOS Accessibility interface and a Swift helper.

## License and trademarks

MIT licensed.

Adobe and Character Animator are either registered trademarks or trademarks of Adobe in the United States and/or
other countries. This project is not affiliated with, endorsed by, or sponsored by Adobe. It does not include or
redistribute Adobe software, puppets or project files; you supply your own licensed application.
