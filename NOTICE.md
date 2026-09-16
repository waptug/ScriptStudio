# License and third-party notices

ScriptStudio source is licensed under **GPL-3.0-or-later**. See `LICENSE` for the GPL
version 3 text; you may use a later version at your option. Copyright 2026 ScriptStudio
contributors. This choice accommodates the GPL Python/Qt tooling used by the native
rendering bridge.

No affiliation with or endorsement by OpenShot, Runway, ElevenLabs, Suno, or Ollama
is implied. Provider names identify integrations; credentials and account rights
are the operator's responsibility.

- **libopenshot**: LGPL-3.0-or-later; https://github.com/OpenShot/libopenshot.
  Debian source package `libopenshot 0.2.7+dfsg1-4`, binary package
  `python3-openshot 0.2.7+dfsg1-4+b1`. Unmodified dynamically linked dependency.
- **OpenShot desktop editor**: GPL-3.0-or-later;
  https://github.com/OpenShot/openshot-qt. Installed only in the optional desktop-test
  image; no editor source is copied into ScriptStudio.
- **PyQt5**: GPL v3 or commercial license; this project uses its GPL distribution.
  https://www.riverbankcomputing.com/software/pyqt/intro.
- **FFmpeg / eSpeak NG / Qt / system fonts**: licenses and copyright notices are
  retained in the Debian image under `/usr/share/doc` and `/usr/share/common-licenses`.
  FFmpeg build options and codecs can be inspected with `ffmpeg -buildconf`.
- **React, Vite, FastAPI, SQLAlchemy, Celery, and other Python/npm dependencies**:
  their licenses remain in installed package distributions. Exact resolved versions
  are recorded in `backend/requirements.lock` and `frontend/package-lock.json`.

If redistributing container images, retain upstream notices and comply with each
component's source-distribution obligations. Matching Debian sources are available
through Debian's source repositories (`apt-get source` with deb-src enabled).
