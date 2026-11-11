"""独立业务层：不依赖终端、HTTP 或前端。"""
from threading import RLock
from models import Student


class NotFoundError(ValueError):
    pass


class DuplicateError(ValueError):
    pass


class StudentService:
    def __init__(self, repository):
        self.repository = repository
        self._students = repository.load()
        self._lock = RLock()

    def list_students(self, student_id=None, sort_by=None, order='asc'):
        with self._lock:
            rows = list(self._students)
        if student_id is not None:
            rows = [s for s in rows if s.student_id == student_id.strip()]
        if order not in ('asc', 'desc'):
            raise ValueError('排序方向仅支持 asc 或 desc')
        if sort_by:
            if sort_by not in ('chinese', 'math', 'english', 'total'):
                raise ValueError('只能按语文、数学、英语或总成绩排序')
            rows.sort(key=lambda s: getattr(s, sort_by), reverse=order == 'desc')
        return [s.to_dict() for s in rows]

    def get_student(self, student_id):
        with self._lock:
            for student in self._students:
                if student.student_id == student_id:
                    return student.to_dict()
        raise NotFoundError('未找到该学号的学生')

    def _save(self, students):
        # 先保存，成功后再替换内存数据，防止保存失败但界面看似已成功。
        self.repository.save(students)
        self._students = students

    def add_student(self, data):
        student = Student.from_dict(data)
        with self._lock:
            if any(s.student_id == student.student_id for s in self._students):
                raise DuplicateError('学号已存在，请使用唯一学号')
            self._save(self._students + [student])
        return student.to_dict()

    def update_student(self, student_id, changes):
        if not isinstance(changes, dict):
            raise ValueError('修改内容必须是一个对象')
        with self._lock:
            for index, current in enumerate(self._students):
                if current.student_id != student_id:
                    continue
                merged = current.to_dict(include_total=False)
                merged.update(changes)  # 未提供的字段保留原值，对应 CLI 的“回车保留”。
                student = Student.from_dict(merged)
                if any(s.student_id == student.student_id for i, s in enumerate(self._students) if i != index):
                    raise DuplicateError('修改后的学号已存在')
                updated = list(self._students)
                updated[index] = student
                self._save(updated)
                return student.to_dict()
        raise NotFoundError('未找到要修改的学生')

    def delete_student(self, student_id):
        with self._lock:
            if not any(s.student_id == student_id for s in self._students):
                raise NotFoundError('未找到要删除的学生')
            self._save([s for s in self._students if s.student_id != student_id])
