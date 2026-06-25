# Forgot Password Flow

## Overview

Thermal Polaris supports email-based password reset and a fallback reset code flow. The backend also includes an SMTP test endpoint to verify mail configuration before attempting password recovery.

## Features

- Request password reset via email
- Fallback reset code endpoint when email delivery is unavailable
- Reset tokens expire after 1 hour
- Secure non-enumeration UX for unknown emails
- SMTP verification endpoint for debugging

## Password Reset Flow

1. User opens `/forgot-password` and submits their email.
2. The backend generates a secure reset token and stores it with a 1-hour expiry.
3. If email is configured correctly, a reset link is sent to the user.
4. If email delivery fails, a reset token can be retrieved via `/api/auth/forgot-password-code`.
5. User opens `/reset-password`, provides the token and new password.
6. Backend validates the token and updates the password.

## API Endpoints

### POST /api/auth/forgot-password

Params:
- `email` (string)

Response:
- `message`
- `success`
- `error` (optional)

### GET /api/auth/forgot-password-code

Query:
- `email` (string)

Response:
- `message`
- `reset_token` (returned when the email exists)
- `expires_in` (1 hour)

### POST /api/auth/test-email

Query or body:
- `to_email` (string, optional)

Response:
- `success`
- `message`
- `email`
- SMTP metadata

### POST /api/auth/reset-password

Params:
- `token` (string)
- `new_password` (string)

Response:
- `message`

## Example Reset Link

When email is delivered successfully, users receive a link such as:

```
http://localhost:5173/reset-password?token=<TOKEN>
```

## SMTP Configuration

Example `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=Thermal Polaris
```

## Testing

1. Start backend and frontend.
2. Verify SMTP:

```bash
curl -X POST "http://localhost:8000/api/auth/test-email?to_email=your-email@example.com"
```

3. Request password reset.
4. If email is unavailable, request the reset code.
5. Use `/api/auth/reset-password` with the token and new password.

## Troubleshooting

- Use an app password for Gmail if authentication fails.
- Check spam/junk folders if email is not received.
- Request a new token if the token expires.
- Verify backend logs for SMTP or token validation errors.

## Notes

- Reset tokens expire in 1 hour.
- The system always returns a generic reset response for unknown emails.
- The reset code endpoint is useful when email delivery cannot be trusted.
