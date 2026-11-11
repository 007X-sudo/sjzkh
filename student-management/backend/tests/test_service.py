"""业务规则、JSON 持久化和真实 HTTP 接口测试。"""
import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from app import create_server
from repository import StudentRepository
from service import DuplicateError, NotFoundError, StudentService


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'students.json'
        self.repository = StudentRepository(self.path)
        self.service = StudentService(self.repository)
        self.student = dict(student_id='S006', name='测试同学', class_name='测试班', chinese=80, math=90, english=100)

    def test_initial_five_and_total_not_stored(self):
        self.assertEqual(len(self.service.list_students()), 5)
        rows = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertTrue(all('total' not in row for row in rows))
        self.assertEqual(self.service.get_student('2026001')['total'], 269)

    def test_add_and_reload(self):
        self.service.add_student(self.student)
        loaded = StudentService(StudentRepository(self.path))
        self.assertEqual(loaded.get_student('S006')['name'], '测试同学')

    def test_duplicate_id(self):
        self.service.add_student(self.student)
        with self.assertRaises(DuplicateError):
            self.service.add_student(self.student)

    def test_score_range_and_type(self):
        for invalid in [-1, 101, True, None, '90', float('nan'), float('inf')]:
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(ValueError):
                    self.service.add_student(dict(self.student, math=invalid))

    def test_zero_and_hundred_valid(self):
        row = self.service.add_student(dict(self.student, chinese=0, math=100, english=0))
        self.assertEqual(row['total'], 100)

    def test_partial_update_and_total(self):
        old = self.service.get_student('2026001')
        row = self.service.update_student('2026001', {'math': 60})
        self.assertEqual(row['name'], old['name'])
        self.assertEqual(row['total'], old['chinese'] + 60 + old['english'])
        stored = json.loads(self.path.read_text(encoding='utf-8'))[0]
        self.assertNotIn('total', stored)

    def test_change_id_checks_uniqueness(self):
        with self.assertRaises(DuplicateError):
            self.service.update_student('2026001', {'student_id': '2026002'})
        self.service.update_student('2026001', {'student_id': 'NEW-ID'})
        self.assertEqual(self.service.get_student('NEW-ID')['name'], '林知远')
        with self.assertRaises(NotFoundError):
            self.service.get_student('2026001')

    def test_exact_search(self):
        self.assertEqual(len(self.service.list_students(student_id='2026001')), 1)
        self.assertEqual(self.service.list_students(student_id='2026'), [])

    def test_eight_sort_combinations(self):
        for key in ['chinese', 'math', 'english', 'total']:
            for order in ['asc', 'desc']:
                with self.subTest(key=key, order=order):
                    values = [r[key] for r in self.service.list_students(sort_by=key, order=order)]
                    self.assertEqual(values, sorted(values, reverse=order == 'desc'))

    def test_delete_and_missing(self):
        self.service.delete_student('2026001')
        self.assertEqual(len(StudentService(StudentRepository(self.path)).list_students()), 4)
        with self.assertRaises(NotFoundError):
            self.service.delete_student('2026001')

    def test_save_failure_keeps_memory(self):
        before = self.service.list_students()
        with patch.object(self.repository, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.service.add_student(self.student)
        self.assertEqual(self.service.list_students(), before)

    def test_corrupt_file_not_overwritten(self):
        self.path.write_text('broken json', encoding='utf-8')
        with self.assertRaises(ValueError):
            StudentService(StudentRepository(self.path))
        self.assertEqual(self.path.read_text(encoding='utf-8'), 'broken json')

    def test_total_cannot_be_manually_set(self):
        with self.assertRaises(ValueError):
            self.service.update_student('2026001', {'total': 999})


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'students.json'
        self.server = create_server(self.path, port=0)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def request(self, method, path, data=None, origin='null'):
        headers = {'Origin': origin}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(req)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers

    def test_full_crud_and_cors(self):
        code, data, headers = self.request('GET', '/api/students')
        self.assertEqual((code, data['count']), (200, 5))
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'null')
        new = dict(student_id='S006', name='接口测试', class_name='测试班', chinese=0, math=100, english=80)
        self.assertEqual(self.request('POST', '/api/students', new)[0], 201)
        self.assertEqual(self.request('POST', '/api/students', new)[0], 409)
        self.assertEqual(self.request('PATCH', '/api/students/S006', {'math': 60})[1]['student']['total'], 140)
        self.assertEqual(self.request('DELETE', '/api/students/S006')[0], 200)
        self.assertEqual(self.request('GET', '/api/students/S006')[0], 404)

    def test_invalid_json_shapes_and_scores(self):
        self.assertEqual(self.request('POST', '/api/students', [1, 2])[0], 400)
        invalid = dict(student_id='S006', name='测试', class_name='测试班', chinese=-1, math=100, english=80)
        self.assertEqual(self.request('POST', '/api/students', invalid)[0], 400)
        self.assertEqual(self.request('GET', '/api/students?sort_by=name')[0], 400)

    def test_external_origin_rejected(self):
        self.assertEqual(self.request('GET', '/api/students', origin='https://example.com')[0], 403)

    def test_root_is_json_not_frontend(self):
        code, data, headers = self.request('GET', '/')
        self.assertEqual(code, 200)
        self.assertEqual(data['app'], 'student-mgmt')
        self.assertIn('application/json', headers['Content-Type'])


if __name__ == '__main__':
    unittest.main()
