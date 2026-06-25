# Forgot Password Flow - Setup & Fixes

## Recent Updates (Feb 2026) ✨

### Major Bug Fixes:
1. **Email Sending Not Tracked** ✅
   - Changed from async background task to synchronous sending with error handling
   - Now returns success/failure status to frontend
   - Added comprehensive logging

2. **Email Service Enhanced** ✅
   - Better error messages (SMTP auth errors, connection errors, etc.)
   - Added timeout to SMTP connection
   - Validates configuration on initialization
   - Detailed logging for debugging

3. **Frontend Improvements** ✅
   - Added alternative "Reset Code" method if email fails
   - Two-method toggle: Email vs. Direct Code
   - Copy-to-clipboard for reset tokens
   - Better error handling and user feedback
   - Shows reset token if email method fails

4. **New Debug/Fallback Endpoints** ✅
   - `/api/auth/test-email` - Test SMTP configuration
   - `/api/auth/forgot-password-code` - Get reset token without email

## Issues Fixed ✅

### 1. **Frontend - Forgot Password Button Not Connected**
   - **Problem**: The "Forgot password?" button in Login.jsx was not clickable/linked
   - **Solution**: Added `Link` to navigate to `/forgot-password` page
   - **File**: `frontend/src/pages/Login.jsx`

### 2. **API Call - Incorrect Parameter Format**
   - **Problem**: `authAPI.forgotPassword()` was passing email incorrectly
   - **Solution**: Fixed to use proper `params: { email }` format
   - **File**: `frontend/src/services/api.js`

### 3. **EMAIL SENDING NOT WORKING (PRIMARY BUG)**
   - **Problem**: Email sent via `background_tasks.add_task()` with no error tracking
   - **Solution**: 
     - Changed to synchronous email sending
     - Added try-catch error handling
     - Returns success/failure status
     - Added logging at each step
   - **File**: `backend/app.py` (forgot_password endpoint)

### 4. **No Fallback If Email Fails**
   - **Problem**: Users had no way to reset password if email wasn't working
   - **Solution**: 
     - Added alternative "Reset Code" method
     - Direct API endpoint to get token without email
     - Frontend toggle between Email and Code methods
   - **Files**: `frontend/src/pages/ForgotPassword.jsx`, `backend/app.py`

### 5. **No SMTP Debugging Capability**
   - **Problem**: No way to test if SMTP was configured correctly
   - **Solution**: Added `/api/auth/test-email` endpoint
   - **File**: `backend/app.py`

## Password Reset Flow

### Step 1: Forgot Password
1. User clicks "Forgot password?" on login page
2. Navigates to `/forgot-password`
3. Enters email address
4. Backend sends reset email with token link (or generates code)

### Step 2: Reset Password
1. User clicks reset link in email: `http://localhost:5173/reset-password?token=<TOKEN>`
   - OR gets token from "Reset Code" method and goes to reset-password page
2. Enters new password and confirmation
3. Submits reset form
4. Backend validates token and updates password
5. Redirects to login page

## Email Service Setup

### Prerequisites
You need to configure email service in `.env` file:

```env
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
FROM_NAME=CSIO ThermalStream
```

### Configure Gmail SMTP

1. **Enable 2FA on Gmail Account**
   - Go to myaccount.google.com
   - Click Security on the left
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or your device)
   - Google generates a 16-character password
   - Copy and paste into `SMTP_PASSWORD` in `.env`

3. **Alternative Email Providers**
   - Outlook: `smtp.outlook.com:587`
   - SendGrid: `smtp.sendgrid.net:587`
   - AWS SES: `email-smtp.[region].amazonaws.com:587`

## Testing the Flow

### Manual Test
1. **Start the application**
   ```bash
   cd frontend && npm run dev
   cd backend && uvicorn app:app --reload
   ```

2. **Test SMTP Configuration (NEW)**
   ```bash
   # Call the test endpoint
   curl -X POST "http://localhost:8000/api/auth/test-email?to_email=your-test-email@example.com"
   
   # Response will show if SMTP is working:
   # {"success": true, "message": "Test email sent successfully"}
   # or
   # {"success": false, "message": "Error: SMTP Authentication failed..."}
   ```

3. **Test forgot password - EMAIL METHOD**
   - Go to http://localhost:5173/login
   - Click "Forgot password?"
   - Toggle to "Email" method (default)
   - Enter your test email
   - Should see success/failure message with error details
   - Check email inbox or backend logs

4. **Test forgot password - RESET CODE METHOD**
   - Go to http://localhost:5173/login
   - Click "Forgot password?"
   - Toggle to "Code" button
   - Enter your test email
   - Copy the reset token displayed
   - Go to /reset-password and paste token

