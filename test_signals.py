import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ptpi.settings")
django.setup()

from teacherhire.models import ClassCategory, Subject, Exam

print("Testing signals...")
# Just check if there are any errors when trying to access exam_set
try:
    cat = ClassCategory.objects.first()
    if cat:
        exams = cat.exam_set.all()
        print(f"Exams for category {cat.name}: {exams.count()}")
        
    sub = Subject.objects.first()
    if sub:
        exams = sub.exam_set.all()
        print(f"Exams for subject {sub.subject_name}: {exams.count()}")
except Exception as e:
    print(f"Error: {e}")
