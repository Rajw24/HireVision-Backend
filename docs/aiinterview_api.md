# AI Interview API Documentation

## Authentication
All endpoints require JWT Authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Endpoints

### Start Interview

**Endpoint:** `/aiinterview/start-interview/`

**Method:** `POST`

**Description:** Creates a new interview session and analyzes the uploaded resume.

**Request Body:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `resume` (file, required): PDF file containing the candidate's resume

**Response:**
```json
{
    "interview_id": "integer",
    "question": "string",
    "message": "string"
}
```

**Status Codes:**
- `201`: Created - Interview started successfully
- `400`: Bad Request - Invalid resume format or missing file
- `401`: Unauthorized - Invalid or missing token

### Next Question

**Endpoint:** `/aiinterview/next-question/`

**Method:** `POST`

**Description:** Processes the current answer and generates the next interview question.

**Request Body:**
```json
{
    "interview_id": "integer",
    "answer": "string"
}
```

**Response:**
```json
{
    "question": "string",
    "question_number": "integer",
    "status": "string"  // "ongoing" or "completed"
}
```

**Status Codes:**
- `200`: OK - Next question generated successfully
- `400`: Bad Request - Invalid input or interview already completed
- `401`: Unauthorized - Invalid or missing token
- `404`: Not Found - Interview not found

### Get Results

**Endpoint:** `/aiinterview/results/<interview_id>/`

**Method:** `GET`

**Description:** Retrieves the complete results and analysis of a finished interview.

**Response:**
```json
{
    "candidate_name": "string",
    "scores": {
        "accuracy": "float",
        "fluency": "float",
        "rhythm": "float",
        "overall": "float"
    },
    "feedback": "string",
    "responses": [
        {
            "question": "string",
            "answer": "string"
        }
    ]
}
```

**Status Codes:**
- `200`: OK - Results retrieved successfully
- `401`: Unauthorized - Invalid or missing token
- `404`: Not Found - Interview not found

### Get Interview History

**Endpoint:** `/aiinterview/history/`

**Method:** `GET`

**Description:** Retrieves a list of all interviews conducted by the authenticated user.

**Response:**
```json
[
    {
        "id": "integer",
        "created_at": "datetime",
        "completed": "boolean",
        "candidate_name": "string"
    }
]
```

**Status Codes:**
- `200`: OK - History retrieved successfully
- `401`: Unauthorized - Invalid or missing token

### Get Interview Details

**Endpoint:** `/aiinterview/details/<interview_id>/`

**Method:** `GET`

**Description:** Retrieves detailed information about a specific interview session.

**Response:**
```json
{
    "id": "integer",
    "candidate_name": "string",
    "created_at": "datetime",
    "completed": "boolean",
    "resume_content": "string",
    "responses": [
        {
            "question_number": "integer",
            "question": "string",
            "answer": "string",
            "created_at": "datetime"
        }
    ]
}
```

**Status Codes:**
- `200`: OK - Details retrieved successfully
- `401`: Unauthorized - Invalid or missing token
- `404`: Not Found - Interview not found

## Error Handling

The API returns error responses in the following format:
```json
{
    "error": "string",
    "message": "string",
    "details": "object (optional)"
}
```

Common error codes:
- `400`: Bad Request - Invalid input data
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server-side error

## Best Practices

1. **Resume Format**
   - Only PDF files are accepted
   - Maximum file size: 5MB
   - Ensure the PDF is text-searchable for best results

2. **Answer Format**
   - Maximum answer length: 2000 characters
   - Avoid HTML or markdown formatting
   - Special characters are supported

3. **Rate Limiting**
   - Maximum 10 requests per minute per user
   - Maximum 3 concurrent interviews per user

4. **Interview Session**
   - Sessions timeout after 30 minutes of inactivity
   - Maximum 10 questions per interview
   - Results are available immediately after completion

## Additional Notes

- All timestamps are returned in ISO 8601 format
- The API uses UTF-8 encoding for all text data
- Responses are cached for 5 minutes where applicable
- Large result sets are paginated with 20 items per page