5. **Reset password**
   - Click reset link from email OR use code method
   - Enter new password (minimum 8 characters)
   - Confirm password
   - Click "Reset Password"
   - Should see success message and redirect to login

6. **Login with new password**
   - Use new password to login
   - Should successfully login

### Email Not Received?

**Check These In Order:**
1. Test SMTP first: `curl -X POST "http://localhost:8000/api/auth/test-email?to_email=test@example.com"`
2. Check `.env` file for correct SMTP credentials
3. SMTP_PASSWORD must be app-specific password (not Gmail password)
4. Gmail account must have 2FA enabled
5. Check spam/junk folder
6. Check backend logs for specific error messages

**Backend Logs to Check:**
```
# Look for these messages in uvicorn output:
"✓ Email sent successfully to user@example.com"  
"✗ SMTP Authentication failed: Check SMTP_USER and SMTP_PASSWORD"
"✗ SMTP Error: Connection refused"
"✗ Error sending email: [specific error]"
```

## API Endpoints (Updated)

### POST /api/auth/forgot-password
- **Params**: `email` (string)
- **Returns**: 
  ```json
  {
    "message": "If the email exists, a reset link has been sent",
    "success": true/false,
    "error": "optional error message"
  }
  ```
- **Notes**: Returns success status + error details (if any)

### GET /api/auth/forgot-password-code (NEW)
- **Params**: `email` (string)
- **Returns**: 
  ```json
  {
    "message": "Reset code generated successfully",
    "reset_token": "token-string",
    "expires_in": "1 hour"
  }
  ```
- **Notes**: Alternative method if email isn't working

### POST /api/auth/test-email (NEW)
- **Params**: `to_email` (string, optional - defaults to "test@example.com")
- **Returns**: 
  ```json
  {
    "success": true/false,
    "message": "Test email sent successfully" or error description
  }
  ```
- **Notes**: For debugging SMTP configuration

### POST /api/auth/reset-password
- **Params**: `token` (string), `new_password` (string)
- **Returns**: `{"message": "Password reset successful"}`

## Files Modified

### Frontend
- `src/pages/ForgotPassword.jsx` - Complete redesign with two methods
- `src/services/api.js` - Added `getResetCode()` and `testEmail()` methods
- Routes already set up in `App.jsx`

### Backend
- `app.py` - Updated forgot_password endpoint with error handling + new endpoints
- `email_service.py` - Enhanced with better error handling and logging

## Database

Make sure User table has these fields (should already exist):
- `reset_token` - VARCHAR for storing reset token
- `reset_token_expires` - DATETIME for token expiration

If missing, run migration or add manually:
```sql
ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN reset_token_expires DATETIME;
```

## Troubleshooting

### "✗ SMTP Authentication failed" Error
- Your SMTP credentials are incorrect
- For Gmail: Make sure you're using App Password, not your Gmail password
- App Password needs 2FA enabled on Gmail account
- Try the test endpoint to verify

### "Connection refused" or Timeout
- SMTP_HOST or SMTP_PORT incorrect
- Firewall is blocking SMTP port 587
- Internet connection issue

### Reset link expired
- User took more than 1 hour to reset
- Token expiration is set to 1 hour in backend
- User can request another reset link

### Token not found/invalid
- User clicked old/expired link
- Token was manually edited in URL
- User should request new password reset

### Password change not taking effect
- Check browser localStorage is cleared
- New password might not meet requirements (8+ chars)
- Check backend logs for database errors

## Security Notes

✅ **Good Practices Implemented:**
- Tokens are cryptographically secure (secrets.token_urlsafe)
- Tokens expire after 1 hour
- User email not revealed in response (prevents account enumeration)
- Password reset requires new password confirmation
- Old session tokens remain valid (user must login with new password)
- Email credentials never sent to frontend (server-side only)

## Quick Fix Checklist

If forgot password isn't working:
- [ ] Check `.env` has SMTP configuration
- [ ] Run test endpoint: `curl -X POST "http://localhost:8000/api/auth/test-email?to_email=your-email@gmail.com"`
- [ ] Check backend logs for specific error
- [ ] If email fails, use "Code" method instead
- [ ] Verify token hasn't expired (1 hour limit)
- [ ] Check spam folder for reset email

## Future Enhancements

Optional improvements:
- Add rate limiting to forgot password endpoint
- Send OTP via SMS as alternative
- Send confirmation email after password change
- Password strength requirements UI feedback
- Remember "me" feature on login
- Admin ability to reset user passwords

