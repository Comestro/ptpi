from teacherhire.models import Question, Exam
import re

def is_hindi(text):
    if not text: return False
    # Check for Devanagari characters
    return bool(re.search(r'[\u0900-\u097F]', text))

def fix_exam_questions(exam_id):
    exam = Exam.objects.get(id=exam_id)
    questions = Question.objects.filter(exam=exam).order_by('order', 'id')
    
    # Group by order
    by_order = {}
    for q in questions:
        if q.order not in by_order:
            by_order[q.order] = []
        by_order[q.order].append(q)
    
    for order, qs in by_order.items():
        print(f"Checking Order {order} for Exam {exam.name}...")
        
        # 1. Identify versions
        english_questions = [q for q in qs if q.language == 'English']
        hindi_questions = [q for q in qs if q.language == 'Hindi']
        
        # 2. Fix mislabeled languages
        for q in qs:
            if q.language == 'Hindi' and not is_hindi(q.text):
                print(f"  Fixing language for ID {q.id}: Hindi -> English (detected English text)")
                q.language = 'English'
                q.save()
            elif q.language == 'English' and is_hindi(q.text):
                print(f"  Fixing language for ID {q.id}: English -> Hindi (detected Hindi text)")
                q.language = 'Hindi'
                q.save()
        
        # Re-fetch after language fix
        qs = list(Question.objects.filter(exam=exam, order=order).order_by('id'))
        english_questions = [q for q in qs if q.language == 'English']
        hindi_questions = [q for q in qs if q.language == 'Hindi']
        
        # 3. Handle duplicates
        if len(english_questions) > 1:
            print(f"  Found {len(english_questions)} English questions at order {order}. Keeping ID {english_questions[0].id}")
            for q in english_questions[1:]:
                print(f"    Deleting duplicate English ID {q.id}")
                q.delete()
            english_questions = [english_questions[0]]

        if len(hindi_questions) > 1:
            print(f"  Found {len(hindi_questions)} Hindi questions at order {order}. Keeping ID {hindi_questions[0].id}")
            for q in hindi_questions[1:]:
                print(f"    Deleting duplicate Hindi ID {q.id}")
                q.delete()
            hindi_questions = [hindi_questions[0]]
            
        # 4. Link pairs
        if english_questions and hindi_questions:
            en = english_questions[0]
            hi = hindi_questions[0]
            if hi.related_question != en:
                print(f"  Linking Hindi ID {hi.id} to English ID {en.id}")
                hi.related_question = en
                hi.save()
        
    print("Cleanup complete.")

# To run for all exams:
# for exam in Exam.objects.all():
#     fix_exam_questions(exam.id)
