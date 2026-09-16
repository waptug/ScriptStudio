# OpenShot integration

ScriptStudio reuses **libopenshot**, rather than embedding the desktop GUI in a web
page or building a new visual compositor. The installed Debian package is pinned to
`python3-openshot=0.2.7+dfsg1-4+b1` on Debian bookworm, with OpenShot's native C++ library
and matching system Python. FastAPI uses Python 3.12; a JSON subprocess bridge avoids
mixing binary Python ABIs. Qt runs offscreen. Native crashes cannot take down the API.

`openshot_runner.py` creates real `openshot.Clip`, `Keyframe`, `Timeline`, and
`FFmpegWriter` objects. Preview and final export both pass through this engine.
Native clip serialization supplies `.osp` clip/keyframe/reader metadata. FFmpeg handles
source normalization and finishing audio so it can retain explicit hold/loop coverage,
exact sample placement, sidechain ducking, AAC encoding, and full decode validation.

Official implementation references:

- [libopenshot](https://github.com/OpenShot/libopenshot)
- [Official Python example](https://github.com/OpenShot/libopenshot/blob/develop/examples/Example.py)
- [OpenShot project loader](https://github.com/OpenShot/openshot-qt/blob/v2.6.1/src/classes/project_data.py)
- [OpenShot path conversion](https://github.com/OpenShot/openshot-qt/blob/v2.6.1/src/classes/json_data.py)
- [Native project defaults](https://github.com/OpenShot/openshot-qt/blob/v2.6.1/src/settings/_default.project)

## Desktop handoff

Every final render includes `ScriptStudio-OpenShot.zip`. Extract all files into a
folder, then open `ScriptStudio.osp` in OpenShot. Relative paths make the bundle
portable between Linux, Windows, and macOS; never open just the `.osp` inside the ZIP.

The handoff contains:

- Individually editable visual clips on video/overlay/title/caption layers.
- Native scale, position, and opacity fade keyframes.
- Transparent PNG title/caption clips and SRT/WebVTT text files.
- A finished audio mix preserving ScriptStudio's exact ducking/fades.
- Original source media, narration, music/effects, reference images, and alternate
  takes in the media library, so desktop users can replace clips or remix audio.
- Immutable ScriptStudio revision/settings, asset provenance, and generation history.

Trimming/hold/loop coverage is baked into normalized visual source clips; native
transform/fade controls remain editable. Title wording can be changed in ScriptStudio
and re-exported, or replaced using OpenShot's title tools. Audio is one finishing mix,
not a promise of lossless automation transfer between different mixing engines.
Desktop edits do not synchronize back; ScriptStudio never overwrites them.

The serialization baseline is OpenShot 2.6.1/libopenshot 0.2.7. Engine-level loading,
frame rendering, and opening the exported bundle in the actual Linux OpenShot 2.6.1
desktop application under Xvfb were tested. Compatibility with newer desktop versions,
Windows, or macOS has not been tested; see [verification evidence](verification.md).

To repeat the desktop check using a final render's bundle path inside the media volume:

```bash
docker build -f backend/Dockerfile.desktop-test -t scriptstudio-desktop-test backend
docker run --rm --init --network none -v scriptstudio_media:/data \
  -v "$PWD/backend:/app:ro" scriptstudio-desktop-test \
  xvfb-run -a -s '-screen 0 1440x1000x24' \
  /usr/bin/python3 /app/tools/desktop_smoke.py \
  /data/PROJECT_ID/renders/RENDER_JOB_ID/ScriptStudio-OpenShot.zip
```

Use a fresh container/profile for each run. The check captures a screenshot and log
under `/data/tmp`; `--init` allows Xvfb signal handling to work correctly.

## Licensing and redistribution

OpenShot's desktop editor is GPL-3.0-or-later. libopenshot's official source labels
its library/example code LGPL-3.0-or-later. ScriptStudio uses the packaged dynamically
linked library and calls its public API. No desktop editor source is vendored or
modified. See the package's `/usr/share/doc/libopenshot21/copyright` and
`/usr/share/doc/python3-openshot/copyright` inside the backend image, along with
[upstream source and license](https://github.com/OpenShot/libopenshot).

When distributing an image, retain the upstream notices/licenses and make matching
source and any modifications available as required by the dependencies' licenses.
The Debian source package for this pinned build is `libopenshot 0.2.7+dfsg1-4`;
`apt-get source libopenshot` with the matching Debian source repository obtains it.
