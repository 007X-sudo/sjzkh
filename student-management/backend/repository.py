"""JSON 读写层：首次初始化五人；写入成功后原子替换数据文件。"""
import json
import os
from pathlib import Path
import tempfile

from models import Student

SAMPLE_STUDENTS = [
    {'student_id': '2026001', 'name': '林知远', 'class_name': '机械 2601', 'chinese': 88, 'math': 96, 'english': 85},
    {'student_id': '2026002', 'name': '陈雨桐', 'class_name': '机械 2601', 'chinese': 95, 'math': 89, 'english': 93},
    {'student_id': '2026003', 'name': '周予安', 'class_name': '自动化 2602', 'chinese': 82, 'math': 92, 'english': 87},
    {'student_id': '2026004', 'name': '许星禾', 'class_name': '自动化 2602', 'chinese': 91, 'math': 85, 'english': 96},
    {'student_id': '2026005', 'name': '沈一舟', 'class_name': '机械 2601', 'chinese': 76, 'math': 88, 'english': 80},
]


class StudentRepository:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            students = [Student.from_dict(row) for row in SAMPLE_STUDENTS]
            self.save(students)
            return students
        rows = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            raise ValueError('数据文件必须是学生列表；原文件未覆盖')
        students = [Student.from_dict(row) for row in rows]
        if len({s.student_id for s in students}) != len(students):
            raise ValueError('数据文件含重复学号；原文件未覆盖')
        return students

    def save(self, students):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=str(self.path.parent), suffix='.tmp', delete=False) as file:
                temporary = Path(file.name)
                # 持久化基础字段；total 不落库。
                json.dump([s.to_dict(include_total=False) for s in students],
                          file, ensure_ascii=False, indent=2, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(str(temporary), str(self.path))
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
