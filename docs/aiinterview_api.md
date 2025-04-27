# AI Interview API Documentation

## Overview
The AI Interview API provides endpoints for conducting automated technical interviews, analyzing responses, and generating comprehensive feedback. All endpoints require authentication using JWT tokens.

## Authentication
- All endpoints require a valid JWT token in the Authorization header
- Format: `Authorization: Bearer <your_jwt_token>`

## Base URL
```
https://hirevision-backend.vercel.app/api/interview/
```

## Endpoints

### 1. Upload Resume
Upload a candidate's resume before starting the interview.

**Endpoint:** `/upload-resume/`  
**Method:** `POST`  
**Content-Type:** `multipart/form-data`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| resume | File | Yes | PDF file of the candidate's resume |

#### Response
```json
{
    "status": "success",
    "message": "Resume uploaded successfully",
    "interview_id": "uuid"
}
```

#### Error Responses
```json
{
    "error": "Missing file",
    "details": "Resume file is required"
}
```
```json
{
    "error": "Invalid file",
    "details": "File must be a PDF"
}
```

### 2. Start Interview
Initialize a new interview session or resume an existing one.

**Endpoint:** `/start/`  
**Method:** `POST`  
**Content-Type:** `application/json`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| interview_id | string | No | UUID of an existing interview (for resuming) |

#### Response
```json
{
    "status": "success",
    "interview_id": "uuid",
    "question": "string",
    "question_number": 1
}
```

#### Error Responses
```json
{
    "error": "Interview initialization failed",
    "details": "error message"
}
```
```json
{
    "error": "Interview not found",
    "details": "Invalid interview_id"
}
```

### 3. Next Question
Submit an answer and receive the next question.

**Endpoint:** `/next-question/`  
**Method:** `POST`  
**Content-Type:** `application/json`

#### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| interview_id | string | Yes | UUID of the current interview |
| answer | string | Yes | Candidate's answer to the current question |

#### Success Response (During Interview)
```json
{
    "status": "success",
    "question": "string",
    "question_number": number
}
```

#### Success Response (Interview Completion)
```json
{
    "status": "completed",
    "result_id": "uuid",
    "analysis": {
        "technical_accuracy": number,
        "depth_of_knowledge": number,
        "relevance_score": number,
        "grammar_score": number,
        "clarity_score": number,
        "professionalism_score": number,
        "positive_sentiment": number,
        "neutral_sentiment": number,
        "negative_sentiment": number,
        "compound_sentiment": number,
        "overall_technical_score": number,
        "overall_communication_score": number,
        "final_score": number,
        "technical_feedback": string,
        "communication_feedback": string,
        "strengths": string[],
        "areas_for_improvement": string[],
        "vocabulary_analysis": object
    }
}
```

#### Error Responses
```json
{
    "error": "Missing required fields",
    "details": "interview_id and answer are required"
}
```
```json
{
    "error": "Interview not found",
    "details": "Invalid interview_id or unauthorized access"
}
```

### 4. Get Interview Results
Retrieve the complete analysis and results of a finished interview.

**Endpoint:** `/results/<interview_id>/`  
**Method:** `GET`

#### URL Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| interview_id | string | Yes | UUID of the completed interview |

#### Response
```json
{
    "candidate_name": "string",
    "technical_scores": {
        "technical_accuracy": number,
        "depth_of_knowledge": number,
        "relevance_score": number,
        "overall_technical_score": number
    },
    "communication_scores": {
        "grammar_score": number,
        "clarity_score": number,
        "professionalism_score": number,
        "overall_communication_score": number
    },
    "sentiment_scores": {
        "positive": number,
        "neutral": number,
        "negative": number,
        "compound": number
    },
    "final_score": number,
    "feedback": {
        "technical_feedback": "string",
        "communication_feedback": "string",
        "strengths": ["string"],
        "areas_for_improvement": ["string"],
        "vocabulary_analysis": object
    },
    "responses": [
        {
            "question": "string",
            "answer": "string"
        }
    ]
}
```

#### Error Response
```json
{
    "error": "Interview not found or unauthorized",
}
```

## Rate Limiting
- Anonymous users: 100 requests per day
- Authenticated users: 1000 requests per day
- Login attempts: 5 per minute

## Interview Flow
1. Upload the candidate's resume (PDF format)
2. Start a new interview session using the returned interview_id
3. Receive the first question
4. Submit answer and receive next question
5. Repeat steps 3-4 until all questions are answered (10 questions total)
6. Receive final analysis and results
7. Access detailed results using the results endpoint

## Notes
- All scores are on a scale of 0-100
- Sentiment scores are on a scale of -1 to 1
- Interview sessions are saved and can be resumed using the interview_id
- Files are processed securely and stored temporarily
- All responses should be handled for proper error management
- The API uses standard HTTP response codes
- All dates are in ISO 8601 format
- Maximum file size for resume upload: 10MB
