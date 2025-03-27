# API Documentation

## Signup API

**Endpoint:** `/auth/signup/`

**Method:** `POST`

**Description:** Registers a new user and sends a verification email.

**Request Parameters:**
- `username` (string): The username of the user.
- `password` (string): The password of the user.
- `email` (string): The email address of the user.
- `first_name` (string): The first name of the user.
- `last_name` (string): The last name of the user.

**Response:**
- `message` (string): Success message if signup is successful.
- `error` (string): Error message if signup fails.

**Status Codes:**
- `201`: Created - Signup successful
- `400`: Bad Request - Invalid input

## Email Verification API

**Endpoint:** `/auth/email-verification/<uidb64>/<token>/`

**Method:** `GET`

**Description:** Verifies the user's email address. Link expires after 10 minutes.

**Response:**
- `message` (string): Success message if email verification is successful.
- `error` (string): Error message if email verification fails.

**Status Codes:**
- `200`: OK - Email verified
- `400`: Bad Request - Invalid or expired token

## Resend Verification Link API

**Endpoint:** `/auth/resend-verification-link/`

**Method:** `POST`

**Description:** Resends the email verification link.

**Request Parameters:**
- `email` (string): The email address of the user.

**Response:**
- `message` (string): Success message if the verification link is resent.
- `error` (string): Error message if resending the verification link fails.

## Signin API

**Endpoint:** `/auth/signin/`

**Method:** `POST`

**Description:** Authenticates the user and returns JWT tokens.

**Request Parameters:**
- `email` (string): The email address of the user.
- `password` (string): The password of the user.
- `remember_me` (boolean): Whether to remember the user for 30 days.

**Response:**
- `message` (string): Success message if signin is successful.
- `refresh` (string): JWT refresh token.
- `access` (string): JWT access token.
- `error` (string): Error message if signin fails.

**Cookies Set:**
- `refresh_token`: HttpOnly secure cookie containing refresh token
- `access_token`: HttpOnly secure cookie containing access token

**Status Codes:**
- `200`: OK - Signin successful
- `400`: Bad Request - Invalid credentials

## Protected Routes

All routes below require JWT Authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Signout API

**Endpoint:** `/auth/signout/`

**Method:** `POST`

**Description:** Logs out the authenticated user and blacklists the JWT token.

**Response:**
- `message` (string): Success message if signout is successful.
- `error` (string): Error message if signout fails.

**Status Codes:**
- `200`: OK - Signout successful
- `400`: Bad Request - Invalid token

## Change Password API

**Endpoint:** `/auth/change-password/`

**Method:** `POST`

**Description:** Changes the password of the authenticated user. Requires user to be active within last 30 days.

**Request Parameters:**
- `new_password` (string): The new password.
- `confirm_password` (string): Confirmation of the new password.

**Response:**
- `message` (string): Success message if the password is changed.
- `error` (string): Error message if changing the password fails.

**Status Codes:**
- `200`: OK - Password changed
- `400`: Bad Request - Invalid input or user inactive

## Forgot Password API

**Endpoint:** `/auth/forgot-password/`

**Method:** `POST`

**Description:** Sends a password reset email to the user.

**Request Parameters:**
- `email` (string): The email address of the user.

**Response:**
- `message` (string): Success message if the password reset email is sent.
- `error` (string): Error message if sending the password reset email fails.

## Reset Password API

**Endpoint:** `/auth/reset-password/<uidb64>/<token>/`

**Method:** `POST`

**Description:** Resets the user's password.

**Request Parameters:**
- `new_password` (string): The new password.
- `confirm_password` (string): Confirmation of the new password.

**Response:**
- `message` (string): Success message if the password is reset.
- `error` (string): Error message if resetting the password fails.
