from teacherhire.models import *
from django.http import JsonResponse
import random
from django.contrib.auth.hashers import make_password
from django.utils import timezone

# Call all seeder functions 
def insert_all_data(request):
    insert_data_examcenter(request)
    insert_data(request)
    # insert_data_teachers(request)
    return JsonResponse({"message": "All data inserted successfully"})

# examcenter seeder
def insert_data_examcenter(request):
    users_data = [
        {"username": "komal", "email": "ks@gmail.com", "password": "12345",  "Fname": "Komal", "Lname": "Raj"},
        {"username": "rahul", "email": "rahul@gmail.com", "password": "12345","Fname": "Rahul", "Lname": "Sharma"},
        {"username": "priya", "email": "priya@gmail.com", "password": "12345", "Fname": "Priya", "Lname": "Verma"},
        {"username": "aman", "email": "aman@gmail.com", "password": "12345", "Fname": "Aman", "Lname": "Kumar"},
        {"username": "neha", "email": "neha@gmail.com", "password": "12345",  "Fname": "Neha", "Lname": "Singh"},
    ]

    centers_data = [
        {"center_name": "Alpha Exam Center", "pincode": "111111", "state": "State A", "city": "City A", "area": "Area A"},
        {"center_name": "Beta Exam Center", "pincode": "222222", "state": "State B", "city": "City B", "area": "Area B"},
        {"center_name": "Gamma Exam Center", "pincode": "333333", "state": "State C", "city": "City C", "area": "Area C"},
        {"center_name": "Delta Exam Center", "pincode": "444444", "state": "State D", "city": "City D", "area": "Area D"},
        {"center_name": "Epsilon Exam Center", "pincode": "555555", "state": "State E", "city": "City E", "area": "Area E"},
    ]

    response_data = {"users_added": 0, "centers_added": 0}

    for user in users_data:
        if not CustomUser.objects.filter(username=user["username"]).exists():
            CustomUser.objects.create(
                username=user["username"],
                email=user["email"],
                password=make_password(user["password"]), 
                is_centeruser = True,
                Fname=user["Fname"],
                Lname=user["Lname"]
            )
            response_data["users_added"] += 1

    users = list(CustomUser.objects.all())

    for center in centers_data:
        if not ExamCenter.objects.filter(center_name=center["center_name"]).exists():
            assigned_user = random.choice(users) if users else None  
            ExamCenter.objects.create(
                user=assigned_user,
                center_name=center["center_name"],
                pincode=center["pincode"],
                state=center["state"],
                city=center["city"],
                area=center["area"],
                status = True,
            )
            response_data["centers_added"] += 1

    return JsonResponse({
        "message": "Seeding completed",
        "users_added": response_data["users_added"],
        "centers_added": response_data["centers_added"]
    })

# teacher data seeder
def insert_data_teachers(request):
    users_data = [
        {"username": "john", "email": "john@gmail.com", "password": "12345", "Fname": "John", "Lname": "Doe"},
        {"username": "alice", "email": "alice@gmail.com", "password": "12345", "Fname": "Alice", "Lname": "Brown"},
        {"username": "mark", "email": "mark@gmail.com", "password": "12345", "Fname": "Mark", "Lname": "Smith"},
    ]

    skills_data = ["Python", "Java", "Mathematics", "Physics", "History"]     
    subjects_data = ["Maths", "Enslish", "Hindi", "Social Science", "Geography"]     
    addresses_data = [
        {"city": "New York", "state": "NY", "pincode": "10001", "area": "Downtown"},
        {"city": "Los Angeles", "state": "CA", "pincode": "90001", "area": "Uptown"},
    ]
    experiences_data = [
        {"institution": "XYZ School", "role": "Teacher", "start_date": "2015-06-01", "end_date": "2018-05-31", "description": "Taught various subjects", "achievements": "Awarded Best Teacher 2017"},
        {"institution": "ABC College", "role": "Lecturer", "start_date": "2019-08-01", "end_date": "Present", "description": "Lecturing Mathematics", "achievements": "Published research paper"}
    ]
    qualifications_data = ["B.Ed", "M.Ed", "PhD"]
    exam_results_data = [
        {"exam_name": "NET", "score": 85},
        {"exam_name": "TET", "score": 90},
    ]
    
    response_data = {"users_added": 0, "skills_added": 0, "subjects_added": 0, "classes_added": 0, 
                     "addresses_added": 0, "results_added": 0, "job_types_added": 0, 
                     "experiences_added": 0, "qualifications_added": 0, "preferences_added": 0}
    
    for user in users_data:
        if not CustomUser.objects.filter(username=user["username"]).exists():
            CustomUser.objects.create(
                username=user["username"],
                email=user["email"],
                password=make_password(user["password"]), 
                is_teacher=True,
                Fname=user["Fname"],
                Lname=user["Lname"]
            )
            response_data["users_added"] += 1
    users = list(CustomUser.objects.all())
    
    for skill_name in skills_data:
        skill_obj, created = Skill.objects.get_or_create(name=skill_name)
        for user in users:
            TeacherSkill.objects.create(user=user, skill=skill_obj)
            response_data["skills_added"] += 1

    for subject_name in subjects_data:
        subject_obj, created = Subject.objects.get_or_create(subject_name=subject_name)
        for user in users:
            TeacherSubject.objects.create(user=user, subject=subject_obj)
            response_data["subjects_added"] += 1
            
    for qualification_name in qualifications_data:
        qualification_obj, created = EducationalQualification.objects.get_or_create(name=qualification_name)
        for user in users:
            institution = f"{qualification_name} Institution"
            year_of_passing = random.randint(2000, 2024)
            grade_or_percentage = f"{random.randint(60, 100)}%"
            TeacherQualification.objects.create(
                user=user,
                qualification=qualification_obj,
                institution=institution,
                year_of_passing=year_of_passing,
                grade_or_percentage=grade_or_percentage
            )
            response_data["qualifications_added"] += 1
    
    for address in addresses_data:
        assigned_user = random.choice(users) if users else None
        if not assigned_user:
            continue  
        city = address.get("city", "")
        state = address.get("state", "")
        pincode = address.get("pincode", "")
        area = address.get("area", "")
        TeachersAddress.objects.create(
            user=assigned_user,
            address_type="current",  
            state="Bihar",
            division="Some Division",
            district="Some District",
            block="Some Block",
            village="Some Village",
            area="Some Area",
            pincode="123456" 
        )
        response_data["addresses_added"] += 1
        
    
    for experience_data in experiences_data:
        for user in users:
            role_obj, created = Role.objects.get_or_create(jobrole_name=experience_data["role"])  # Create or get the role
            start_date = timezone.datetime.strptime(experience_data["start_date"], "%Y-%m-%d").date()
            end_date = timezone.datetime.strptime(experience_data["end_date"], "%Y-%m-%d").date() if experience_data["end_date"] != "Present" else None
            
            TeacherExperiences.objects.create(
                user=user,
                institution=experience_data["institution"],
                role=role_obj,
                start_date=start_date,
                end_date=end_date,
                description=experience_data["description"],
                achievements=experience_data["achievements"]
            )
            response_data["experiences_added"] += 1
    
    for qualification_name in qualifications_data:
        assigned_user = random.choice(users) if users else None
        if assigned_user:
            qualification_obj, created = EducationalQualification.objects.get_or_create(name=qualification_name)
            TeacherQualification.objects.create(user=assigned_user, qualification=qualification_obj)
            response_data["qualifications_added"] += 1
    
    # Seed Preferences
    for user in users:
        job_roles = Role.objects.all()  # Fetch all roles
        class_categories = ClassCategory.objects.all()  # Fetch all class categories
        subjects = Subject.objects.all()  # Fetch all subjects
        job_types = TeacherJobType.objects.all()  # Fetch all job types
        
        preference = Preference.objects.create(user=user)
        
        preference.job_role.set(random.sample(list(job_roles), min(3, len(job_roles))))
        preference.class_category.set(random.sample(list(class_categories), min(2, len(class_categories)))) 
        preference.prefered_subject.set(random.sample(list(subjects), min(2, len(subjects))))
        preference.teacher_job_type.set(random.sample(list(job_types), min(2, len(job_types))))
        
        preference.save()
        response_data["preferences_added"] += 1
    
    return JsonResponse({
        "message": "Seeding completed",
        **response_data
    })

