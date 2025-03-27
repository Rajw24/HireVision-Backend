# Aptitude Test API Documentation

## Authentication
All endpoints require authentication using JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Endpoints

### Get User Question History
**Endpoint:** `/aptitude/history/`

**Method:** `GET`

**Description:** Retrieves all questions attempted by the authenticated user.

**Response Parameters:**
- `id` (integer): Question ID
- `question` (string): The question text
- `options` (array): List of possible answers
- `correct_answer` (string): The correct answer
- `explanation` (string): Explanation for the answer
- `exam` (integer): Associated exam ID

**Status Codes:**
- `200`: OK - Request successful
- `401`: Unauthorized - Invalid or missing token

### Start New Exam
**Endpoint:** `/aptitude/start/`

**Method:** `POST`

**Description:** Creates a new exam session with 25 random questions.

**Response Parameters:**
- `exam_id` (integer): The ID of the created exam
- `questions` (array): List of questions containing:
  - `id` (integer): Question ID
  - `question` (string): The question text
  - `options` (array): List of possible answers

**Status Codes:**
- `200`: OK - Exam created successfully
- `401`: Unauthorized - Invalid or missing token

### Submit Exam
**Endpoint:** `/aptitude/submit/`

**Method:** `POST`

**Description:** Submit answers for an exam session.

**Request Parameters:**
- `exam_id` (integer): The ID of the exam being submitted
- `answers` (array): List of answers containing:
  - `question_id` (integer): ID of the question
  - `answer` (string): User's answer for the question

**Response Parameters:**
- `score` (integer): Number of correct answers
- `total` (integer): Total number of questions

**Status Codes:**
- `200`: OK - Exam submitted successfully
- `400`: Bad Request - Exam already submitted
- `401`: Unauthorized - Invalid or missing token
- `404`: Not Found - Exam not found

### Get Exam History
**Endpoint:** `/aptitude/exam-history/`

**Method:** `GET`

**Description:** Retrieves all exams taken by the authenticated user.

**Response Parameters:**
- Array of exam objects containing:
  - `id` (integer): Exam ID
  - `score` (integer): Exam score
  - `completed` (boolean): Exam completion status
  - `created_at` (string): Exam creation timestamp

**Status Codes:**
- `200`: OK - Request successful
- `401`: Unauthorized - Invalid or missing token

### Get Exam Details
**Endpoint:** `/aptitude/exam-details/<exam_id>/`

**Method:** `GET`

**Description:** Retrieves detailed information about a specific exam.

**Path Parameters:**
- `exam_id` (integer): ID of the exam

**Response Parameters:**
- `exam` (object):
  - `id` (integer): Exam ID
  - `score` (integer): Exam score
  - `completed` (boolean): Exam completion status
  - `created_at` (string): Exam creation timestamp
- `questions` (array): List of questions containing:
  - `id` (integer): Question ID
  - `question` (string): Question text
  - `options` (array): List of possible answers
  - `correct_answer` (string): Correct answer
  - `explanation` (string): Answer explanation

**Status Codes:**
- `200`: OK - Request successful
- `401`: Unauthorized - Invalid or missing token
- `404`: Not Found - Exam not found
