# TeacherHire Test Suite Documentation

A robust, modular test suite has been implemented for the `teacherhire` application using Django's `TestCase` and REST Framework's `APITestCase`.

## 📂 Structure
The tests are organized within the `teacherhire/tests/` package:

- **`factories.py`**: Helper functions to create test data (Users, Exams, Questions, etc.) without boilerplate.
- **`test_models.py`**: Unit tests for model logic, constraints, and auto-generation (e.g., `user_code`).
- **`test_serializers.py`**: Validation logic tests, specifically ensuring complex rules (like unique options in questions) are enforced.
- **`test_auth.py`**: Integration tests for Login, Logout, Registration, and Role-Based Access Control.
- **`test_permissions.py`**: Unit tests for custom permission classes (e.g., `IsAdminUser`, `IsTeacherUser`).
- **`test_admin_api.py`**: Management endpoints for Skills, Subjects, Question Managers, and Exam Centers.
- **`test_exam_api.py`**: End-to-end flow for creating exams, submitting results, and attempt tracking.

---

## 🚀 How to Run Tests

Ensure your virtual environment is active and all dependencies are installed.

### Run all tests
```bash
python manage.py test teacherhire.tests
```

### Run specific test file
```bash
python manage.py test teacherhire.tests.test_models
```

### Run with verbosity (details)
```bash
python manage.py test teacherhire.tests --verbosity=2
```

---

## 🛠️ Key Improvements Made
During test implementation, several fixes were applied to the core codebase:
1. **Security Fixed**: `AllTeacherViewSet` was previously unprotected (commented out permissions). It is now restricted to Admin users.
2. **Crash Fixed**: `ValidationError` was importing from `django.db.models` (which caused a crash in Django 4.2). It was corrected to `django.core.exceptions`.
3. **Consistency**: Ensured `AssignedQuestionUser` status toggling correctly deactivates the associated User's login account.
4. **Attempt Tracking**: Verified that English and Hindi exam attempts are tracked independently as per the user's latest requirements.

> [!TIP]
> Use `factories.py` for any new tests you create to keep the code clean and maintain consistent data state.
