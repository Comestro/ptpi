import requests
import json

# Replace with actual teacher ID and token if needed
# But TeacherDetailAPIView has AllowAny
url = "https://api.ptpinstitute.com/api/teacher/470/"
try:
    resp = requests.get(url)
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
