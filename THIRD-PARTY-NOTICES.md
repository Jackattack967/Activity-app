# Third-party notices

Activity Schedule Dashboard is built on open-source software. This file
credits every third-party package the app installs, with its license.

The app's own front-end (`static/app.js`, `static/style.css`, `static/sw.js`,
the templates) contains no third-party or copied code, loads no CDN scripts,
and embeds no third-party fonts or icon sets. Everything below is a Python
package pulled in by `requirements.txt`.

Versions listed are those resolved at the time of writing. `requirements.txt`
pins minimums, so newer compatible versions may be installed — the licenses
below are stable across those updates, but re-check if a major version
changes.

## Direct dependencies

These are the packages named in `requirements.txt`.

| Package | Version | License | Used for |
|---|---|---|---|
| [Flask](https://github.com/pallets/flask/) | 3.1.3 | BSD-3-Clause | The web framework — routing, requests, templates |
| [Werkzeug](https://github.com/pallets/werkzeug/) | 3.1.8 | BSD-3-Clause | Flask's underlying HTTP layer; `ProxyFix` for Render's TLS proxy |
| [Jinja2](https://github.com/pallets/jinja/) | 3.1.6 | BSD-3-Clause | HTML templating (`templates/*.html`) |
| [Flask-SQLAlchemy](https://github.com/pallets-eco/flask-sqlalchemy/) | 3.1.1 | BSD-3-Clause | Database models and sessions (`models.py`) |
| [SQLAlchemy](https://www.sqlalchemy.org) | 2.0.52 | MIT | The ORM underneath Flask-SQLAlchemy |
| [Flask-Login](https://github.com/maxcountryman/flask-login) | 0.6.3 | MIT | Signed-in session handling |
| [Authlib](https://github.com/authlib/authlib) | 1.7.2 | BSD-3-Clause | Google OAuth 2.0 / OpenID Connect sign-in (`auth.py`) |
| [Requests](https://github.com/psf/requests) | 2.34.2 | Apache-2.0 | HTTP calls to the municipal portals and email APIs |
| [psycopg2-binary](https://psycopg.org/) | 2.9.12 | LGPL-3.0-or-later with exceptions | PostgreSQL driver (see note below) |
| [Gunicorn](https://gunicorn.org) | 26.1.0 | MIT | Production WSGI server on Render |
| [pywebpush](https://github.com/web-push-libs/pywebpush) | 2.4.0 | MPL-2.0 | Sending Web Push notifications (`watcher.py`) |
| [py-vapid](https://github.com/mozilla-services/vapid) | 1.9.4 | MPL-2.0 | VAPID signing for Web Push |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.3 | BSD-3-Clause | Loading `.env` during local development |
| [tzdata](https://github.com/python/tzdata) | 2026.3 | Apache-2.0 | IANA time zone database (`America/Vancouver`) |

## Transitive dependencies

Pulled in automatically by the packages above.

| Package | Version | License |
|---|---|---|
| [aiohappyeyeballs](https://github.com/aio-libs/aiohappyeyeballs) | 2.7.1 | PSF-2.0 |
| [aiohttp](https://github.com/aio-libs/aiohttp) | 3.14.3 | Apache-2.0 AND MIT |
| [aiosignal](https://github.com/aio-libs/aiosignal) | 1.4.0 | Apache-2.0 |
| [attrs](https://github.com/python-attrs/attrs) | 26.1.0 | MIT |
| [blinker](https://github.com/pallets-eco/blinker/) | 1.9.0 | MIT |
| [certifi](https://github.com/certifi/python-certifi) | 2026.7.22 | MPL-2.0 |
| [cffi](https://github.com/python-cffi/cffi) | 2.1.1 | MIT-0 |
| [charset-normalizer](https://github.com/jawah/charset_normalizer) | 3.5.1 | MIT |
| [click](https://github.com/pallets/click/) | 8.4.2 | BSD-3-Clause |
| [colorama](https://github.com/tartley/colorama) | 0.4.6 | BSD-3-Clause |
| [cryptography](https://github.com/pyca/cryptography) | 50.0.0 | Apache-2.0 OR BSD-3-Clause |
| [frozenlist](https://github.com/aio-libs/frozenlist) | 1.8.0 | Apache-2.0 |
| [greenlet](https://greenlet.readthedocs.io) | 3.5.5 | MIT AND PSF-2.0 |
| [http-ece](https://github.com/martinthomson/encrypted-content-encoding) | 1.2.1 | MIT |
| [idna](https://github.com/kjd/idna) | 3.19 | BSD-3-Clause |
| [itsdangerous](https://github.com/pallets/itsdangerous/) | 2.2.0 | BSD-3-Clause |
| [joserfc](https://github.com/authlib/joserfc) | 1.7.4 | BSD-3-Clause |
| [MarkupSafe](https://github.com/pallets/markupsafe/) | 3.0.3 | BSD-3-Clause |
| [multidict](https://github.com/aio-libs/multidict) | 6.7.1 | Apache-2.0 |
| [propcache](https://github.com/aio-libs/propcache) | 0.5.2 | Apache-2.0 |
| [pycparser](https://github.com/eliben/pycparser) | 3.0 | BSD-3-Clause |
| [typing-extensions](https://github.com/python/typing_extensions) | 4.16.0 | PSF-2.0 |
| [urllib3](https://github.com/urllib3/urllib3) | 2.7.0 | MIT |
| [yarl](https://github.com/aio-libs/yarl) | 1.24.5 | Apache-2.0 |

## Development-only tools

Not installed on the server and not part of the deployed app.

| Package | Version | License | Used for |
|---|---|---|---|
| [Pillow](https://github.com/python-pillow/Pillow) | 12.3.0 | MIT-CMU | Generating the app icons in `gen_icons.py` |

## Note on psycopg2 and the LGPL

`psycopg2-binary` is licensed under the LGPL v3 with an exception permitting
use with software under other licenses. The LGPL's source-sharing obligation
is triggered by *distributing* the library. This app runs psycopg2 on its own
server and never ships it to users, so no additional obligation applies here.
The notice above is provided as attribution. If the app is ever repackaged and
distributed as a bundle that includes psycopg2, revisit this.

## Data sources

Schedule data is read from the public PerfectMind booking portals operated by
the **City of Coquitlam** and the **City of Port Moody**. This project is
unofficial and is not affiliated with, endorsed by, or operated by either city
or by PerfectMind. All schedule information remains the property of its
respective source; registration and payment happen on the cities' own sites.

## Reproducing this list

```bash
pip install pip-licenses
pip-licenses --format=markdown --with-urls
```
