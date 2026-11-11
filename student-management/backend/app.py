"""纯 Python JSON API；此文件不包含或提供前端页面。"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
from urllib.parse import parse_qs, unquote, urlsplit

from repository import StudentRepository
from service import DuplicateError, NotFoundError, StudentService


def create_server(data_path=None, port=8000):
    path = Path(data_path) if data_path is not None else Path(__file__).resolve().parent / 'data' / 'students.json'
    service = StudentService(StudentRepository(path))

    class Handler(BaseHTTPRequestHandler):
        def allowed_origin(self):
            origin = self.headers.get('Origin')
            if origin == 'null':  # 允许双击打开的本地 HTML 连接 API。
                return origin
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme in ('http', 'https') and parsed.hostname in ('127.0.0.1', 'localhost'):
                    return origin
            return None

        def reply(self, status, data):
            raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            origin = self.allowed_origin()
            if origin is not None:
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            if self.headers.get('Origin') and self.allowed_origin() is None:
                self.reply(403, {'error': '仅允许本地预览页面连接'})
                return
            self.send_response(204)
            origin = self.allowed_origin()
            if origin is not None:
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

        def do_GET(self):
            self.dispatch('GET')

        def do_POST(self):
            self.dispatch('POST')

        def do_PATCH(self):
            self.dispatch('PATCH')

        def do_DELETE(self):
            self.dispatch('DELETE')

        @staticmethod
        def reject_constant(value):
            raise ValueError('成绩必须是有限数字')

        def read_body(self):
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise ValueError('请求正文必须使用 application/json')
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise ValueError('请求长度无效')
            if not 0 < length <= 65536:
                raise ValueError('请求正文不能为空且不能超过 64 KB')
            try:
                return json.loads(self.rfile.read(length).decode('utf-8'),
                    parse_constant=self.reject_constant)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise ValueError('请求正文不是有效 JSON')

        def dispatch(self, method):
            try:
                # 本地服务不接收外部网站发起的写操作。
                if self.headers.get('Origin') and self.allowed_origin() is None:
                    self.reply(403, {'error': '仅允许本地预览页面连接'})
                    return
                parsed = urlsplit(self.path)
                path = parsed.path.rstrip('/') or '/'
                if method == 'GET' and path in ('/', '/api/health'):
                    self.reply(200, {'app': 'student-mgmt', 'status': 'ok', 'message': '此服务仅提供 JSON API，请打开独立 HTML 预览。'})
                    return
                if path == '/api/students':
                    if method == 'GET':
                        query = parse_qs(parsed.query, keep_blank_values=True)
                        rows = service.list_students(student_id=query.get('student_id', [None])[0],
                            sort_by=query.get('sort_by', [None])[0], order=query.get('order', ['asc'])[0])
                        self.reply(200, {'students': rows, 'count': len(rows)})
                        return
                    if method == 'POST':
                        self.reply(201, {'student': service.add_student(self.read_body())})
                        return
                if path.startswith('/api/students/'):
                    student_id = unquote(path[len('/api/students/'):])
                    if method == 'GET':
                        self.reply(200, {'student': service.get_student(student_id)})
                        return
                    if method == 'PATCH':
                        self.reply(200, {'student': service.update_student(student_id, self.read_body())})
                        return
                    if method == 'DELETE':
                        service.delete_student(student_id)
                        self.reply(200, {'message': '学生已删除'})
                        return
                self.reply(404, {'error': '接口不存在'})
            except DuplicateError as error:
                self.reply(409, {'error': str(error)})
            except NotFoundError as error:
                self.reply(404, {'error': str(error)})
            except ValueError as error:
                self.reply(400, {'error': str(error)})
            except OSError:
                self.reply(500, {'error': '数据文件保存失败，请检查目录权限或磁盘空间'})

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    with create_server() as server:
        print('Student API: http://127.0.0.1:8000/api/students')
        print('Press Ctrl+C to stop. Frontend is a separate HTML file.')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
