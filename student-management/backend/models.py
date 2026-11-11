"""学生数据模型：总成绩始终根据三科成绩计算。"""
from dataclasses import asdict, dataclass
import math

FIELDS = ('student_id', 'name', 'class_name', 'chinese', 'math', 'english')
SUBJECTS = ('chinese', 'math', 'english')


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    class_name: str
    chinese: float
    math: float
    english: float

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError('学生信息必须是一个对象')
        unknown = set(data) - set(FIELDS)
        if unknown:
            raise ValueError('不支持的字段：' + ', '.join(sorted(unknown)))
        values = {}
        labels = {'student_id': '学号', 'name': '姓名', 'class_name': '班级'}
        for field, label in labels.items():
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(label + '不能为空')
            values[field] = value.strip()
        for field in SUBJECTS:
            value = data.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError('三科成绩必须为数字')
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError('每科成绩必须在 0 到 100 之间')
            values[field] = float(value)
        return cls(**values)

    @property
    def total(self):
        return round(self.chinese + self.math + self.english, 2)

    def to_dict(self, include_total=True):
        result = asdict(self)
        if include_total:
            result['total'] = self.total
        return result
