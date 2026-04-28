# Forgot Password Flow - Complete Setup & Fixes (Final Version)

## Overview

This implementation provides a robust and fault-tolerant password reset system with:
- Email-based reset link
- Direct reset code fallback (if email fails)
- SMTP testing endpoint
- Full error tracking and logging
- Improved frontend UX with method switching

---

## Key Features

1. Reliable Email Handling
- Synchronous email sending (no background task issues)
- Returns success/failure to frontend
- Detailed SMTP error messages
- Connection timeout support
- Config validation at startup

2. Fallback Reset Code Method
- Generates reset token without email dependency
- Useful when SMTP is misconfigured or blocked
- Token displayed directly in UI
- Copy-to-clipboard support

3. Debugging Support
- /api/auth/test-email endpoint for SMTP verification
- Clear backend logs for troubleshooting

4. Frontend Improvements
- Toggle between Email and Reset Code
- Better error messages
- Displays token if email fails
- Proper navigation from login page

---

## Password Reset Flow

Step 1: Request Reset
1. User clicks "Forgot password?" on login page
2. Navigates to /forgot-password
3. Enters email
4. Chooses method:
   - Email (default)
   - Reset Code (fallback)

Step 2: Receive Token
- Email method → Reset link:
  http://localhost:5173/reset-password?token=<TOKEN>
- Code method → Token shown in UI

Step 3: Reset Password
1. User opens /reset-password
2. Enters token, new password, confirm password
3. Backend validates token
4. Password updated
5. Redirect to login

---

## Environment Configuration (.env)

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=CSIO ThermalStream

---

## Gmail SMTP Setup

1. Enable 2-Step Verification
2. Generate App Password:
   https://myaccount.google.com/apppasswords
3. Use generated password in SMTP_PASSWORD

---

## API Endpoints

1. POST /api/auth/forgot-password
Params:
email: string

Response:
{
  "message": "If the email exists, a reset link has been sent",
  "success": true,
  "error": null
}

---

2. GET /api/auth/forgot-password-code
Params:
email: string

Response:
{
  "message": "Reset code generated successfully",
  "reset_token": "token-string",
  "expires_in": "1 hour"
}

---

3. POST /api/auth/test-email
Params:
to_email: string (optional)

Response:
{
  "success": true,
  "message": "Test email sent successfully"
}

---

4. POST /api/auth/reset-password
Params:
token: string
new_password: string

Response:
{
  "message": "Password reset successful"
}

---

## Testing the Flow

Start Servers:
cd frontend && npm run dev
cd backend && uvicorn app:app --reload

---

Step 1: Test SMTP
```bash
curl -X POST "http://localhost:8000/api/auth/test-email?to_email=your-email@example.com"
```
---

Step 2: Test Email Method
- Go to /login
- Click Forgot password
- Enter email
- Check inbox and logs

---

Step 3: Test Code Method
- Toggle to Code
- Enter email
- Copy token
- Go to /reset-password
- Paste token

---

Step 4: Reset Password
- Enter new password (min 8 chars)
- Confirm password
- Submit
- Login with new password

---

## Database Requirements

ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;

---

## Files Updated

Frontend:
- src/pages/Login.jsx
- src/pages/ForgotPassword.jsx
- src/services/api.js

Backend:
- app.py
- email_service.py

---

## Troubleshooting

SMTP Authentication Failed:
- Use App Password (not Gmail password)
- Ensure 2FA is enabled

Connection Refused / Timeout:
- Check SMTP host/port
- Check firewall blocking port 587

Email Not Received:
- Check spam folder
- Verify using /test-email
- Check backend logs

Invalid / Expired Token:
- Token expires in 1 hour
- Request new reset

Password Not Updating:
- Ensure password >= 8 characters
- Check backend logs

---

## Security Notes

- Tokens are cryptographically secure
- Tokens expire in 1 hour
- No email exposure (prevents enumeration)
- Password confirmation required
- Credentials handled server-side only

---

## Quick Checklist

- .env configured correctly
- SMTP tested via /test-email
- Backend logs checked
- Fallback code method works
- Token not expired
- Email not in spam

---

## Future Enhancements

- Rate limiting on forgot password
- SMS OTP support
- Password strength UI
- Email confirmation after reset
- Remember me feature
- Admin reset option