# Screensaver review — 2026-11-05

Reviewed the Flask backend, browser class/HTML, media and photo helpers, Docker
build, startup script, local runner, and release instructions while adding the
doorbell camera override. The single-file backend/frontend structure is retained.

The 2.5.0 changelog lists the fixes. The most consequential findings were:

- Every photo was given an image source immediately, decoding the whole library
  on a memory-limited tablet. The browser now loads one image, plus the outgoing
  image during a crossfade, and releases the previous source afterwards.
- Absolute asset paths escaped HA ingress, unescaped `#`/`?` in photo names broke
  retrieval, and the LAN HTTP iframe failed under HTTPS ingress. Assets are now
  relative/encoded and ingress uses the containing HA origin.
- Demo transport/volume buttons posted to real HA service routes. They now stay
  inert in demo mode. A late media response could also reopen music mode after
  leaving it; mode changes now invalidate old responses.
- The app exposed a Supervisor-authenticated proxy to arbitrary `/api/` paths,
  served non-photo files from the configured share, and allowed wildcard CORS on
  privileged media controls. The proxy now only serves image endpoints without
  redirects, photo delivery checks image extensions, and controls require JSON
  without cross-origin permission. These controls preserve the app's existing
  trusted-LAN/direct-port access model; they do not add another login.
- Per-PID conversion scratch names collided between threads, pruning could delete
  unfinished conversions, JSON caches could be read half-written, and the
  geocoder's rate limit applied separately to each request. Cross-process file
  locks, atomic cache replacement, and a shared geocoding limit address these.
- Shell interpolation could produce invalid JSON options. Startup now serializes
  the Supervisor's validated JSON. The local runner no longer installs into the
  system environment or overwrites an existing local config.

Backend regressions are covered by `tests/test_app.py`; the silent browser
scenarios are in `tests/browser.cjs`. They cover expiry and server-clock handling,
restart-stable IDs, unavailable/invalid helper values, request boundaries,
concurrent conversion/geocoding, cache invalidation, camera priority, dismissal,
timeout, repeated rings, mode restoration, image bounds, and ingress-origin logic.

Dependency/image versions were checked against primary release sources:
[Flask changes](https://flask.palletsprojects.com/en/stable/changes/),
[Gunicorn on PyPI](https://pypi.org/project/gunicorn/), and the published HA
[aarch64](https://github.com/home-assistant/docker-base/pkgs/container/aarch64-base),
[amd64](https://github.com/home-assistant/docker-base/pkgs/container/amd64-base), and
[armv7](https://github.com/home-assistant/docker-base/pkgs/container/armv7-base)
base images. The dependency pins are Flask 3.1.3 and Gunicorn 26.2.0, both verified
by an actual install. The base is 3.22, available across the existing architecture
matrix. Runtime validation is on amd64 locally and the household's aarch64 Green;
armv7 remains a compatibility target without a runtime validation here.

## Remaining design limits

- Browser same-origin rules prevent seeing all activity *inside* a cross-origin
  HA iframe. The existing focus/blur idle heuristic detects entry, rather than
  every subsequent touch inside HA. In ingress the parent and iframe share an
  origin, but direct-port mode still needs an explicit activity bridge in HA or
  a kiosk application's own idle handling for fully accurate detection.
- The photo list is scanned on page load. New/deleted photos require a page
  refresh; an incremental background library refresh would be a useful follow-up.
- The camera iframe's load event proves navigation, not that a live video frame
  was decoded. Expired HA login is visible in the iframe and can be repaired by
  signing in. Camera codec/network behavior still needs checking on the actual
  tablet; a direct stream player would allow richer health reporting later.
- The direct port shares the existing trusted-LAN model for household photos and
  the configured media player. Use authenticated HA ingress when remote access
  is needed. This review does not make the standalone port a public service.
