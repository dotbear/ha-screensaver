"""Regression checks for doorbell expiry, ingress assets and HA control boundaries."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('screensaver', ROOT / 'ha-screensaver/app.py')
screensaver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screensaver)


class DoorbellTests(unittest.TestCase):
    def setUp(self):
        self.config = {**screensaver.DEFAULT_CONFIG, 'doorbell_entity': 'input_datetime.doorbell'}
        self.client = screensaver.app.test_client()

    def state(self, timestamp, state='2026-11-05 21:00:00'):
        return {'state': state, 'attributes': {'timestamp': timestamp, 'access_token': 'secret'}}

    def test_recent_ring_has_stable_id_and_absolute_expiry(self):
        result = screensaver.doorbell_status(self.state(1000.75), self.config, 1010)
        self.assertTrue(result['active'])
        self.assertEqual(result['ring_id'], 'input_datetime.doorbell:1000')
        self.assertEqual(result['expires_at'], 1060)
        self.assertNotIn('secret', json.dumps(result))
        restored = screensaver.doorbell_status(self.state(1000), self.config, 1010)
        self.assertEqual(result['ring_id'], restored['ring_id'])

    def test_old_restored_ring_and_future_ring_are_inactive(self):
        for timestamp in (100, 1060):
            with self.subTest(timestamp=timestamp):
                self.assertFalse(screensaver.doorbell_status(self.state(timestamp), self.config, 1000)['active'])

    def test_bad_helper_states_never_ring(self):
        states = [None, {}, {'attributes': None}]
        states += [self.state(value) for value in (None, '1000', True, float('nan'), float('inf'), 0)]
        states += [self.state(1000, state) for state in ('unknown', 'unavailable')]
        for state in states:
            with self.subTest(state=state):
                self.assertFalse(screensaver.doorbell_status(state, self.config, 1010)['active'])

    def test_disabled_doorbell_does_not_contact_ha(self):
        with patch.object(screensaver, 'load_config', return_value=screensaver.DEFAULT_CONFIG), \
                patch.object(screensaver.urllib.request, 'urlopen') as upstream:
            response = self.client.get('/api/doorbell')
        self.assertFalse(response.json['active'])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        upstream.assert_not_called()

    def test_ha_outage_is_distinct_from_no_ring(self):
        with patch.object(screensaver, 'load_config', return_value=self.config), \
                patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'private'}), \
                patch.object(screensaver.urllib.request, 'urlopen', side_effect=TimeoutError):
            response = self.client.get('/api/doorbell')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private', response.text)

    def test_helper_timestamp_uses_server_clock_and_never_exposes_attributes(self):
        with patch.object(screensaver, 'load_config', return_value=self.config), \
                patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'private'}), \
                patch.object(screensaver.time, 'time', return_value=1010), \
                patch.object(screensaver.urllib.request, 'urlopen') as upstream:
            upstream.return_value.__enter__.return_value.read.return_value = json.dumps(self.state(1000)).encode()
            response = self.client.get('/api/doorbell')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['server_time'], 1010)
        self.assertTrue(response.json['active'])
        self.assertNotIn('secret', response.text)


class AppRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = screensaver.app.test_client()

    def test_photo_names_are_encoded_and_assets_resolve_under_ingress(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'family #1?.jpg').write_bytes(b'not an actual photo')
            with patch.object(screensaver, 'HAS_PILLOW', False):
                photos = screensaver.get_image_files(directory, motion_enabled=False)
        self.assertEqual(photos[0]['url'], 'photos/family%20%231%3F.jpg')
        self.assertEqual(urljoin('https://ha.example/api/hassio_ingress/id/', photos[0]['url']),
                         'https://ha.example/api/hassio_ingress/id/photos/family%20%231%3F.jpg')

    def test_media_controls_reject_cross_site_form_posts(self):
        with patch.object(screensaver, '_call_media_service') as service:
            response = self.client.post('/api/media/play_pause', data={})
            self.assertEqual(response.status_code, 415)
            service.assert_not_called()
        response = self.client.options('/api/media/play_pause', headers={
            'Origin': 'https://another-site.example', 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type',
        })
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_photo_route_cannot_serve_other_shared_files(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'private.txt').write_text('private document')
            config = {**screensaver.DEFAULT_CONFIG, 'photos_folder': directory}
            with patch.object(screensaver, 'load_config', return_value=config):
                response = self.client.get('/photos/private.txt')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('private document', response.text)

    def test_bad_volume_payload_is_400_and_never_calls_ha(self):
        with patch.object(screensaver, '_call_media_service') as service:
            for body in ([1], {'volume_level': 'loud'}, {'volume_level': True},
                         {'volume_level': 'NaN'}, {'volume_level': {'value': 1}}):
                with self.subTest(body=body):
                    self.assertEqual(self.client.post('/api/media/volume', json=body).status_code, 400)
            service.assert_not_called()

    def test_volume_clamps_and_ha_failures_are_reported(self):
        with patch.object(screensaver, '_call_media_service', return_value=True) as service:
            self.assertEqual(self.client.post('/api/media/volume', json={'volume_level': 5}).status_code, 200)
            service.assert_called_once_with('volume_set', {'volume_level': 1.0})
        with patch.object(screensaver, '_call_media_service', return_value=False):
            self.assertEqual(self.client.post('/api/media/play_pause', json={}).status_code, 502)

    def test_album_proxy_cannot_read_arbitrary_ha_endpoints(self):
        with patch.object(screensaver.urllib.request, 'build_opener') as upstream:
            for url in ('/api/states', '/api/hassio/backups', 'https://outside.example/image',
                        '/api/media_player_proxy/../states', '/api/media_player_proxy/%2e%2e/states'):
                with self.subTest(url=url):
                    response = self.client.get('/api/media/image', query_string={'url': url})
                    self.assertEqual(response.status_code, 400)
            upstream.assert_not_called()

    def test_source_replacement_in_same_second_invalidates_decoded_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'photo.heic')
            source.write_bytes(b'first')
            os.utime(source, ns=(100000000001, 100000000001))
            before = screensaver._cache_key(source)
            source.write_bytes(b'other')
            os.utime(source, ns=(100000000002, 100000000002))
            self.assertNotEqual(before, screensaver._cache_key(source))

    def test_concurrent_requests_only_decode_a_source_once(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, 'photo.heic')
            source.write_bytes(b'photo')
            cache = Path(directory, 'cache')
            entered = threading.Event()

            def decode(command, timeout):
                entered.set()
                time.sleep(0.05)
                Path(command[-1]).write_bytes(b'jpeg')
                return True

            with patch.object(screensaver, 'CACHE_DIR', cache), \
                    patch.object(screensaver, 'HEIF_CONVERT_BIN', 'fake-heif'), \
                    patch.object(screensaver, '_run_tool', side_effect=decode) as decoder, \
                    ThreadPoolExecutor(2) as pool:
                first = pool.submit(screensaver.heif_jpeg, source)
                self.assertTrue(entered.wait(1))
                second = pool.submit(screensaver.heif_jpeg, source)
                self.assertEqual(first.result(), second.result())
                self.assertEqual(decoder.call_count, 1)

    def test_pruning_never_deletes_an_in_progress_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            completed = cache / ('a' * 40 + '.jpg')
            scratch = cache / ('b' * 40 + '.123.tmp.jpg')
            completed.write_bytes(b'jpeg')
            scratch.write_bytes(b'work in progress')
            with patch.object(screensaver, 'CACHE_DIR', cache), patch.object(screensaver, 'CACHE_MAX_BYTES', 0):
                screensaver._prune_cache()
            self.assertFalse(completed.exists())
            self.assertTrue(scratch.exists())

    def test_geocoding_rate_limit_is_shared_by_concurrent_scans(self):
        with tempfile.TemporaryDirectory() as directory:
            started = []

            def geocode(lat, lng):
                started.append(time.monotonic())
                return 'Faaborg, Denmark'

            with patch.object(screensaver, 'GEOCACHE_FILE', Path(directory, 'locations.json')), \
                    patch.object(screensaver, '_nominatim_reverse', side_effect=geocode) as reverse, \
                    ThreadPoolExecutor(2) as pool:
                first = pool.submit(screensaver._cached_location, 55.1, 10.2)
                second = pool.submit(screensaver._cached_location, 55.2, 10.3)
                self.assertEqual(first.result(), 'Faaborg, Denmark')
                self.assertEqual(second.result(), 'Faaborg, Denmark')
                self.assertGreaterEqual(started[1] - started[0], 0.95)
                screensaver._cached_location(55.1, 10.2)
                self.assertEqual(reverse.call_count, 2, 'existing coordinates use the shared disk cache')


if __name__ == '__main__':
    unittest.main()