# admin data seeder
def insert_data(request):
    data_to_insert = {
        "class_categories": {
            "model": ClassCategory,
            "field": "name",
            "data": ["1 to 5", "6 to 10", "11 to 12", "BCA", "MCA"]
        },
        "reason": {
            "model": Reason,
            "field": "issue_type",
            "data": ["answer wrong", "question wrong", "spelling mistake", "question and answer wrong ", "number mistake"]
        },
        "levels": {
            "model": Level,
            "field": "name",
            "data": ["1st Level", "2nd Level Online", "2nd Level Offline"]
        },
        "skills": {
            "model": Skill,
            "field": "name",
            "data": ["Maths", "Physics", "Writing", "Mapping", "Research"]
        },
        "roles": {
            "model": Role,
            "field": "jobrole_name",
            "data": ["Teacher", "Professor", "Principal", "PtTeacher", "Sports Teacher"]
        },
        "subjects": {
            "model": Subject,
            "field": "subject_name",
            "data": ["Maths", "Physics", "php", "DBMS", "Hindi"]
        },
        "Teacherjobtype": {
            "model": TeacherJobType,
            "field": "teacher_job_name",
            "data": ["Coaching Teacher", "School Teacher", "Tutor"]
        },
        "Educationqualification": {
            "model": EducationalQualification,
            "field": "name",
            "data": ["matric", "Intermediate", "Under Graduate", "Post Graduate"]
        },
        "exam_centers": {
            "model": ExamCenter,
            "field": "center_name",
            "data": [
                {"center_name": "Alpha Exam Center", "pincode": "111111", "state": "State A", "city": "City A", "area": "Area A"},
                {"center_name": "Beta Exam Center", "pincode": "222222", "state": "State B", "city": "City B", "area": "Area B"},
                {"center_name": "Gamma Exam Center", "pincode": "333333", "state": "State C", "city": "City C", "area": "Area C"},
                {"center_name": "Delta Exam Center", "pincode": "444444", "state": "State D", "city": "City D", "area": "Area D"},
                {"center_name": "Epsilon Exam Center", "pincode": "555555", "state": "State E", "city": "City E", "area": "Area E"},
            ]
        },   
        "Exams": {
            "model": Exam,
            "field": "name",
            "data": [
                {"name": "Set A",  "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B", "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 200, "duration": 240, "type": "online"},
                {"name": "Set A", "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B",  "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C",  "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set A",  "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set B",  "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 200, "duration": 240, "type": "online"},
                {"name": "Set A",  "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B",  "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C",  "class_category": "1 to 5", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Offline Set A",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                {"name": "Offline Set B",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                {"name": "Offline Set C",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set A",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set B",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set C",  "class_category": "1 to 5", "level": "2nd Level Offline", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Set A",  "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B",  "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A",  "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B",  "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C",  "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A",  "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B",  "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C",  "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A",  "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B",  "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "2nd Level Online", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
            ]
        },
    }

    response_data = {}

    for key, config in data_to_insert.items():
        model = config["model"]
        field = config["field"]
        entries = config["data"]
        added_count = 0

        for entry in entries:
            if key == "exam_centers":  # Handle ExamCenter data
                if not model.objects.filter(center_name=entry["center_name"]).exists():
                    model.objects.create(
                        center_name=entry["center_name"],
                        pincode=entry["pincode"],
                        state=entry["state"],
                        city=entry["city"],
                        area=entry["area"]
                    )
                    added_count += 1
            elif key == "Exams":  # Handle Exam data
                name = entry.get("name")
                total_marks = entry.get("total_marks")
                duration = entry.get("duration")
                type = entry.get("type")
                class_category_name = entry.get("class_category")
                level_name = entry.get("level")
                subject_name = entry.get("subject")
                assigneduser = entry.get("assigneduser")

                # Fetch related objects
                class_category, _ = ClassCategory.objects.get_or_create(name=class_category_name)
                level, _ = Level.objects.get_or_create(name=level_name)
                subject, _ = Subject.objects.get_or_create(subject_name=subject_name)
                assigneduser, _ = AssignedQuestionUser.objects.get_or_create(id=assigneduser)
                if not model.objects.filter(
                        name=name,
                        class_category=class_category,
                        level=level,
                        subject=subject,
                        type=type,
                        assigneduser=assigneduser
                ).exists():
                    model.objects.create(
                        name=name,
                        total_marks=total_marks,
                        duration=duration,
                        class_category=class_category,
                        level=level,
                        subject=subject,
                        type=type,
                        assigneduser=assigneduser
                    )
                    added_count += 1
            else:  # Handle other data
                if not model.objects.filter(**{field: entry}).exists():
                    model.objects.create(**{field: entry})
                    added_count += 1

        response_data[key] = {
            "message": f'{added_count} {key.replace("_", " ")} added successfully.' if added_count > 0 else f'All {key.replace("_", " ")} already exist.',
            "added_count": added_count
        }

    exams = Exam.objects.all()
    if exams.exists():
        questions_data = [
    {
                
                "exam": exams[0],
                "time": 1.5,
                "language": "English",
                "text": "What is the capital of India?",
                "options": ["New Delhi", "Mumbaiinsert_", "Kolkata", "Chennai"],
                "solution": "New Delhi is the capital of India.",
                "correct_option": 1
            },
            {
                
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "What is the full form of DBMS?",
                "options": ["Database Management System", "Data Management System", "Database Maintenance System",
                            "Data Backup Management System"],
                "solution": "DBMS stands for Database Management System.",
                "correct_option": 1
            },
            {
                
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "Which of the following is a type of database model?",
                "options": ["Hierarchical Model", "Relational Model", "Object-Oriented Model", "All of the above"],
                "solution": "The correct answer is 'All of the above'. Each of these is a type of database model.",
                "correct_option": 3
            },
            {
                
                "exam": exams[4],
                "language": "English",
                "time": 1.5,
                "text": "Which SQL command is used to retrieve data from a database?",
                "options": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "solution": "The correct SQL command to retrieve data from a database is 'SELECT'.",
                "correct_option": 1
            },
            {
                
                "exam": exams[5],
                "language": "English",
                "time": 1.5,
                "text": "What is normalization in DBMS?",
                "options": ["The process of organizing data to reduce redundancy",
                            "The process of copying data for backup", "The process of making data available online",
                            "The process of encrypting data"],
                "solution": "Normalization is the process of organizing data in a database to reduce redundancy and improve data integrity.",
                "correct_option": 1
            },
            {
                "exam": exams[6],
                "time": 1.5,
                "language": "English",
                "text": "Which of the following is a type of join in SQL?",
                "options": ["INNER JOIN", "OUTER JOIN", "CROSS JOIN", "All of the above"],
                "solution": "The correct answer is 'All of the above'. INNER JOIN, OUTER JOIN, and CROSS JOIN are all types of SQL joins.",
                "correct_option": 3
            },
            {               
                "exam": exams[7],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत की राजधानी क्या है?",
                "options": ["नई दिल्ली", "मुंबई", "कोलकाता", "चेन्नई"],
                "solution": "नई दिल्ली भारत की राजधानी है।",
                "correct_option": 1
            },
            { 
                "exam": exams[8],
                "time": 1.5,
                "language": "English",
                "text": "What is 5 + 5?",
                "options": ["8", "9", "10", "11"],
                "solution": "The correct answer is 10.",
                "correct_option": 3
            },
            {
                "exam": exams[9],
                "time": 1.5,
                "language": "English",
                "text": "What is the boiling point of water?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The correct answer is 100°C.",
                "correct_option": 2
            },
            {
                "exam": exams[9],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत का सबसे बड़ा राज्य कौन सा है?",
                "options": ["राजस्थान", "उत्तर प्रदेश", "मध्य प्रदेश", "महाराष्ट्र"],
                "solution": "भारत का सबसे बड़ा राज्य राजस्थान है।",
                "correct_option": 1
            },
            {
                "exam": exams[10],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत का पहला प्रधानमंत्री कौन थे?",
                "options": ["लाल बहादुर शास्त्री", "पंडित नेहरू", "इंदिरा गांधी", "राजीव गांधी"],
                "solution": "भारत के पहले प्रधानमंत्री पंडित नेहरू थे।",
                "correct_option": 2
            },
            {
                "exam": exams[11],
                "time": 1.5,
                "language": "Hindi",
                "text": "एक ट्रेन 60 किमी/घंटे की गति से 2 घंटे में कितनी दूरी तय करेगी?",
                "options": ["60 किमी", "120 किमी", "180 किमी", "240 किमी"],
                "solution": "ट्रेन 120 किमी की दूरी तय करेगी।",
                "correct_option": 2
            },
            {
                "exam": exams[5],
                "time": 1.5,
                "language": "English",
                "text": "If a train travels at 60 km/hr for 2 hours, what distance does it cover?",
                "options": ["60 km", "120 km", "180 km", "240 km"],
                "solution": "The train covers 120 km.",
                "correct_option": 2
            },
            {
                "exam": exams[0],
                "time": 1.5,
                "language": "Hindi",
                "text": "5 का घनफल क्या है?",
                "options": ["25", "125", "15", "225"],
                "solution": "5 का घनफल 125 है।",
                "correct_option": 2
            },
            {
                "exam": exams[1],
                "time": 1.5,
                "language": "English",
                "text": "What is the cube of 5?",
                "options": ["25", "125", "15", "225"],
                "solution": "The cube of 5 is 125.",
                "correct_option": 2
            },
            {
                "exam": exams[2],
                "time": 1.5,
                "language": "Hindi",
                "text": "100 और 250 का औसत क्या है?",
                "options": ["175", "150", "200", "225"],
                "solution": "100 और 250 का औसत 175 है।",
                "correct_option": 1
            },
            {
                
                "exam": exams[3],
                "time": 1.5,
                "language": "English",
                "text": "What is the average of 100 and 250?",
                "options": ["175", "150", "200", "225"],
                "solution": "The average of 100 and 250 is 175.",
                "correct_option": 1
            },
            {
                
                "exam": exams[4],
                "time": 1.5,
                "language": "Hindi",
                "text": "प्रकाश की गति क्या है?",
                "options": ["3 × 10^6 मीटर/सेकेंड", "3 × 10^8 मीटर/सेकेंड", "3 × 10^9 मीटर/सेकेंड",
                            "3 × 10^7 मीटर/सेकेंड"],
                "solution": "प्रकाश की गति 3 × 10^8 मीटर/सेकेंड है।",
                "correct_option": 2
            },
            {
                
                "exam": exams[5],
                "time": 1.5,
                "language": "English",
                "text": "What is the speed of light?",
                "options": ["3 × 10^6 m/s", "3 × 10^8 m/s", "3 × 10^9 m/s", "3 × 10^7 m/s"],
                "solution": "The speed of light is 3 × 10^8 m/s.",
                "correct_option": 2
            },
            {
                
                "exam": exams[6],
                "time": 1.5,
                "language": "Hindi",
                "text": "न्यूटन के गति का दूसरा नियम क्या है?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "न्यूटन के गति का दूसरा नियम F = ma है।",
                "correct_option": 1
            },
            {
                
                "exam": exams[7],
                "time": 1.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                
                "exam": exams[8],
                "time": 1.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                
                "exam": exams[9],
                "time": 1.5,
                "language": "English",
                "text": "Which of the following is the largest planet in our solar system?",
                "options": ["Earth", "Mars", "Jupiter", "Saturn"],
                "solution": "Jupiter is the largest planet in our solar system.",
                "correct_option": 3
            },
            {
                
                "exam": exams[10],
                "time": 1.5,
                "language": "English",
                "text": "Who is the author of the play 'Romeo and Juliet'?",
                "options": ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"],
                "solution": "The author of 'Romeo and Juliet' is William Shakespeare.",
                "correct_option": 1
            },
            {
                
                "exam": exams[1],
                "time": 1.5,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                
                "exam": exams[2],
                "time": 1.5,
                "language": "English",
                "text": "Who proposed the theory of relativity?",
                "options": ["Isaac Newton", "Albert Einstein", "Galileo Galilei", "Marie Curie"],
                "solution": "The theory of relativity was proposed by Albert Einstein.",
                "correct_option": 2
            },
            {
                
                "exam": exams[3],
                "time": 1.5,
                "language": "English",
                "text": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria", "Ribosome", "Golgi apparatus"],
                "solution": "The mitochondria are known as the powerhouse of the cell.",
                "correct_option": 2
            },
            {
                
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 64?",
                "options": ["6", "7", "8", "9"],
                "solution": "The square root of 64 is 8.",
                "correct_option": 3
            },
            {
                
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
                "solution": "'Romeo and Juliet'",
                "correct_option": 1
            },
            {
                
                "exam": exams[1],
                "time": 2.5,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "Who proposed the theory of relativity?",
                "options": ["Isaac Newton", "Albert Einstein", "Galileo Galilei", "Marie Curie"],
                "solution": "The theory of relativity was proposed by Albert Einstein.",
                "correct_option": 2
            },
            {
                
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria", "Ribosome", "Golgi apparatus"],
                "solution": "The mitochondria are known as the powerhouse of the cell.",
                "correct_option": 2
            },
            {
                
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 64?",
                "options": ["6", "7", "8", "9"],
                "solution": "The square root of 64 is 8.",
                "correct_option": 3
            },
            {
                
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
                "solution": "'Romeo and Juliet' was written by William Shakespeare.",
                "correct_option": 2
            },
            {
                
                "exam": exams[7],
                "time": 2.5,
                "language": "English",
                "text": "What is the boiling point of water at sea level?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The boiling point of water at sea level is 100°C.",
                "correct_option": 2
            },
            {
                
                "exam": exams[8],
                "time": 2.5,
                "language": "English",
                "text": "Which planet is known as the Red Planet?",
                "options": ["Venus", "Mars", "Jupiter", "Saturn"],
                "solution": "Mars is known as the Red Planet.",
                "correct_option": 2
            },
            {
                
                "exam": exams[9],
                "time": 2.5,
                "language": "English",
                "text": "What is the largest organ in the human body?",
                "options": ["Liver", "Heart", "Skin", "Lungs"],
                "solution": "The skin is the largest organ in the human body.",
                "correct_option": 3
            },
            {
                
                "exam": exams[10],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of π (pi) up to two decimal places?",
                "options": ["3.12", "3.13", "3.14", "3.15"],
                "solution": "The value of π (pi) up to two decimal places is 3.14.",
                "correct_option": 3
            },
            {
                
                "exam": exams[0],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of π (pi) up to two decimal places?",
                "options": ["3.12", "3.14", "3.16", "3.18"],
                "solution": "The value of π up to two decimal places is 3.14.",
                "correct_option": 2
            },
            {
                
                "exam": exams[1],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 144?",
                "options": ["10", "11", "12", "13"],
                "solution": "The square root of 144 is 12.",
                "correct_option": 3
            },
            {
                
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "Solve: 5 + 3 × 2.",
                "options": ["11", "16", "21", "13"],
                "solution": "According to the order of operations (BODMAS), 5 + 3 × 2 = 11.",
                "correct_option": 1
            },
            {
                
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "What is 15% of 200?",
                "options": ["25", "30", "35", "40"],
                "solution": "15% of 200 is 30.",
                "correct_option": 2
            },
            {
                
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "If x + 5 = 12, what is the value of x?",
                "options": ["5", "6", "7", "8"],
                "solution": "Subtracting 5 from both sides gives x = 7.",
                "correct_option": 3
            },
            {
                
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "Solve: 9 × (3 + 2).",
                "options": ["36", "40", "45", "50"],
                "solution": "Using BODMAS, 9 × (3 + 2) = 45.",
                "correct_option": 3
            },
            {
                
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "What is the perimeter of a rectangle with length 10 and width 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The perimeter of a rectangle is 2 × (length + width). So, 2 × (10 + 5) = 30.",
                "correct_option": 3
            },
            {
                
                "exam": exams[7],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of 2³?",
                "options": ["6", "8", "9", "12"],
                "solution": "2³ means 2 × 2 × 2 = 8.",
                "correct_option": 2
            },
            {
                
                "exam": exams[8],
                "time": 2.5,
                "language": "English",
                "text": "What is the area of a triangle with base 8 and height 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The area of a triangle is ½ × base × height. So, ½ × 8 × 5 = 20.",
                "correct_option": 1
            },
            {
                
                "exam": exams[9],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of 100 ÷ 4?",
                "options": ["20", "25", "30", "40"],
                "solution": "100 ÷ 4 = 25.",
                "correct_option": 2
            },
            {
                
                "exam": exams[12],
                "time": 2.5,
                "language": "English",
                "text": "What is the unit of force?",
                "options": ["Newton", "Pascal", "Joule", "Watt"],
                "solution": "The SI unit of force is the Newton (N), named after Isaac Newton.",
                "correct_option": 1
            },
            {
                
                "exam": exams[12],
                "time": 2.5,
                "language": "English",
                "text": "What is the acceleration due to gravity on Earth?",
                "options": ["9.8 m/s²", "8.9 m/s²", "10.2 m/s²", "7.6 m/s²"],
                "solution": "The acceleration due to gravity on Earth is approximately 9.8 m/s².",
                "correct_option": 1
            },
            {
                
                "exam": exams[13],
                "time": 2.5,
                "language": "English",
                "text": "Which law explains why a rocket moves upward when gases are expelled downward?",
                "options": [
                    "Newton's First Law",
                    "Newton's Second Law",
                    "Newton's Third Law",
                    "Law of Gravitation"
                ],
                "solution": "Newton's Third Law states that for every action, there is an equal and opposite reaction.",
                "correct_option": 2
            },
            {
                
                "exam": exams[13],
                "time": 2.5,
                "language": "English",
                "text": "Which of the following is a scalar quantity?",
                "options": ["Velocity", "Force", "Speed", "Momentum"],
                "solution": "Speed is a scalar quantity because it has only magnitude, not direction.",
                "correct_option": 2
            },
            {
                
                "exam": exams[14],
                "time": 2.5,
                "language": "English",
                "text": "What is the formula for kinetic energy?",
                "options": [
                    "KE = mv",
                    "KE = 1/2 mv²",
                    "KE = 2mv",
                    "KE = m²v"
                ],
                "solution": "The formula for kinetic energy is KE = 1/2 mv².",
                "correct_option": 1
            },
            {
                
                "exam": exams[14],
                "time": 2.5,
                "language": "English",
                "text": "What is the speed of light in a vacuum?",
                "options": [
                    "3 × 10⁸ m/s",
                    "2 × 10⁸ m/s",
                    "1.5 × 10⁸ m/s",
                    "4 × 10⁸ m/s"
                ],
                "solution": "The speed of light in a vacuum is approximately 3 × 10⁸ meters per second.",
                "correct_option": 1
            },
            {
        
                "exam": exams[15],
        "time": 2.5,
        "language": "English",
        "text": "Solve: 5 + 3 × 2.",
        "options": ["11", "16", "21", "13"],
        "solution": "According to the order of operations (BODMAS), 5 + 3 × 2 = 11.",
        "correct_option": 2
    },
    {
        
                "exam": exams[15],
        "time": 2.5,
        "language": "English",
        "text": "What is the square root of 81?",
        "options": ["7", "8", "9", "10"],
        "solution": "The square root of 81 is 9.",
        "correct_option": 3
    },
    { 
        
                "exam": exams[16],
        "time": 1.5,
        "language": "English",
        "text": "Find the value of 12 ÷ 4 × 3.",
        "options": ["9", "3", "12", "15"],
        "solution": "Using BODMAS, 12 ÷ 4 × 3 = 3 × 3 = 9.",
        "correct_option": 1
    },
    {
        
                "exam": exams[16],
        "time": 1.5,
        "language": "English",
        "text": "Solve: 7 × (8 - 3).",
        "options": ["35", "56", "40", "21"],
        "solution": "First solve inside the brackets: 8 - 3 = 5. Then multiply: 7 × 5 = 35.",
        "correct_option": 1
    },
    {
        
                "exam": exams[17],
        "time": 1.5,
        "language": "English",
        "text": "What is 50% of 200?",
        "options": ["50", "100", "150", "200"],
        "solution": "50% of 200 is 100.",
        "correct_option": 1
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 + 3?",
        "options": ["4", "5", "6", "7"],
        "solution": "2 + 3 equals 5.",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What comes after 7?",
        "options": ["6", "8", "9", "10"],
        "solution": "8 comes after 7.",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 - 4?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 - 4 equals 6.",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is the smallest two-digit number?",
        "options": ["9", "10", "11", "12"],
        "solution": "The smallest two-digit number is 10.",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 + 3 कितना है?",
        "options": ["4", "5", "6", "7"],
        "solution": "2 + 3 का उत्तर 5 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "7 के बाद कौन सा नंबर आता है?",
        "options": ["6", "8", "9", "10"],
        "solution": "7 के बाद 8 आता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 - 4 कितना है?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 - 4 का उत्तर 6 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज के कितने भुजाएँ होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज की 3 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "सबसे छोटा दो-अंकीय नंबर कौन सा है?",
        "options": ["9", "10", "11", "12"],
        "solution": "सबसे छोटा दो-अंकीय नंबर 10 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 + 2?",
        "options": ["1", "2", "4", "5"],
        "solution": "The sum of 2 and 2 is 4.",
        "correct_option": 3
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is the next number after 5?",
        "options": ["4", "6", "7", "8"],
        "solution": "The next number after 5 is 6.",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 minus 4?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 minus 4 equals 6.",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "How many hours are there in a day?",
        "options": ["12", "24", "36", "48"],
        "solution": "There are 24 hours in a day.",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 + 2 कितना होता है?",
        "options": ["1", "2", "4", "5"],
        "solution": "2 और 2 का योग 4 होता है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 के बाद कौन सा संख्या आती है?",
        "options": ["4", "6", "7", "8"],
        "solution": "5 के बाद 6 आता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज में कितने भुजाएं होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज में 3 भुजाएं होती हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 में से 4 घटाएं तो कितना होगा?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 में से 4 घटाने पर 6 होता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "एक दिन में कितने घंटे होते हैं?",
        "options": ["12", "24", "36", "48"],
        "solution": "एक दिन में 24 घंटे होते हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 5 + 3?",
        "options": ["7", "8", "9", "6"],
        "solution": "5 + 3 equals 8.",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a square have?",
        "options": ["3", "4", "5", "6"],
        "solution": "A square has 4 sides.",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 divided by 2?",
        "options": ["3", "5", "7", "10"],
        "solution": "10 divided by 2 equals 5.",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 times 4?",
        "options": ["6", "8", "9", "10"],
        "solution": "2 times 4 equals 8.",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is the smallest two-digit number?",
        "options": ["9", "10", "11", "12"],
        "solution": "The smallest two-digit number is 10.",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 और 3 का योगफल क्या है?",
        "options": ["7", "8", "9", "6"],
        "solution": "5 और 3 का योगफल 8 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "एक वर्ग में कितने भुजाएँ होती हैं?",
        "options": ["3", "4", "5", "6"],
        "solution": "एक वर्ग में 4 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 को 2 से विभाजित करें।",
        "options": ["3", "5", "7", "10"],
        "solution": "10 को 2 से विभाजित करने पर 5 प्राप्त होता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 और 4 का गुणा क्या है?",
        "options": ["6", "8", "9", "10"],
        "solution": "2 और 4 का गुणा 8 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "सबसे छोटा दो अंकों का अंक कौन सा है?",
        "options": ["9", "10", "11", "12"],
        "solution": "सबसे छोटा दो अंकों का अंक 10 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that pulls objects towards the Earth?",
        "options": ["Magnetic force", "Gravitational force", "Electric force", "Frictional force"],
        "solution": "Gravitational force pulls objects towards the Earth.",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "वह कौन सी ताकत है जो वस्तुओं को पृथ्वी की ओर खींचती है?",
        "options": ["चुम्बकीय बल", "गुरुत्वाकर्षण बल", "वैद्युतिक बल", "घर्षण बल"],
        "solution": "गुरुत्वाकर्षण बल वस्तुओं को पृथ्वी की ओर खींचता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a source of light?",
        "options": ["Moon", "Sun", "Earth", "Clouds"],
        "solution": "The Sun is a source of light.",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा प्रकाश का स्रोत है?",
        "options": ["चाँद", "सूरज", "पृथ्वी", "बादल"],
        "solution": "सूरज प्रकाश का स्रोत है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What is the change in position of an object called?",
        "options": ["Motion", "Speed", "Force", "Energy"],
        "solution": "The change in position of an object is called motion.",
        "correct_option": 1
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "वस्तु की स्थिति में परिवर्तन को क्या कहा जाता है?",
        "options": ["गति", "गति", "बल", "ऊर्जा"],
        "solution": "वस्तु की स्थिति में परिवर्तन को गति कहा जाता है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What do we use to measure temperature?",
        "options": ["Thermometer", "Barometer", "Speedometer", "Odometer"],
        "solution": "We use a thermometer to measure temperature.",
        "correct_option": 1
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "हम तापमान मापने के लिए किसका उपयोग करते हैं?",
        "options": ["थर्मामीटर", "बारोमीटर", "स्पीडोमीटर", "ओडोमीटर"],
        "solution": "हम तापमान मापने के लिए थर्मामीटर का उपयोग करते हैं।",
        "correct_option": 1
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a form of energy?",
        "options": ["Water", "Electricity", "Wood", "Stone"],
        "solution": "Electricity is a form of energy.",
        "correct_option": 2
    },
    {
        
                "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा ऊर्जा का रूप है?",
        "options": ["पानी", "बिजली", "लकड़ी", "पत्थर"],
        "solution": "बिजली ऊर्जा का रूप है।",
        "correct_option": 2
    },
     {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the unit of force?",
    "options": ["Meter", "Newton", "Kilogram", "Second"],
    "solution": "The unit of force is Newton.",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "बल की इकाई क्या है?",
    "options": ["मीटर", "न्यूटन", "किलोग्राम", "सेकंड"],
    "solution": "बल की इकाई न्यूटन है।",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the boiling point of water?",
    "options": ["90°C", "100°C", "110°C", "120°C"],
    "solution": "The boiling point of water is 100°C.",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "पानी का उबालने का बिंदु क्या है?",
    "options": ["90°C", "100°C", "110°C", "120°C"],
    "solution": "पानी का उबालने का बिंदु 100°C है।",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the force that attracts objects towards the Earth?",
    "options": ["Gravity", "Magnetism", "Friction", "Electricity"],
    "solution": "Gravity is the force that attracts objects towards the Earth.",
    "correct_option": 1
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "वह बल जो वस्तुओं को पृथ्वी की ओर आकर्षित करता है, क्या कहलाता है?",
    "options": ["गुरुत्वाकर्षण", "चुम्बकत्व", "घर्षण", "बिजली"],
    "solution": "वह बल जो वस्तुओं को पृथ्वी की ओर आकर्षित करता है, गुरुत्वाकर्षण कहलाता है।",
    "correct_option": 1
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the shape of the Earth?",
    "options": ["Flat", "Round", "Oval", "Square"],
    "solution": "The Earth is round in shape.",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "पृथ्वी का आकार क्या है?",
    "options": ["समतल", "गोल", "अंडाकार", "वर्गाकार"],
    "solution": "पृथ्वी का आकार गोल है।",
    "correct_option": 2
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the source of light in the daytime?",
    "options": ["Moon", "Lamp", "Sun", "Star"],
    "solution": "The source of light in the daytime is the Sun.",
    "correct_option": 3
  },
  {
    
                "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "दिन के समय प्रकाश का स्रोत क्या है?",
    "options": ["चाँद", "दीपक", "सूर्य", "तारा"],
    "solution": "दिन के समय प्रकाश का स्रोत सूर्य है।",
    "correct_option": 3
  },
  {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is the main source of light on Earth?",
        "options": ["Sun", "Moon", "Stars", "Lamp"],
        "solution": "The Sun is the main source of light on Earth.",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is water in its solid form?",
        "options": ["Ice", "Liquid", "Steam", "Rain"],
        "solution": "Water in its solid form is ice.",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a gas?",
        "options": ["Oxygen", "Water", "Iron", "Gold"],
        "solution": "Oxygen is a gas.",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that slows down a moving object?",
        "options": ["Push", "Friction", "Gravity", "Lift"],
        "solution": "Friction is the force that slows down a moving object.",
        "correct_option": 2
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "Which of these is an example of an insulator?",
        "options": ["Wood", "Metal", "Glass", "Copper"],
        "solution": "Wood is an example of an insulator.",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी पर मुख्य प्रकाश स्रोत क्या है?",
        "options": ["सूर्य", "चाँद", "तारे", "दीपक"],
        "solution": "पृथ्वी पर मुख्य प्रकाश स्रोत सूर्य है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "पानी अपनी ठोस अवस्था में क्या होता है?",
        "options": ["बर्फ", "द्रव", "वाष्प", "बारिश"],
        "solution": "पानी अपनी ठोस अवस्था में बर्फ होता है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन गैस है?",
        "options": ["ऑक्सीजन", "पानी", "लोहा", "सोना"],
        "solution": "ऑक्सीजन गैस है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "वह कौन सा बल है जो चलती हुई वस्तु को धीमा कर देता है?",
        "options": ["धक्का", "घर्षण", "गुरुत्वाकर्षण", "उठाव"],
        "solution": "घर्षण वह बल है जो चलती हुई वस्तु को धीमा कर देता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "इनमें से कौन सा उदाहरण इंसुलेटर का है?",
        "options": ["लकड़ी", "धातु", "कांच", "तांबा"],
        "solution": "लकड़ी इंसुलेटर का उदाहरण है।",
        "correct_option": 1
    },
     {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 5 + 3?",
        "options": ["6", "7", "8", "9"],
        "solution": "5 + 3 equals 8.",
        "correct_option": 3
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 - 4?",
        "options": ["5", "6", "7", "4"],
        "solution": "10 - 4 equals 6.",
        "correct_option": 2
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is the shape of a ball?",
        "options": ["Square", "Rectangle", "Circle", "Triangle"],
        "solution": "The shape of a ball is a circle.",
        "correct_option": 3
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 7 × 2?",
        "options": ["12", "13", "14", "15"],
        "solution": "7 × 2 equals 14.",
        "correct_option": 3
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 + 3 क्या है?",
        "options": ["6", "7", "8", "9"],
        "solution": "5 + 3 का उत्तर 8 है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 - 4 क्या है?",
        "options": ["5", "6", "7", "4"],
        "solution": "10 - 4 का उत्तर 6 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "गेंद का आकार क्या है?",
        "options": ["वर्ग", "आयत", "वृत्त", "त्रिभुज"],
        "solution": "गेंद का आकार वृत्त होता है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज के कितने भुजाएँ होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज की 3 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "7 × 2 क्या है?",
        "options": ["12", "13", "14", "15"],
        "solution": "7 × 2 का उत्तर 14 है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[7],
        "language": "English",
        "text": "What is 15 - 7?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "15 - 7 = 8."
    },
    {
        
                "exam": exams[7],
        "language": "English",
        "text": "What is the smallest 2-digit number?",
        "options": ["9", "10", "11", "12"],
        "correct_option": 2,
        "solution": "The smallest two-digit number is 10."
    },
    {
        
                "exam": exams[7],
        "language": "English",
        "text": "How many sides does a pentagon have?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "A pentagon has 5 sides."
    },
    {
        
                "exam": exams[7],
        "language": "English",
        "text": "What is 25 ÷ 5?",
        "options": ["4", "5", "6", "7"],
        "correct_option": 2,
        "solution": "25 ÷ 5 = 5."
    },
    {
        
                "exam": exams[7],
        "language": "English",
        "text": "What comes after 499?",
        "options": ["498", "500", "501", "502"],
        "correct_option": 2,
        "solution": "The number after 499 is 500."
    },
    {
        
                "exam": exams[7],
        "language": "Hindi",
        "text": "15 - 7 क्या है?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "15 - 7 = 8।"
    },
    {
        
                "exam": exams[7],
        "language": "Hindi",
        "text": "सबसे छोटी दो-अंकीय संख्या क्या है?",
        "options": ["9", "10", "11", "12"],
        "correct_option": 2,
        "solution": "सबसे छोटी दो-अंकीय संख्या 10 है।"
    },
    {
        
                "exam": exams[7],
        "language": "Hindi",
        "text": "पंचभुज में कितने भुजाएँ होती हैं?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "पंचभुज में 5 भुजाएँ होती हैं।"
    },
    {
        
                "exam": exams[7],
        "language": "Hindi",
        "text": "25 ÷ 5 कितना है?",
        "options": ["4", "5", "6", "7"],
        "correct_option": 2,
        "solution": "25 ÷ 5 = 5।"
    },
    {
        
                "exam": exams[7],
        "language": "Hindi",
        "text": "499 के बाद कौन सी संख्या आती है?",
        "options": ["498", "500", "501", "502"],
        "correct_option": 2,
        "solution": "499 के बाद 500 आती है।"
    },
    {
        
                "exam": exams[8],
        "language": "English",
        "text": "What is 12 + 8?",
        "options": ["18", "19", "20", "21"],
        "correct_option": 3,
        "solution": "12 + 8 = 20."
    },
    {
        
                "exam": exams[8],
        "language": "English",
        "text": "How many hours are there in 2 days?",
        "options": ["24", "36", "48", "60"],
        "correct_option": 3,
        "solution": "2 days × 24 hours/day = 48 hours."
    },
    {
        
                "exam": exams[8],
        "language": "English",
        "text": "Which shape has 4 equal sides?",
        "options": ["Triangle", "Square", "Rectangle", "Circle"],
        "correct_option": 2,
        "solution": "A square has 4 equal sides."
    },
    {
        
                "exam": exams[8],
        "language": "English",
        "text": "What is 5 × 6?",
        "options": ["25", "30", "35", "40"],
        "correct_option": 2,
        "solution": "5 × 6 = 30."
    },
    {
        
                "exam": exams[8],
        "language": "English",
        "text": "What is 100 minus 45?",
        "options": ["55", "50", "60", "45"],
        "correct_option": 1,
        "solution": "100 - 45 = 55."
    },
    {
        
                "exam": exams[8],
        "language": "Hindi",
        "text": "12 + 8 क्या है?",
        "options": ["18", "19", "20", "21"],
        "correct_option": 3,
        "solution": "12 + 8 = 20।"
    },
    {
        
                "exam": exams[8],
        "language": "Hindi",
        "text": "2 दिनों में कितने घंटे होते हैं?",
        "options": ["24", "36", "48", "60"],
        "correct_option": 3,
        "solution": "2 दिनों में 48 घंटे होते हैं।"
    },
    {
        
                "exam": exams[8],
        "language": "Hindi",
        "text": "कौन सा आकार चार बराबर भुजाएँ रखता है?",
        "options": ["त्रिभुज", "वर्ग", "आयत", "वृत्त"],
        "correct_option": 2,
        "solution": "वर्ग चार बराबर भुजाएँ रखता है।"
    },
    {
        
                "exam": exams[8],
        "language": "Hindi",
        "text": "5 × 6 कितना है?",
        "options": ["25", "30", "35", "40"],
        "correct_option": 2,
        "solution": "5 × 6 = 30।"
    },
    {
        
                "exam": exams[8],
        "language": "Hindi",
        "text": "100 में से 45 घटाने पर क्या प्राप्त होगा?",
        "options": ["55", "50", "60", "45"],
        "correct_option": 1,
        "solution": "100 - 45 = 55।"
    },
    {
        
                "exam": exams[9],
        "language": "English",
        "text": "What is the source of energy for the sun?",
        "options": ["Nuclear fusion", "Electric energy", "Chemical reaction", "Magnetic field"],
        "correct_option": 1,
        "solution": "The sun's energy comes from nuclear fusion, where hydrogen atoms combine to form helium, releasing a vast amount of energy."
    },
    {
        
                "exam": exams[9],
        "language": "English",
        "text": "What force pulls objects towards the Earth?",
        "options": ["Friction", "Magnetism", "Gravity", "Air resistance"],
        "correct_option": 3,
        "solution": "Gravity is the force that pulls objects towards the Earth's center due to its mass."
    },
    {
        
                "exam": exams[9],
        "language": "English",
        "text": "Which is the lightest planet in the solar system?",
        "options": ["Earth", "Mars", "Jupiter", "Mercury"],
        "correct_option": 4,
        "solution": "Mercury is the lightest planet in the solar system due to its small size and low mass."
    },
    {
        
                "exam": exams[9],
        "language": "English",
        "text": "What do we use to see very small objects?",
        "options": ["Telescope", "Binoculars", "Microscope", "Magnifying glass"],
        "correct_option": 3,
        "solution": "A microscope is used to observe very small objects by magnifying them to make them visible."
    },
    {
        
                "exam": exams[9],
        "language": "English",
        "text": "What is formed when light passes through a prism?",
        "options": ["Shadow", "Spectrum", "Reflection", "Absorption"],
        "correct_option": 2,
        "solution": "When light passes through a prism, it splits into its constituent colors, forming a spectrum."
    },
    {
        
                "exam": exams[9],
        "language": "Hindi",
        "text": "सूरज का ऊर्जा स्रोत क्या है?",
        "options": ["नाभिकीय संलयन", "विद्युत ऊर्जा", "रासायनिक प्रतिक्रिया", "चुंबकीय क्षेत्र"],
        "correct_option": 1,
        "solution": "सूरज की ऊर्जा का स्रोत नाभिकीय संलयन है, जिसमें हाइड्रोजन परमाणु मिलकर हीलियम बनाते हैं और ऊर्जा उत्पन्न करते हैं।"
    },
    {
        
                "exam": exams[9],
        "language": "Hindi",
        "text": "पृथ्वी की ओर वस्तुओं को खींचने वाला बल कौन सा है?",
        "options": ["घर्षण", "चुंबकत्व", "गुरुत्वाकर्षण", "वायुरोध"],
        "correct_option": 3,
        "solution": "गुरुत्वाकर्षण बल पृथ्वी की ओर वस्तुओं को खींचता है क्योंकि यह पृथ्वी के द्रव्यमान के कारण उत्पन्न होता है।"
    },
    {
        
                "exam": exams[9],
        "language": "Hindi",
        "text": "सौरमंडल में सबसे हल्का ग्रह कौन सा है?",
        "options": ["पृथ्वी", "मंगल", "बृहस्पति", "बुध"],
        "correct_option": 4,
        "solution": "बुध सौरमंडल का सबसे हल्का ग्रह है क्योंकि इसका आकार और द्रव्यमान बहुत छोटा है।"
    },
    {
        
                "exam": exams[9],
        "language": "Hindi",
        "text": "बहुत छोटे वस्तुओं को देखने के लिए हम क्या उपयोग करते हैं?",
        "options": ["दूरबीन", "दूरदर्शी", "सूक्ष्मदर्शी", "आवर्धक काँच"],
        "correct_option": 3,
        "solution": "बहुत छोटे वस्तुओं को देखने के लिए सूक्ष्मदर्शी का उपयोग किया जाता है, जो वस्तुओं को बड़ा दिखाने में मदद करता है।"
    },
    {
        
                "exam": exams[9],
        "language": "Hindi",
        "text": "प्रिज्म से प्रकाश गुजरने पर क्या बनता है?",
        "options": ["छाया", "वर्णक्रम", "परावर्तन", "अवशोषण"],
        "correct_option": 2,
        "solution": "प्रिज्म से प्रकाश गुजरने पर यह विभाजित होकर विभिन्न रंगों का वर्णक्रम बनाता है।"
    },

    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What happens when you place an object in water, and it floats?",
        "options": ["The object is heavy", "The object is light", "The water is hot", "The water is cold"],
        "solution": "The object is light, which is why it floats.",
        "correct_option": 2
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What is the natural satellite of Earth?",
        "options": ["Mars", "Sun", "Moon", "Venus"],
        "solution": "The Moon is the natural satellite of Earth.",
        "correct_option": 3
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "Which force slows down a moving ball on the ground?",
        "options": ["Friction", "Gravity", "Electricity", "Magnetism"],
        "solution": "Friction slows down a moving ball on the ground.",
        "correct_option": 1
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "Which of these can change the shape of an object?",
        "options": ["Push", "Pull", "Both", "None"],
        "solution": "Both pushing and pulling can change the shape of an object.",
        "correct_option": 3
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What do plants use from sunlight to make food?",
        "options": ["Heat", "Energy", "Water", "Air"],
        "solution": "Plants use energy from sunlight to make food.",
        "correct_option": 2
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "जब आप किसी वस्तु को पानी में रखते हैं और वह तैरती है, तो क्या होता है?",
        "options": ["वस्तु भारी होती है", "वस्तु हल्की होती है", "पानी गर्म होता है", "पानी ठंडा होता है"],
        "solution": "वस्तु हल्की होती है, इसलिए वह तैरती है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी का प्राकृतिक उपग्रह क्या है?",
        "options": ["मंगल", "सूर्य", "चंद्रमा", "शुक्र"],
        "solution": "चंद्रमा पृथ्वी का प्राकृतिक उपग्रह है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "कौन सा बल जमीन पर चल रही गेंद को धीमा कर देता है?",
        "options": ["घर्षण", "गुरुत्वाकर्षण", "बिजली", "चुंबकत्व"],
        "solution": "घर्षण जमीन पर चल रही गेंद को धीमा कर देता है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "इनमें से कौन सी चीज किसी वस्तु का आकार बदल सकती है?",
        "options": ["धक्का", "खींचना", "दोनों", "कोई नहीं"],
        "solution": "धक्का और खींचना दोनों वस्तु का आकार बदल सकते हैं।",
        "correct_option": 3
    },
    {
        
                "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "पौधे भोजन बनाने के लिए सूर्य के प्रकाश से क्या उपयोग करते हैं?",
        "options": ["गर्मी", "ऊर्जा", "पानी", "हवा"],
        "solution": "पौधे भोजन बनाने के लिए सूर्य के प्रकाश से ऊर्जा का उपयोग करते हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[11],
        "language": "English",
        "text": "What is the force that pulls objects towards the Earth?",
        "options": ["Magnetism", "Friction", "Gravity", "Electricity"],
        "correct_option": 3,
        "solution": "Gravity is the force that pulls objects towards the Earth."
    },
    {
        
                "exam": exams[11],
        "language": "English",
        "text": "Which of the following is the source of light during the day?",
        "options": ["Moon", "Stars", "Sun", "Streetlight"],
        "correct_option": 3,
        "solution": "The Sun is the source of light during the day."
    },
    {
        
                "exam": exams[11],
        "language": "English",
        "text": "What is the state of water when it freezes?",
        "options": ["Liquid", "Gas", "Solid", "Plasma"],
        "correct_option": 3,
        "solution": "Water turns into a solid state when it freezes."
    },
    {
        
                "exam": exams[11],
        "language": "English",
        "text": "What tool do we use to measure the weight of an object?",
        "options": ["Thermometer", "Barometer", "Spring scale", "Compass"],
        "correct_option": 3,
        "solution": "A spring scale is used to measure the weight of an object."
    },
    {
        
                "exam": exams[11],
        "language": "English",
        "text": "What happens when you heat a solid?",
        "options": ["It becomes liquid", "It becomes gas", "It stays the same", "It becomes smaller"],
        "correct_option": 1,
        "solution": "When you heat a solid, it can melt and turn into a liquid."
    },
    {
        
                "exam": exams[11],
        "language": "Hindi",
        "text": "वह कौन सा बल है जो वस्तुओं को पृथ्वी की ओर खींचता है?",
        "options": ["चुंबकत्व", "घर्षण", "गुरुत्वाकर्षण", "विद्युत ऊर्जा"],
        "correct_option": 3,
        "solution": "गुरुत्वाकर्षण वह बल है जो वस्तुओं को पृथ्वी की ओर खींचता है।"
    },
    {
        
                "exam": exams[11],
        "language": "Hindi",
        "text": "दिन के समय प्रकाश का स्रोत क्या है?",
        "options": ["चाँद", "तारे", "सूरज", "सड़क की बत्तियाँ"],
        "correct_option": 3,
        "solution": "सूरज दिन के समय प्रकाश का मुख्य स्रोत है।"
    },
    {
        
                "exam": exams[11],
        "language": "Hindi",
        "text": "जब पानी जमता है, तो उसकी अवस्था क्या होती है?",
        "options": ["तरल", "गैस", "ठोस", "प्लाज्मा"],
        "correct_option": 3,
        "solution": "जब पानी जमता है, तो वह ठोस अवस्था में बदल जाता है।"
    },
    {
        
                "exam": exams[11],
        "language": "Hindi",
        "text": "हम किसी वस्तु का वजन मापने के लिए कौन सा यंत्र उपयोग करते हैं?",
        "options": ["थर्मामीटर", "वायुदाबमापी", "स्प्रिंग स्केल", "कंपास"],
        "correct_option": 3,
        "solution": "वजन मापने के लिए हम स्प्रिंग स्केल का उपयोग करते हैं।"
    },
    {
        
                "exam": exams[11],
        "language": "Hindi",
        "text": "जब आप किसी ठोस को गरम करते हैं, तो क्या होता है?",
        "options": ["यह तरल बन जाता है", "यह गैस बन जाता है", "यह वैसा का वैसा रहता है", "यह छोटा हो जाता है"],
        "correct_option": 1,
        "solution": "जब आप किसी ठोस को गरम करते हैं, तो वह पिघलकर तरल में बदल सकता है।"
    },
    {
        
                "exam": exams[18],
        "language": "English",
        "text": "What is the sum of 56 and 78?",
        "options": ["134", "136", "148", "138"],
        "correct_option": 1,
        "solution": "The sum of 56 and 78 is 134."
    },
    {
        
                "exam": exams[18],
        "language": "English",
        "text": "What is the product of 12 and 9?",
        "options": ["108", "96", "72", "110"],
        "correct_option": 1,
        "solution": "The product of 12 and 9 is 108."
    },
    {
        
                "exam": exams[18],
        "language": "English",
        "text": "What is 36 divided by 4?",
        "options": ["9", "8", "7", "10"],
        "correct_option": 1,
        "solution": "36 divided by 4 equals 9."
    },
    {
        
                "exam": exams[18],
        "language": "English",
        "text": "What is the square of 7?",
        "options": ["49", "56", "72", "64"],
        "correct_option": 1,
        "solution": "The square of 7 is 49."
    },
    {
        
                "exam": exams[18],
        "language": "English",
        "text": "What is the perimeter of a rectangle with length 8 cm and width 5 cm?",
        "options": ["26 cm", "32 cm", "16 cm", "18 cm"],
        "correct_option": 1,
        "solution": "The perimeter of the rectangle is 26 cm (2 × (8 + 5))."
    },
    {
        
                "exam": exams[18],
        "language": "Hindi",
        "text": "56 और 78 का योगफल क्या है?",
        "options": ["134", "136", "148", "138"],
        "correct_option": 1,
        "solution": "56 और 78 का योगफल 134 है।"
    },
    {
        
                "exam": exams[18],
        "language": "Hindi",
        "text": "12 और 9 का गुणनफल क्या है?",
        "options": ["108", "96", "72", "110"],
        "correct_option": 1,
        "solution": "12 और 9 का गुणनफल 108 है।"
    },
    {
        
                "exam": exams[18],
        "language": "Hindi",
        "text": "36 को 4 से भाग देने पर क्या प्राप्त होता है?",
        "options": ["9", "8", "7", "10"],
        "correct_option": 1,
        "solution": "36 को 4 से भाग देने पर 9 प्राप्त होता है।"
    },
    {
        
                "exam": exams[18],
        "language": "Hindi",
        "text": "7 का वर्गफल क्या है?",
        "options": ["49", "56", "72", "64"],
        "correct_option": 1,
        "solution": "7 का वर्गफल 49 है।"
    },
    {
        
                "exam": exams[18],
        "language": "Hindi",
        "text": "8 सेंटीमीटर लंबाई और 5 सेंटीमीटर चौड़ाई वाले आयत का परिमाप क्या होगा?",
        "options": ["26 सेंटीमीटर", "32 सेंटीमीटर", "16 सेंटीमीटर", "18 सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का परिमाप 26 सेंटीमीटर होगा (2 × (8 + 5))."
    },
    {
        
                "exam": exams[19],
        "language": "English",
        "text": "What is the sum of 45 and 63?",
        "options": ["108", "110", "112", "114"],
        "correct_option": 1,
        "solution": "The sum of 45 and 63 is 108."
    },
    {
        
                "exam": exams[19],
        "language": "English",
        "text": "What is the difference between 95 and 47?",
        "options": ["48", "50", "52", "58"],
        "correct_option": 1,
        "solution": "The difference between 95 and 47 is 48."
    },
    {
        
                "exam": exams[19],
        "language": "English",
        "text": "What is 15 multiplied by 6?",
        "options": ["90", "96", "84", "72"],
        "correct_option": 1,
        "solution": "15 multiplied by 6 is 90."
    },
    {
        
                "exam": exams[19],
        "language": "English",
        "text": "What is the area of a rectangle with length 10 cm and width 5 cm?",
        "options": ["50 cm²", "55 cm²", "60 cm²", "45 cm²"],
        "correct_option": 1,
        "solution": "The area of the rectangle is 50 cm² (length × width)."
    },
    {
        
                "exam": exams[19],
        "language": "English",
        "text": "What is the square root of 49?",
        "options": ["7", "6", "8", "9"],
        "correct_option": 1,
        "solution": "The square root of 49 is 7."
    },
     {
        
                "exam": exams[19],
        "language": "Hindi",
        "text": "45 और 63 का योगफल क्या है?",
        "options": ["108", "110", "112", "114"],
        "correct_option": 1,
        "solution": "45 और 63 का योगफल 108 है।"
    },
    {
        
                "exam": exams[19],
        "language": "Hindi",
        "text": "95 और 47 के बीच का अंतर क्या है?",
        "options": ["48", "50", "52", "58"],
        "correct_option": 1,
        "solution": "95 और 47 के बीच का अंतर 48 है।"
    },
    {
        
                "exam": exams[19],
        "language": "Hindi",
        "text": "15 को 6 से गुणा करने पर क्या मिलता है?",
        "options": ["90", "96", "84", "72"],
        "correct_option": 1,
        "solution": "15 को 6 से गुणा करने पर 90 मिलता है।"
    },
    {
        
                "exam": exams[19],
        "language": "Hindi",
        "text": "10 सेंटीमीटर लंबाई और 5 सेंटीमीटर चौड़ाई वाले आयत का क्षेत्रफल क्या है?",
        "options": ["50 सेमी²", "55 सेमी²", "60 सेमी²", "45 सेमी²"],
        "correct_option": 1,
        "solution": "आयत का क्षेत्रफल 50 सेमी² है (लंबाई × चौड़ाई)।"
    },
    {
        
                "exam": exams[19],
        "language": "Hindi",
        "text": "49 का वर्गमूल क्या है?",
        "options": ["7", "6", "8", "9"],
        "correct_option": 1,
        "solution": "49 का वर्गमूल 7 है।"
    },
     {
        
                "exam": exams[20],
        "language": "English",
        "text": "What is the sum of 125 and 75?",
        "options": ["200", "210", "190", "180"],
        "correct_option": 1,
        "solution": "The sum of 125 and 75 is 200."
    },
    {
        
                "exam": exams[20],
        "language": "English",
        "text": "What is the product of 12 and 8?",
        "options": ["96", "98", "100", "104"],
        "correct_option": 1,
        "solution": "The product of 12 and 8 is 96."
    },
    {
        
                "exam": exams[20],
        "language": "English",
        "text": "What is the perimeter of a square with side length 6 cm?",
        "options": ["24 cm", "18 cm", "20 cm", "22 cm"],
        "correct_option": 1,
        "solution": "The perimeter of the square is 24 cm (4 × side length)."
    },
    {
        
                "exam": exams[20],
        "language": "English",
        "text": "What is 72 divided by 9?",
        "options": ["8", "7", "9", "6"],
        "correct_option": 1,
        "solution": "72 divided by 9 equals 8."
    },
    {
        
                "exam": exams[20],
        "language": "English",
        "text": "What is the value of 15 raised to the power of 2?",
        "options": ["225", "250", "200", "300"],
        "correct_option": 1,
        "solution": "15 raised to the power of 2 equals 225."
    },
    {
        
                "exam": exams[20],
        "language": "Hindi",
        "text": "125 और 75 का योगफल क्या है?",
        "options": ["200", "210", "190", "180"],
        "correct_option": 1,
        "solution": "125 और 75 का योगफल 200 है।"
    },
    {
        
                "exam": exams[20],
        "language": "Hindi",
        "text": "12 और 8 का गुणनफल क्या है?",
        "options": ["96", "98", "100", "104"],
        "correct_option": 1,
        "solution": "12 और 8 का गुणनफल 96 है।"
    },
    {
        
                "exam": exams[20],
        "language": "Hindi",
        "text": "6 सेंटीमीटर लंबाई वाले वर्ग का परिमाप क्या है?",
        "options": ["24 सेमी", "18 सेमी", "20 सेमी", "22 सेमी"],
        "correct_option": 1,
        "solution": "वर्ग का परिमाप 24 सेमी है (4 × लंबाई)।"
    },
    {
        
                "exam": exams[20],
        "language": "Hindi",
        "text": "72 को 9 से भाग करने पर क्या मिलता है?",
        "options": ["8", "7", "9", "6"],
        "correct_option": 1,
        "solution": "72 को 9 से भाग करने पर 8 मिलता है।"
    },
    {
        
                "exam": exams[20],
        "language": "Hindi",
        "text": "15 का वर्गमूल क्या है?",
        "options": ["225", "250", "200", "300"],
        "correct_option": 1,
        "solution": "15 का वर्गमूल 225 है।"
    },
    {
        
                "exam": exams[21],
        "language": "English",
        "text": "What is the square root of 81?",
        "options": ["8", "9", "7", "6"],
        "correct_option": 2,
        "solution": "The square root of 81 is 9."
    },
    {
        
                "exam": exams[21],
        "language": "English",
        "text": "What is the result of 15 × 4?",
        "options": ["60", "55", "65", "70"],
        "correct_option": 1,
        "solution": "15 multiplied by 4 is 60."
    },
    {
        
                "exam": exams[21],
        "language": "English",
        "text": "If a rectangle has a length of 8 cm and a width of 5 cm, what is its area?",
        "options": ["40 cm²", "50 cm²", "60 cm²", "45 cm²"],
        "correct_option": 1,
        "solution": "The area of the rectangle is 40 cm² (length × width)."
    },
    {
        
                "exam": exams[21],
        "language": "English",
        "text": "What is the sum of 56 and 44?",
        "options": ["90", "100", "110", "120"],
        "correct_option": 2,
        "solution": "The sum of 56 and 44 is 100."
    },
    {
        
                "exam": exams[21],
        "language": "English",
        "text": "What is the value of 100 ÷ 5?",
        "options": ["25", "20", "30", "15"],
        "correct_option": 1,
        "solution": "100 divided by 5 is 20."
    },
    {
        
                "exam": exams[21],
        "language": "Hindi",
        "text": "81 का वर्गमूल क्या है?",
        "options": ["8", "9", "7", "6"],
        "correct_option": 2,
        "solution": "81 का वर्गमूल 9 है।"
    },
    {
        
                "exam": exams[21],
        "language": "Hindi",
        "text": "15 × 4 का परिणाम क्या है?",
        "options": ["60", "55", "65", "70"],
        "correct_option": 1,
        "solution": "15 गुणा 4 का परिणाम 60 है।"
    },
    {
        
                "exam": exams[21],
        "language": "Hindi",
        "text": "यदि आयत की लंबाई 8 सेंटीमीटर और चौड़ाई 5 सेंटीमीटर है, तो उसका क्षेत्रफल क्या होगा?",
        "options": ["40 वर्ग सेंटीमीटर", "50 वर्ग सेंटीमीटर", "60 वर्ग सेंटीमीटर", "45 वर्ग सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का क्षेत्रफल 40 वर्ग सेंटीमीटर है (लंबाई × चौड़ाई)।"
    },
    {
        
                "exam": exams[21],
        "language": "Hindi",
        "text": "56 और 44 का योगफल क्या है?",
        "options": ["90", "100", "110", "120"],
        "correct_option": 2,
        "solution": "56 और 44 का योगफल 100 है।"
    },
    {
        
                "exam": exams[21],
        "language": "Hindi",
        "text": "100 ÷ 5 का मान क्या है?",
        "options": ["25", "20", "30", "15"],
        "correct_option": 1,
        "solution": "100 को 5 से विभाजित करने पर 20 मिलता है।"
    },
    {
        
                "exam": exams[22],
        "language": "English",
        "text": "What is 18 ÷ 3?",
        "options": ["5", "6", "7", "8"],
        "correct_option": 2,
        "solution": "18 divided by 3 is 6."
    },
    {
        
                "exam": exams[22],
        "language": "English",
        "text": "What is the perimeter of a square with each side measuring 4 cm?",
        "options": ["12 cm", "14 cm", "16 cm", "20 cm"],
        "correct_option": 3,
        "solution": "The perimeter of a square is 4 times the length of one side. 4 × 4 = 16 cm."
    },
    {
        
                "exam": exams[22],
        "language": "English",
        "text": "What is 25 × 3?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 2,
        "solution": "25 multiplied by 3 is 75."
    },
    {
        
                "exam": exams[22],
        "language": "English",
        "text": "What is the area of a rectangle with a length of 6 cm and width of 3 cm?",
        "options": ["15 cm²", "18 cm²", "20 cm²", "24 cm²"],
        "correct_option": 2,
        "solution": "The area of the rectangle is 18 cm² (length × width)."
    },
    {
        
                "exam": exams[22],
        "language": "English",
        "text": "What is the sum of 45 and 35?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 1,
        "solution": "The sum of 45 and 35 is 80."
    },
    {
        
                "exam": exams[22],
        "language": "Hindi",
        "text": "18 ÷ 3 क्या है?",
        "options": ["5", "6", "7", "8"],
        "correct_option": 2,
        "solution": "18 को 3 से विभाजित करने पर 6 मिलता है।"
    },
    {
        
                "exam": exams[22],
        "language": "Hindi",
        "text": "एक वर्ग का परिधि क्या है जिसका प्रत्येक किनारा 4 सेंटीमीटर है?",
        "options": ["12 सेंटीमीटर", "14 सेंटीमीटर", "16 सेंटीमीटर", "20 सेंटीमीटर"],
        "correct_option": 3,
        "solution": "वर्ग का परिधि 4 गुना एक किनारे की लंबाई होती है। 4 × 4 = 16 सेंटीमीटर।"
    },
    {
        
                "exam": exams[22],
        "language": "Hindi",
        "text": "25 × 3 क्या है?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 2,
        "solution": "25 को 3 से गुणा करने पर 75 मिलता है।"
    },
    {
        
                "exam": exams[22],
        "language": "Hindi",
        "text": "एक आयत का क्षेत्रफल क्या होगा जिसकी लंबाई 6 सेंटीमीटर और चौड़ाई 3 सेंटीमीटर है?",
        "options": ["15 वर्ग सेंटीमीटर", "18 वर्ग सेंटीमीटर", "20 वर्ग सेंटीमीटर", "24 वर्ग सेंटीमीटर"],
        "correct_option": 2,
        "solution": "आयत का क्षेत्रफल 18 वर्ग सेंटीमीटर होगा (लंबाई × चौड़ाई)।"
    },
    {
        
                "exam": exams[22],
        "language": "Hindi",
        "text": "45 और 35 का योगफल क्या है?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 1,
        "solution": "45 और 35 का योगफल 80 है।"
    },
     {
        
                "exam": exams[23],
        "language": "English",
        "text": "What is the square root of 64?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "The square root of 64 is 8."
    },
    {
        
                "exam": exams[23],
        "language": "English",
        "text": "What is 9 × 7?",
        "options": ["56", "63", "72", "81"],
        "correct_option": 2,
        "solution": "9 multiplied by 7 is 63."
    },
    {
        
                "exam": exams[23],
        "language": "English",
        "text": "What is the area of a triangle with base 10 cm and height 6 cm?",
        "options": ["30 cm²", "40 cm²", "50 cm²", "60 cm²"],
        "correct_option": 1,
        "solution": "The area of the triangle is 30 cm² (base × height ÷ 2)."
    },
    {
        
                "exam": exams[23],
        "language": "English",
        "text": "What is the sum of 150 and 275?",
        "options": ["425", "450", "475", "500"],
        "correct_option": 1,
        "solution": "The sum of 150 and 275 is 425."
    },
    {
        
                "exam": exams[23],
        "language": "English",
        "text": "What is 12 ÷ 4?",
        "options": ["2", "3", "4", "5"],
        "correct_option": 2,
        "solution": "12 divided by 4 is 3."
    },
    {
        
                "exam": exams[23],
        "language": "Hindi",
        "text": "64 का वर्गमूल क्या है?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "64 का वर्गमूल 8 है।"
    },
    {
        
                "exam": exams[23],
        "language": "Hindi",
        "text": "9 × 7 क्या है?",
        "options": ["56", "63", "72", "81"],
        "correct_option": 2,
        "solution": "9 को 7 से गुणा करने पर 63 मिलता है।"
    },
    {
        
                "exam": exams[23],
        "language": "Hindi",
        "text": "एक त्रिकोण का क्षेत्रफल क्या होगा जिसकी आधार 10 सेंटीमीटर और ऊंचाई 6 सेंटीमीटर है?",
        "options": ["30 वर्ग सेंटीमीटर", "40 वर्ग सेंटीमीटर", "50 वर्ग सेंटीमीटर", "60 वर्ग सेंटीमीटर"],
        "correct_option": 1,
        "solution": "त्रिकोण का क्षेत्रफल 30 वर्ग सेंटीमीटर होगा (आधार × ऊंचाई ÷ 2)।"
    },
    {
        
                "exam": exams[23],
        "language": "Hindi",
        "text": "150 और 275 का योगफल क्या है?",
        "options": ["425", "450", "475", "500"],
        "correct_option": 1,
        "solution": "150 और 275 का योगफल 425 है।"
    },
    {
        
                "exam": exams[23],
        "language": "Hindi",
        "text": "12 ÷ 4 क्या है?",
        "options": ["2", "3", "4", "5"],
        "correct_option": 2,
        "solution": "12 को 4 से विभाजित करने पर 3 मिलता है।"
    },
     {
        
                "exam": exams[24],
        "language": "English",
        "text": "What is 15 × 8?",
        "options": ["120", "130", "140", "150"],
        "correct_option": 1,
        "solution": "15 multiplied by 8 is 120."
    },
    {
        
                "exam": exams[24],
        "language": "English",
        "text": "What is the perimeter of a rectangle with length 12 cm and width 8 cm?",
        "options": ["40 cm", "50 cm", "60 cm", "70 cm"],
        "correct_option": 1,
        "solution": "The perimeter of a rectangle is 2 × (length + width), so 2 × (12 + 8) = 40 cm."
    },
    {
        
                "exam": exams[24],
        "language": "English",
        "text": "What is 45 ÷ 9?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 1,
        "solution": "45 divided by 9 is 5."
    },
    {
        
                "exam": exams[24],
        "language": "English",
        "text": "What is the product of 12 and 7?",
        "options": ["72", "75", "78", "84"],
        "correct_option": 4,
        "solution": "The product of 12 and 7 is 84."
    },
    {
        
                "exam": exams[24],
        "language": "English",
        "text": "What is the area of a square with side length 6 cm?",
        "options": ["30 cm²", "36 cm²", "42 cm²", "48 cm²"],
        "correct_option": 2,
        "solution": "The area of a square is side × side, so 6 × 6 = 36 cm²."
    },
    {
        
                "exam": exams[24],
        "language": "Hindi",
        "text": "15 × 8 क्या है?",
        "options": ["120", "130", "140", "150"],
        "correct_option": 1,
        "solution": "15 को 8 से गुणा करने पर 120 मिलता है।"
    },
    {
        
                "exam": exams[24],
        "language": "Hindi",
        "text": "एक आयत का परिधि क्या होगा, जिसकी लंबाई 12 सेंटीमीटर और चौड़ाई 8 सेंटीमीटर है?",
        "options": ["40 सेंटीमीटर", "50 सेंटीमीटर", "60 सेंटीमीटर", "70 सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का परिधि 2 × (लंबाई + चौड़ाई) होता है, तो 2 × (12 + 8) = 40 सेंटीमीटर।"
    },
    {
        
                "exam": exams[24],
        "language": "Hindi",
        "text": "45 ÷ 9 क्या है?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "45 को 9 से विभाजित करने पर 5 मिलता है।"
    },
    {
        
                "exam": exams[24],
        "language": "Hindi",
        "text": "12 और 7 का गुणनफल क्या है?",
        "options": ["72", "75", "78", "84"],
        "correct_option": 4,
        "solution": "12 और 7 का गुणनफल 84 है।"
    },
    {
        
                "exam": exams[24],
        "language": "Hindi",
        "text": "एक वर्ग का क्षेत्रफल क्या होगा, जिसका एक भुजा 6 सेंटीमीटर है?",
        "options": ["30 वर्ग सेंटीमीटर", "36 वर्ग सेंटीमीटर", "42 वर्ग सेंटीमीटर", "48 वर्ग सेंटीमीटर"],
        "correct_option": 2,
        "solution": "वर्ग का क्षेत्रफल भुजा × भुजा होता है, तो 6 × 6 = 36 वर्ग सेंटीमीटर।"
    },
     {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the dimensional formula of force?",
        "options": ["MLT^-2", "ML^-1T^-2", "ML^2T^-2", "MLT^-1"],
        "solution": "The dimensional formula of force is MLT^-2.",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "Which physical quantity is measured in Hertz?",
        "options": ["Frequency", "Force", "Energy", "Power"],
        "solution": "Frequency is measured in Hertz.",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of acceleration due to gravity on Earth?",
        "options": ["9.8 m/s^2", "10.8 m/s^2", "8.8 m/s^2", "7.8 m/s^2"],
        "solution": "The acceleration due to gravity on Earth is 9.8 m/s^2.",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a scalar quantity?",
        "options": ["Speed", "Velocity", "Force", "Momentum"],
        "solution": "Speed is a scalar quantity.",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the SI unit of work?",
        "options": ["Joule", "Newton", "Watt", "Pascal"],
        "solution": "The SI unit of work is Joule.",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "बल का विमीय सूत्र क्या है?",
        "options": ["MLT^-2", "ML^-1T^-2", "ML^2T^-2", "MLT^-1"],
        "solution": "बल का विमीय सूत्र MLT^-2 है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "कौन सा भौतिक मात्रा हर्ट्ज़ में मापा जाता है?",
        "options": ["आवृत्ति", "बल", "ऊर्जा", "शक्ति"],
        "solution": "आवृत्ति हर्ट्ज़ में मापा जाता है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी पर गुरुत्वाकर्षण के कारण त्वरण का मान क्या है?",
        "options": ["9.8 मी/से^2", "10.8 मी/से^2", "8.8 मी/से^2", "7.8 मी/से^2"],
        "solution": "पृथ्वी पर गुरुत्वाकर्षण के कारण त्वरण का मान 9.8 मी/से^2 है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन एक अदिश मात्रा है?",
        "options": ["गति", "वेग", "बल", "संचलन"],
        "solution": "गति एक अदिश मात्रा है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "कार्य की एसआई इकाई क्या है?",
        "options": ["जूल", "न्यूटन", "वाट", "पास्कल"],
        "solution": "कार्य की एसआई इकाई जूल है।",
        "correct_option": 1
    },
     {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the derivative of (x^2)?",
        "options": ["1", "2x", "x", "2"],
        "solution": "The derivative of (x^2) is 2x.",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "If the matrix A is of order 2x2, how many elements does it have?",
        "options": ["2", "4", "6", "8"],
        "solution": "A matrix of order 2x2 has 4 elements.",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the integral of (1/x)?",
        "options": ["ln(x)", "x", "x^2/2", "1/(2x)"],
        "solution": "The integral of (1/x) is ln(x).",
        "correct_option": 1
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the sum of the angles in a triangle?",
        "options": ["90 degrees", "180 degrees", "270 degrees", "360 degrees"],
        "solution": "The sum of the angles in a triangle is 180 degrees.",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "Solve for x: (2x + 3 = 7)",
        "options": ["1", "2", "3", "4"],
        "solution": "The solution for (2x + 3 = 7) is x = 2.",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "क्या है (x^2) का अवकलन?",
        "options": ["1", "2x", "x", "2"],
        "solution": "(x^2) का अवकलन 2x है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "यदि मैट्रिक्स A का क्रम 2x2 है, तो इसमें कितने तत्व होते हैं?",
        "options": ["2", "4", "6", "8"],
        "solution": "क्रम 2x2 का एक मैट्रिक्स में 4 तत्व होते हैं।",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "(1/x) का समाकलन क्या है?",
        "options": ["ln(x)", "x", "x^2/2", "1/(2x)"],
        "solution": "(1/x) का समाकलन ln(x) है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज में कोणों का योग कितना होता है?",
        "options": ["90 डिग्री", "180 डिग्री", "270 डिग्री", "360 डिग्री"],
        "solution": "त्रिभुज में कोणों का योग 180 डिग्री होता है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "x के लिए हल करें: (2x + 3 = 7)",
        "options": ["1", "2", "3", "4"],
        "solution": "(2x + 3 = 7) के लिए हल x = 2 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the derivative of (e^x)?",
        "options": ["1", "e^x", "x", "e"],
        "solution": "The derivative of (e^x) is (e^x).",
        "correct_option": 2
    },
    {
        
                "exam": exams[27],
        "time": 1.5,
        "language": "Hindi",
        "text": "समीकरण (2x - 5 = 9) का हल क्या है?",
        "options": ["2", "4", "7", "5"],
        "solution": "समीकरण (2x - 5 = 9) का हल (x = 7) है।",
        "correct_option": 3
    },
     {
        
                "exam": exams[27],
        "time": 1.5,
        "language": "Hindi",
        "text": "यदि A = {1, 2, 3}, तो A का पावर सेट क्या है?",
        "options": ["{{1}, {2}, {3}}", "{{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}", "{{1}, {2}, {3}, {1,2,3}}", "{{1,2}, {2,3}, {1,3}}"],
        "solution": "A का पावर सेट {{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}} है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the solution to the equation (2x - 5 = 9)?",
        "options": ["2", "4", "7", "5"],
        "solution": "The solution to the equation (2x - 5 = 9) is (x = 7).",
        "correct_option": 3
    },
    {
        
                "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of (log(1))?",
        "options": ["0", "1", "10", "Infinity"],
        "solution": "The value of (log(1)) is 0.",
        "correct_option": 1
    },
    {
        
                "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(e^x) का अवकलन क्या है?",
        "options": ["1", "e^x", "x", "e"],
        "solution": "(e^x) का अवकलन (e^x) है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(sin(90^circ)) का मान क्या है?",
        "options": ["0", "1", "-1", "0.5"],
        "solution": "(sin(90^circ)) का मान 1 है।",
        "correct_option": 2
    },
    {
        
                "exam": exams[28],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of (sin(90^circ))?",
        "options": ["0", "1", "-1", "0.5"],
        "solution": "The value of (sin(90^circ)) is 1.",
        "correct_option": 2
    },
    
    {
        
                "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(log(1)) का मान क्या है?",
        "options": ["0", "1", "10", "अनंत"],
        "solution": "(log(1)) का मान 0 है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[28],
        "time": 1.5,
        "language": "English",
        "text": "If A = {1, 2, 3}, what is the power set of A?",
        "options": ["{{1}, {2}, {3}}", "{{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}", "{{1}, {2}, {3}, {1,2,3}}", "{{1,2}, {2,3}, {1,3}}"],
        "solution": "The power set of A is {{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}.",
        "correct_option": 2
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the unit of length?",
        "options": ["Meter", "Kilogram", "Newton", "Second"],
        "solution": "The unit of length is Meter.",
        "correct_option": 1
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the state of water at 0°C?",
        "options": ["Solid", "Liquid", "Gas", "Plasma"],
        "solution": "Water is in solid state at 0°C (Ice).",
        "correct_option": 1
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is not a natural source of light?",
        "options": ["Sun", "Moon", "Star", "Lamp"],
        "solution": "Lamp is not a natural source of light.",
        "correct_option": 4
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that opposes motion between two surfaces?",
        "options": ["Magnetism", "Gravity", "Friction", "Electricity"],
        "solution": "The force that opposes motion between two surfaces is Friction.",
        "correct_option": 3
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What do you call the process of water changing from liquid to gas?",
        "options": ["Freezing", "Evaporation", "Condensation", "Melting"],
        "solution": "The process of water changing from liquid to gas is Evaporation.",
        "correct_option": 2
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "लंबाई की इकाई क्या है?",
        "options": ["मीटर", "किलोग्राम", "न्यूटन", "सेकंड"],
        "solution": "लंबाई की इकाई मीटर है।",
        "correct_option": 1
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "0°C पर पानी की अवस्था क्या होती है?",
        "options": ["ठोस", "तरल", "गैस", "प्लाज्मा"],
        "solution": "0°C पर पानी ठोस अवस्था में होता है (बर्फ)।",
        "correct_option": 1
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा प्राकृतिक प्रकाश का स्रोत नहीं है?",
        "options": ["सूरज", "चाँद", "तारा", "दीपक"],
        "solution": "दीपक प्राकृतिक प्रकाश का स्रोत नहीं है।",
        "correct_option": 4
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "दो सतहों के बीच गति का विरोध करने वाली शक्ति क्या है?",
        "options": ["चुम्बकत्व", "गुरुत्वाकर्षण", "घर्षण", "विद्युत"],
        "solution": "दो सतहों के बीच गति का विरोध करने वाली शक्ति घर्षण है।",
        "correct_option": 3
    },
    {
        
                "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "पानी का तरल से गैस में बदलने की प्रक्रिया को क्या कहते हैं?",
        "options": ["जमना", "वाष्पीकरण", "संघनन", "पिघलना"],
        "solution": "पानी का तरल से गैस में बदलने की प्रक्रिया वाष्पीकरण कहलाती है।",
        "correct_option": 2
    }
    ]

        question_added_count = 0
        for question in questions_data:
            existing_question = Question.objects.filter(
                exam=question["exam"],
                text=question["text"]
            ).first()

            if not existing_question:
                Question.objects.create(
                    exam=question["exam"],
                    language=question["language"],
                    text=question["text"],
                    options=question["options"],
                    solution=question["solution"],
                    correct_option=question["correct_option"],
                )
                question_added_count += 1

        response_data["questions"] = {
            "message": f'{question_added_count} questions added successfully.',
            "added_count": question_added_count
        }

    return JsonResponse(response_data)

