from django.core.management.base import BaseCommand
from teacherhire.models import Exam


class Command(BaseCommand):
    help = 'Fix exam names that have mismatched class categories'

    def handle(self, *args, **options):
        exams = Exam.objects.all()
        fixed_count = 0
        
        for exam in exams:
            # Get the correct class_category name from the exam's actual class_category
            correct_class_category = exam.class_category.name
            subject_name = exam.subject.subject_name
            level_name = exam.level.name
            
            # Generate the correct exam name prefix
            correct_prefix = f"{correct_class_category} | {subject_name} | {level_name}"
            
            # Check if the current name has a different class category
            if not exam.name.startswith(correct_prefix):
                # Extract the set number (e.g., "S11" from the end)
                parts = exam.name.split(" | ")
                if len(parts) >= 4:
                    set_number = parts[-1]
                else:
                    # Try to find "S" followed by digits
                    import re
                    match = re.search(r'S\d+', exam.name)
                    set_number = match.group(0) if match else "S1"
                
                # Generate new name with correct class category
                new_name = f"{correct_prefix} | {set_number}"
                
                old_name = exam.name
                exam.name = new_name
                exam.save()
                
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Fixed Exam ID {exam.id}:\n'
                        f'  Old: {old_name}\n'
                        f'  New: {new_name}\n'
                    )
                )
        
        if fixed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully fixed {fixed_count} exam(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No exams needed fixing')
            )
