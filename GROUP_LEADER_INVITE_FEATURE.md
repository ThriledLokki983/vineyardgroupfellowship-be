# Group Leader Invite Feature - Implementation Guide

## Overview

This document outlines the recommended implementation for allowing group leaders to invite users to their groups via email, including automatic account creation for non-registered users.

**Feature Requirements:**
1. Group leader provides an email address to invite
2. System checks if user exists in the database
3. If user doesn't exist, create a pending account (inactive until verified)
4. Send invitation email containing group details and acceptance link
5. User accepts invitation and verifies email to activate account
6. User is added to group with appropriate membership status

---

## Current System Analysis

### **Existing Infrastructure**

Your application already has all the necessary building blocks for this feature:

#### 1. **User Model** (`authentication/models.py`)
- Email-based authentication with unique constraint
- Built-in `email_verified` and `is_active` flags for account states
- Username field (auto-generated for invited users)
- UUID primary keys throughout the system
- Support for inactive accounts (perfect for pending invitations)

#### 2. **GroupMembership Model** (`group/models.py`)
- Status field with 'pending', 'active', 'inactive', 'removed' states
- Role-based membership (leader, co_leader, member)
- Unique constraint on (group, user) prevents duplicate memberships
- Tracking fields (joined_at, notes)

#### 3. **Email Verification System** (`authentication/utils/auth.py`)
- Secure token generation with configurable expiry (24 hours)
- Async email sending to prevent request timeouts
- HTML and text template support
- URL building for verification links
- Integration with Django's email backend

#### 4. **Onboarding System** (`onboarding/` app)
- Role-based onboarding flows
- Progress tracking for multi-step processes
- Can be triggered automatically after account creation
- Step-by-step user guidance

**Conclusion:** Your existing architecture is well-suited for invitation functionality. No major refactoring needed.

---

## Recommended Approach: Invite with Pending Account

### **Why This Approach?**

After analyzing multiple implementation strategies, the **Pending Account approach** is the best fit for your application because:

1. **Security First:** Accounts remain inactive until the user explicitly verifies their email and accepts the invitation
2. **Privacy Compliant:** Respects GDPR and privacy laws by requiring user consent before activation
3. **User Control:** Recipients can decline invitations instead of being force-added
4. **Trackable:** Leaders can see invitation status (pending, accepted, declined, expired)
5. **Leverages Existing Code:** Uses your current email verification infrastructure
6. **Clean Database:** Inactive accounts can be auto-purged after expiry
7. **Audit Trail:** Tracks who invited whom and when

---

## Critical Downsides & Challenges

### **1. Multi-Step User Journey (Friction)**

**The Problem:**
New users must complete multiple steps before accessing the group:
1. Click invitation email link
2. Land on registration page
3. Set their password
4. Submit registration form
5. Check email again for verification
6. Click verification link
7. Finally access the group

**Why This Matters:**
- Higher drop-off rate compared to single-click invitations
- Users may forget what step they're on
- Email deliverability issues compound the problem (2 emails required)
- Mobile users switching between email and browser may lose context

**Mitigation Strategies:**
- Combine invitation + verification into single token flow (accept invitation = verify email)
- Show clear progress indicators: "Step 2 of 3: Set Your Password"
- Send reminder emails if registration not completed within 24 hours
- Pre-fill email and group context on registration page
- Implement "magic link" alternative (passwordless first login)

---

### **2. Invitation Expiry Management**

**The Problem:**
Invitations expire after 7 days (or whatever window you choose):
- User opens email on day 8, link is dead
- Leader must resend invitation
- User may feel rejected or confused
- Creates support burden ("Why isn't my link working?")

**Why This Matters:**
- Users check email at different intervals (some weekly)
- Email may be caught in spam filters initially
- User may be on vacation or busy during invitation window
- Expired invitations leave orphaned pending accounts in database

**Mitigation Strategies:**
- Longer expiry window (14 days instead of 7)
- Grace period: Show "expired" message with "Request New Invitation" button
- Auto-resend logic: If user clicks expired link, auto-generate new invitation
- Email reminder at day 5: "Your invitation expires in 2 days"
- Cleanup job: Delete pending accounts after 30 days of inactivity

---

### **3. Shadow Account Pollution**

**The Problem:**
Every invitation creates a User record, even if never accepted:
- Database fills with inactive accounts
- User table bloated with `invited_xyz123` usernames
- Complicates user analytics (how many "real" users?)
- May hit database size limits on hosting plans
- Orphaned accounts create security surface area

**Why This Matters:**
- 100 invitations = 100 User records, even if only 20 accept
- Email uniqueness constraint prevents re-inviting same email
- Inactive accounts may be exploited if token generation is weak
- Makes user metrics unreliable (total users vs active users)

**Mitigation Strategies:**
- Mark invited accounts with `invitation_pending=True` flag
- Scheduled cleanup: Delete unaccepted accounts after 30 days
- Don't count inactive accounts in user metrics
- Use separate `GroupInvitation` table for tracking (recommended)
- Implement soft delete with archive table for audit trail

---

### **4. Username Generation Challenges**

**The Problem:**
Django requires unique usernames, but invited users haven't chosen one yet:
- Must auto-generate: `invited_8a7d9f23` or similar
- Generated username may be ugly if user sees it
- Collision risk if generation logic is naive
- Username change flow needed after acceptance
- Profile URLs may be broken if based on username

**Why This Matters:**
- Poor UX if user sees `invited_8a7d9f23` in profile
- Some parts of your app may display username instead of full name
- Email-based apps often struggle with username requirements
- Username changes break bookmarks/links if not handled properly

**Mitigation Strategies:**
- Generate username from email: `john_doe_a3f7` (first part of email + random)
- Hide username from UI, always show full name
- Allow username customization during onboarding
- Use UUID in URLs instead of username: `/users/abc-123-uuid/`
- Consider making username optional (Django 3.2+ supports this)

---

### **5. Email Deliverability Dependency**

**The Problem:**
Entire flow depends on email delivery:
- Invitation email must reach inbox (not spam)
- Verification email must also be delivered
- User may not check email regularly
- Corporate email filters may block
- Typo in email = invitation goes nowhere

**Why This Matters:**
- SPF/DKIM/DMARC misconfig can break everything
- Gmail/Outlook may flag bulk invitations as spam
- User enters wrong email, thinks invite "didn't work"
- No way to contact user if email bounces
- Leader frustration: "I sent the invite but they say they didn't get it"

**Mitigation Strategies:**
- Email validation before sending (check format + disposable domains)
- "Confirm email" double-entry field for leaders
- Preview: "Invitation will be sent to user@example.com - Is this correct?"
- Track email bounces and show error to leader
- Alternative: In-app notification system for existing users
- Fallback: Leaders can share invitation link directly (copy/paste)

---

### **6. Invitation Spam & Abuse Potential**

**The Problem:**
Without rate limiting, bad actors could:
- Spam invitations to random emails
- Harass users with repeated invitations
- Create thousands of fake accounts
- Flood email servers
- Abuse the feature for phishing (invitation emails look official)

**Why This Matters:**
- Your domain's email reputation could be blacklisted
- Hosting costs increase (email sending quota)
- Legitimate invitations may be blocked due to sender reputation
- Legal liability if abused for spam/harassment
- User trust erodes if they receive unwanted invitations

**Mitigation Strategies:**
- Rate limit: 10 invitations per leader per day
- Max pending invitations per group: 50
- Require CAPTCHA after 5 invitations in 1 hour
- Track invitation acceptance rate; flag suspicious patterns
- Block disposable email domains (guerrillamail.com, etc.)
- Email confirmation: "You're about to send 5 invitations - Continue?"
- Admin dashboard to monitor invitation abuse

---

### **7. Duplicate Invitation Confusion**

**The Problem:**
What happens if a leader invites the same person twice?
- User receives two emails with different tokens
- Only one can be accepted (unique constraint on group + user)
- Confusing if user clicks old invitation link
- Leader may not remember if they already invited someone

**Why This Matters:**
- Poor UX: "This invitation has already been accepted" (even if it wasn't)
- Database complexity: Checking for existing pending invitations
- Race conditions: Two leaders invite same user simultaneously
- Status conflicts: What if user declined first invite but accepted second?

**Mitigation Strategies:**
- Check for existing pending invitations before creating new one
- If duplicate detected, show leader: "Already invited on Nov 8 - Resend?"
- Resend = invalidate old token, generate new one
- Unique constraint: `(group, email, status='pending')` allows only one active invite
- Show invitation history in leader dashboard
- Auto-decline old pending invitations when sending new one

---

### **8. Cross-User Privacy Leaks**

**The Problem:**
Invitation system may leak information:
- Leader learns if email exists in system (user_exists=true response)
- Invitation token in URL could be intercepted
- Group details visible before acceptance (in email)
- Leader can track when user opened email (if tracking pixels used)

**Why This Matters:**
- Privacy violation: Revealing user existence
- Security: Email enumeration attack vector
- Consent: User hasn't agreed to join but sees group details
- Abuse: Stalker could use invitations to track user activity

**Mitigation Strategies:**
- Don't reveal user existence in API response
- HTTPS-only invitation links
- Short-lived tokens (7 days)
- One-time-use tokens (invalidate after click)
- No tracking pixels in invitation emails
- Group details only shown after user clicks link
- Require authentication to see invitation details (for existing users)

---

### **9. Incomplete Registration Abandonment**

**The Problem:**
User journey has many exit points:
- Clicks invitation link, sees registration form, closes tab
- Starts filling form, gets distracted, never submits
- Submits form but never checks verification email
- Verifies email but never logs in to accept invitation

**Why This Matters:**
- High abandonment rate = wasted engineering effort
- Leader thinks user ignored them (hurts feelings)
- Pending accounts clutter database
- No clear recovery path if user wants to continue later

**Mitigation Strategies:**
- Save form progress (local storage)
- "Continue where you left off" link in reminder emails
- Simplified registration: Just name + password (other fields later)
- Magic link option: Skip password entirely for first login
- Show progress: "80% complete - Just verify your email!"
- Analytics: Track where users drop off to optimize flow

---

### **10. Mobile Email Client Issues**

**The Problem:**
Mobile users switching between email app and browser:
- Click link in Gmail app → Opens in-app browser → Can't save password
- Switch to Safari/Chrome → Lost invitation token/context
- Email app doesn't support HTML → Link not clickable
- Small screen makes multi-step flow harder to follow

**Why This Matters:**
- Over 60% of email opens are on mobile
- In-app browsers have limited functionality
- Users may not know how to "Open in Safari"
- Password managers don't work well in in-app browsers

**Mitigation Strategies:**
- Deep links: Auto-open your mobile app if installed
- "Open in browser" button prominently displayed
- SMS alternative: Send invitation link via text message
- QR code in email: Scan to open on phone directly
- Progressive Web App (PWA) for better mobile experience
- Test extensively on iOS/Android email clients

---

## Implementation Architecture

### **Core Components**

#### **1. GroupInvitation Model**

This is the central tracking system for invitations. Key considerations:

**Fields:**
- `group` and `email`: Who is invited where
- `invited_by`: Audit trail and attribution
- `status`: Lifecycle management (pending → accepted/declined/expired)
- `token`: Secure, unique, unpredictable identifier
- `expires_at`: Enforces invitation lifetime
- `personal_message`: Humanizes the invitation
- `invited_role`: Determines permissions after acceptance

**Database Indexes:**
- `(email, status)`: Fast lookup of user's pending invitations
- `(token)`: Quick validation of invitation links
- `(expires_at)`: Efficient cleanup queries

**Unique Constraint:**
- `(group, email, status='pending')`: Prevents duplicate active invitations
- Allows historical tracking (accepted/declined invitations remain in DB)

---

#### **2. Invitation Service Layer**

Business logic should live in a dedicated service, not in views:

**GroupInvitationService Responsibilities:**
- Validate email format and check for disposable domains
- Check rate limits before creating invitation
- Detect duplicate pending invitations
- Create or retrieve User record
- Generate secure token with sufficient entropy
- Create GroupMembership with pending status
- Coordinate email sending
- Handle transaction rollback if email fails

**Why Service Layer?**
- Reusable from management commands, Celery tasks, admin actions
- Easier to test (no HTTP request/response mocking)
- Clear separation of concerns
- Can be called from multiple endpoints (invite, reinvite, bulk invite)

---

#### **3. Email Templates Strategy**

Two distinct email types needed:

**For New Users:**
- Welcoming tone: "You've been invited to join Vineyard Group Fellowship"
- Explains what the platform is (they may not know)
- Clear call-to-action: "Create Your Account"
- Sets expectations: "This will take about 2 minutes"
- Shows group details to entice acceptance

**For Existing Users:**
- Familiar tone: "Hi [Name], you've been invited to join [Group]"
- Simpler flow: "Just click to accept"
- Shows their existing profile info
- One-click acceptance (already authenticated)

**Email Best Practices:**
- Plain text fallback for email clients that block HTML
- Mobile-responsive design (most opens are mobile)
- Clear sender name: "Vineyard Group Fellowship Invitations"
- Preheader text: First line should summarize action needed
- Unsubscribe link (even though it's transactional)
- Footer with support contact

---

#### **4. API Endpoints Design**

**POST /api/v1/groups/{id}/invite-member/**
- Permission: IsGroupLeader
- Rate limited: 10 requests per hour per user
- Validates email before creating invitation
- Returns invitation_id for tracking
- Idempotent: Resends if duplicate detected

**GET /api/v1/invitations/{token}/**
- Public endpoint (no authentication)
- Returns invitation details (group name, inviter name, expiry)
- Does not reveal if user already exists
- Rate limited to prevent token enumeration

**POST /api/v1/invitations/{token}/accept/**
- Requires authentication (user must be logged in)
- Validates token freshness and user email match
- Activates account and group membership atomically
- Triggers welcome email and onboarding flow

**GET /api/v1/groups/{id}/invitations/**
- Permission: IsGroupLeader
- Lists all invitations for this group
- Filterable by status (pending, accepted, expired)
- Shows acceptance rate metrics

---

### **Security Hardening**

#### **Token Generation**
- Use `secrets.token_urlsafe(32)` for 256-bit entropy
- Store tokens hashed (SHA-256) in database
- One-time use: Invalidate after acceptance
- Short lifetime: 7-14 days maximum
- Include timestamp in validation to prevent timing attacks

#### **Rate Limiting Strategy**
- Per-user: 10 invitations per day
- Per-IP: 50 invitation requests per hour
- Per-group: 50 pending invitations maximum
- Exponential backoff: Double delay after each violation

#### **Email Validation**
- Format validation: RFC 5322 compliant
- DNS MX record check: Does domain accept email?
- Disposable email blocklist: Block guerrillamail.com, etc.
- Previous bounce check: Has this email bounced before?

#### **Authorization Checks**
- Only group leaders can invite
- Co-leaders can invite if settings allow
- Members cannot invite (prevent spam)
- Revoked invitations cannot be re-accepted

---

## User Experience Flow

### **Leader's Perspective**

1. **Initiation**
   - Navigate to group page
   - Click "Invite Member" button
   - See modal/form with email input
   - Optionally add personal message
   - Select role (member or co-leader)

2. **Confirmation**
   - Preview: "Invitation will be sent to user@example.com"
   - Option to copy invitation link for manual sharing
   - Success message: "Invitation sent! They'll receive an email shortly."
   - Dashboard shows invitation status

3. **Tracking**
   - View list of pending invitations
   - See who accepted/declined
   - Resend expired invitations
   - Revoke invitations before acceptance

### **New User's Perspective**

1. **Email Receipt**
   - Receives invitation email from group leader
   - Email explains what Vineyard Group Fellowship is
   - Shows group details (name, description, meeting time)
   - Personal message from leader adds human touch
   - Clear "Accept Invitation" button

2. **Registration** (if new user)
   - Click link → Lands on registration page
   - Email is pre-filled (from invitation)
   - Only need to provide: Name, Password
   - Submit → Account created but inactive
   - Clear message: "Check your email to verify and join the group"

3. **Email Verification**
   - Receives second email with verification link
   - Click verification link → Account activated
   - Automatically redirects to group page
   - Membership changes from 'pending' to 'active'
   - Welcome message from group

4. **First Login Experience**
   - Sees group in "My Groups" list
   - Can access group content (messages, prayer requests, events)
   - Onboarding flow guides through platform features
   - Option to complete profile (optional fields)

### **Existing User's Perspective**

1. **Email Receipt**
   - Receives invitation email with familiar interface
   - "Hi [FirstName], you've been invited..."
   - Two buttons: "Accept" and "Decline"
   - Group details preview

2. **One-Click Acceptance**
   - Click "Accept" → Redirects to login page
   - Log in with existing credentials
   - Automatically added to group
   - Redirected to group page
   - No email verification needed (already verified)

---

## Technical Implementation Details

### **Database Model Structure**

The `GroupInvitation` model serves as the central tracking mechanism:

**Status Lifecycle:**
- `pending`: Invitation sent, awaiting user action
- `accepted`: User completed registration and verified email
- `declined`: User explicitly rejected invitation
- `expired`: Invitation passed expiry date without acceptance
- `revoked`: Leader cancelled invitation before acceptance

**Token Management:**
- Generated using `secrets.token_urlsafe(32)` for cryptographic security
- Provides 256 bits of entropy (extremely difficult to guess)
- Stored in database with unique constraint
- Used in invitation URL: `/invitations/{token}`
- Single-use: Invalidated after acceptance/decline
- Time-limited: 7-day expiry from creation

**Unique Constraint Rationale:**
- `(group, email, status='pending')` ensures only one active invitation per user per group
- Allows multiple historical records (accepted/declined) for analytics
- Prevents leader confusion ("Did I already invite them?")
- Handles race conditions (two leaders invite same person)

**Index Strategy:**
- `(email, status)`: Fast lookup when user checks their pending invitations
- `(token)`: Sub-millisecond validation of invitation links
- `(expires_at)`: Efficient batch expiry cleanup queries
- Consider adding `(group, status)` if showing group invitation lists becomes slow

---

### **Service Layer Responsibilities**

**GroupInvitationService.create_invitation():**

This method orchestrates the entire invitation creation process:

1. **Email Validation Phase:**
   - Format check using Django's EmailValidator
   - DNS MX record lookup (does domain accept mail?)
   - Disposable email detection (block 10minutemail.com, etc.)
   - Previous bounce history check (has this email failed before?)

2. **User Existence Check:**
   - Query User table by email
   - If exists: Retrieve existing user
   - If not: Create shadow account with `is_active=False`
   - Auto-generate username: `invited_` + 8-char random hex

3. **Duplicate Detection:**
   - Check for existing pending invitation (same group + email)
   - If found: Offer to resend (invalidate old token, create new)
   - Check for existing active membership (prevent redundant invites)
   - Check for previously declined invitation (respect user's choice)

4. **Rate Limit Enforcement:**
   - Count invitations sent by this leader today
   - If >= 10: Reject with "Daily invitation limit reached"
   - Per-group limit: Max 50 pending invitations
   - Per-IP limit: Prevent API abuse from single source

5. **Invitation Record Creation:**
   - Generate secure token
   - Calculate expiry (now + 7 days)
   - Store invitation with status='pending'
   - Create pending GroupMembership record
   - Both operations wrapped in database transaction

6. **Email Dispatch:**
   - Determine user type (new vs existing)
   - Select appropriate email template
   - Build invitation URL with token
   - Queue email for async sending (Celery)
   - Handle email failure gracefully (rollback DB transaction)

**Error Handling Strategy:**
- Wrap entire flow in try/except
- Rollback database transaction if email fails
- Log all errors with context (user, group, email)
- Return user-friendly error messages
- Don't reveal internal details to API consumers

---

### **Email Template Design Principles**

**Why Two Templates?**

New users and existing users have fundamentally different contexts:

**New User Considerations:**
- They don't know what Vineyard Group Fellowship is
- Need explanation of the platform's purpose
- Higher skepticism (is this spam?)
- Must complete registration + verification (multi-step)
- Should show social proof (how many groups, users)

**Existing User Considerations:**
- Already familiar with platform
- Just need to decide: Accept or decline?
- Can complete action in 1 click (already authenticated)
- Email should be brief and actionable
- Personal touch matters more than explanation

**Template Best Practices:**

1. **Subject Line:**
   - New users: "You're invited to join [Group] on Vineyard Group Fellowship"
   - Existing users: "[LeaderName] invited you to join [Group]"
   - Keep under 50 characters for mobile displays
   - Include group name for context

2. **Preheader Text:**
   - First 80-100 characters shown in inbox preview
   - New users: "Create your account and connect with [Group]"
   - Existing users: "Accept or decline this invitation"

3. **Email Body Structure:**
   - Greeting (personalized if existing user)
   - Context (who invited you, which group)
   - Personal message from leader (if provided)
   - Clear call-to-action button
   - Group details (name, description, meeting info)
   - Expiry notice ("This invitation expires in 7 days")
   - Decline/ignore option ("Not interested? Ignore this email")

4. **Mobile Optimization:**
   - Single-column layout
   - Buttons at least 44×44 pixels (Apple guideline)
   - Font size minimum 16px (prevents auto-zoom on iOS)
   - Test on Gmail app, Apple Mail, Outlook mobile

5. **Accessibility:**
   - Alt text for all images
   - Semantic HTML (proper heading hierarchy)
   - High contrast text (4.5:1 minimum)
   - Plain text fallback for accessibility tools

---

### **API Endpoint Implementation**

**POST /groups/{id}/invite-member/**

**Permission Logic:**
```python
# Only group leaders and co-leaders can invite
def has_permission(user, group):
    membership = GroupMembership.objects.filter(
        group=group,
        user=user,
        status='active',
        role__in=['leader', 'co_leader']
    ).exists()
    return membership
```

**Rate Limiting Strategy:**
- Use Django's cache framework with Redis backend
- Key: `invitation_rate_limit:user:{user_id}`
- Value: Count of invitations sent today
- TTL: Midnight UTC (resets daily)
- Check before creating invitation, increment after success

**Idempotency Handling:**
- If duplicate detected, return existing invitation
- Don't create new record unnecessarily
- Optionally update personal_message if different
- Return 200 (not 201) for duplicate requests
- Include "already_invited": true in response

**Response Status Codes:**
- 201: New invitation created successfully
- 200: Invitation already exists (resent)
- 400: Invalid email format or user already member
- 403: User lacks permission to invite
- 429: Rate limit exceeded
- 500: Email sending failed or database error

---

**GET /invitations/{token}/**

**Why Public Endpoint?**

This endpoint must work without authentication because:
- User may not have account yet (new users)
- User may not be logged in when clicking email link
- Mobile email apps don't send auth headers
- Simplifies frontend logic (no conditional auth)

**Security Concerns:**
- Token has 256 bits of entropy (brute-force infeasible)
- Short expiry (7 days) limits attack window
- One-time use (invalidated after acceptance)
- Rate limit to prevent enumeration (100 requests/hour per IP)
- Don't reveal whether user exists in system

**Response Contents:**
- Group name, description, meeting details
- Inviter's name (not email for privacy)
- Expiry timestamp
- Whether invitation is still valid
- Whether email matches existing account (user_exists: boolean)

**Error Responses:**
- 404: Token not found or already used
- 410: Invitation expired
- 429: Too many requests (rate limit)

---

**POST /invitations/{token}/accept/**

**Authentication Requirements:**
- New users: Must complete registration first, then call this endpoint
- Existing users: Must be logged in (Authorization header required)
- Email match validation: `user.email == invitation.email`
- Prevents invitation hijacking (user A can't accept user B's invite)

**Transactional Operations:**
All database changes must be atomic (wrapped in transaction):
1. Update invitation status to 'accepted'
2. Set invitation.accepted_at timestamp
3. Update GroupMembership status from 'pending' to 'active'
4. If new user: Set user.is_active=True
5. Trigger welcome email (async, non-blocking)
6. Log acceptance event for analytics

**Rollback Scenarios:**
- If any step fails, all changes are rolled back
- User sees generic error message
- Engineering team notified via logging/monitoring
- User can retry acceptance (invitation still pending)

**Post-Acceptance Actions:**
- Send welcome email with group guidelines
- Trigger onboarding flow (if configured)
- Create feed items for user (populate their feed)
- Notify group leader (optional): "User X accepted your invitation"
- Update group member count cache

---

### **Security Deep Dive**

**Token Generation & Storage:**

The token is the entire security perimeter for invitations:

**Generation:**
```python
import secrets
token = secrets.token_urlsafe(32)  # Returns 43-character string
```

**Why secrets.token_urlsafe()?**
- Uses os.urandom() (cryptographically secure)
- 32 bytes = 256 bits of entropy
- Base64-URL-safe encoding (no special chars in URLs)
- Suitable for security-sensitive applications

**Storage Consideration:**
- Store token directly in database (hashing not necessary here)
- Token is single-use (invalidated immediately after use)
- Short lifetime (7 days) limits exposure
- If ultra-paranoid: Hash token (SHA-256) and store hash only

**Token in URL:**
- Always HTTPS (never HTTP) to prevent interception
- No token in query params if possible (use path: `/invitations/{token}`)
- Query params logged by proxies/analytics tools
- Tokens in paths are safer

---

**Email Enumeration Protection:**

**The Attack:**
Attacker tries to discover which emails are registered:
1. Call `/groups/123/invite-member/` with email
2. Check response: Does it say "user already exists"?
3. Build list of all registered users

**Defense:**
- Never reveal user existence in API response
- Same message for existing and new users: "Invitation sent"
- Use generic `user_exists` boolean only for internal logging
- Don't expose different behavior (timing attacks)

---

**Rate Limiting Deep Dive:**

**Why Multiple Rate Limit Layers?**

1. **Per-User Limit (10/day):**
   - Prevents individual account abuse
   - Stops compromised accounts from spamming
   - Reasonable limit for legitimate group leaders
   - Daily reset at midnight UTC

2. **Per-IP Limit (50/hour):**
   - Prevents bot attacks
   - Catches distributed attacks from same network
   - Protects against account enumeration
   - Sliding window implementation

3. **Per-Group Limit (50 pending):**
   - Prevents mass invitation spam to single group
   - Keeps pending invitation list manageable
   - Limits database table growth
   - Cleared as invitations accepted/expired

**Implementation:**
- Use Redis for fast rate limit checks
- Cache keys: `invite_limit:user:{id}:daily`
- Atomic increment operations (INCR command)
- Set TTL to expire at midnight
- Check before processing, increment after success

---

**Spam & Abuse Prevention:**

Beyond rate limits, additional protections:

1. **Disposable Email Blocking:**
   - Maintain blocklist: guerrillamail.com, 10minutemail.com, etc.
   - Use third-party API (like kickbox.io) for real-time validation
   - Block invitations to disposable domains
   - Log attempts for pattern analysis

2. **Email Bounce Tracking:**
   - Monitor bounce notifications from email provider
   - Mark emails that hard-bounce (mailbox doesn't exist)
   - Prevent future invitations to bounced emails
   - Show warning to leader: "This email bounced previously"

3. **Invitation Pattern Analysis:**
   - Flag users who invite many addresses from same domain
   - Detect rapid-fire invitations (>5 in 1 minute)
   - Alert admins to suspicious behavior
   - Temporarily suspend invitation privileges

4. **CAPTCHA Implementation:**
   - After 5 invitations in 1 hour, require CAPTCHA
   - Prevents automated bot attacks
   - Use hCaptcha or reCAPTCHA v3
   - Invisible to legitimate users (low friction)

---

### **Cleanup & Maintenance**

**Automated Expiry Job:**

Why cleanup is critical:
- Prevents database bloat (thousands of expired invitations)
- Frees up email uniqueness constraint (re-invite previously expired)
- Maintains accurate pending invitation counts
- Improves query performance (fewer rows to scan)

**Management Command:**
```bash
python manage.py expire_invitations
```

**What it does:**
1. Query all invitations with status='pending' and expires_at < now
2. Update status to 'expired' (don't delete for analytics)
3. Update related GroupMembership records to 'inactive'
4. Optionally send "invitation expired" email to inviter
5. Log expiry metrics for monitoring

**Run frequency:**
- Daily via cron job or Celery beat
- Run at low-traffic time (3 AM server time)
- Batch update (1000 records at a time)
- Monitor execution time

---

**Shadow Account Cleanup:**

Pending accounts (never verified) pollute database:

**Management Command:**
```bash
python manage.py cleanup_shadow_accounts
```

**Criteria for deletion:**
- `is_active=False`
- `email_verified=False`
- `created_at` older than 30 days
- No accepted invitations
- No login history

**What it does:**
1. Query inactive accounts older than 30 days
2. Check for any group memberships (even expired)
3. If truly orphaned, soft delete or hard delete
4. Log deletion for audit trail
5. Send weekly summary to admins

**Considerations:**
- Keep accepted invitations' user accounts (even if inactive)
- Don't delete accounts with any activity (logins, posts)
- Soft delete first (archive), hard delete after 90 days
- GDPR compliance: User data must be deletable

---

## Implementation Roadmap

### **Phase 1: Foundation (Days 1-3)**

**Day 1: Database Layer**
- Create GroupInvitation model in `group/models.py`
- Define all fields, indexes, constraints
- Write migration file
- Run migration in local Docker environment
- Test in Django shell (create/query invitations)
- Estimated time: 3-4 hours

**Day 2: Service Layer**
- Create `group/services/invitation_service.py`
- Implement `create_invitation()` method
- Implement `accept_invitation()` method
- Add email validation logic
- Add duplicate detection
- Write unit tests for service layer
- Estimated time: 4-5 hours

**Day 3: Email Templates**
- Design HTML templates for new users
- Design HTML templates for existing users
- Create plain text fallbacks
- Add Django template logic (variables, conditionals)
- Test rendering with sample data
- Test with MailHog locally
- Estimated time: 3-4 hours

**Phase 1 Total: 10-13 hours**

---

### **Phase 2: API Layer (Days 4-6)**

**Day 4: Invitation Endpoints**
- Add `invite_member` action to `GroupViewSet`
- Implement permission checks (IsGroupLeader)
- Add input validation (serializer)
- Integrate with `GroupInvitationService`
- Write API tests (success and error cases)
- Estimated time: 4-5 hours

**Day 5: Acceptance Endpoints**
- Create `InvitationViewSet`
- Implement `get_invitation_details` (public)
- Implement `accept_invitation` (authenticated)
- Implement `decline_invitation` (public)
- Add token validation logic
- Write API tests
- Estimated time: 4-5 hours

**Day 6: Additional Endpoints**
- Implement `list_invitations` (for leaders)
- Implement `revoke_invitation` (for leaders)
- Add filtering (by status)
- Add pagination
- Update OpenAPI schema
- Write integration tests
- Estimated time: 3-4 hours

**Phase 2 Total: 11-14 hours**

---

### **Phase 3: Security & Polish (Days 7-9)**

**Day 7: Rate Limiting**
- Implement per-user rate limiting (Redis)
- Implement per-IP rate limiting
- Implement per-group limits
- Add CAPTCHA integration (optional)
- Test rate limit enforcement
- Estimated time: 3-4 hours

**Day 8: Email Validation**
- Integrate disposable email blocklist
- Add DNS MX record validation
- Implement bounce tracking
- Add email format validation
- Test with various email formats
- Estimated time: 2-3 hours

**Day 9: Cleanup Jobs**
- Create `expire_invitations` management command
- Create `cleanup_shadow_accounts` command
- Test commands with sample data
- Set up Celery beat schedule (if using Celery)
- Document cron job setup
- Estimated time: 2-3 hours

**Phase 3 Total: 7-10 hours**

---

### **Phase 4: Testing & Deployment (Days 10-12)**

**Day 10: Comprehensive Testing**
- End-to-end test: New user flow
- End-to-end test: Existing user flow
- Test expiry scenarios
- Test error handling (email fails, DB errors)
- Load testing (concurrent invitations)
- Security testing (token guessing, SQL injection)
- Estimated time: 4-5 hours

**Day 11: Documentation**
- Write API documentation (request/response examples)
- Create frontend integration guide
- Document rate limits and quotas
- Write deployment guide
- Create admin usage guide
- Estimated time: 3-4 hours

**Day 12: Deployment**
- Merge feature branch to main
- Run migrations on staging
- Test on staging environment
- Verify email sending (real emails)
- Deploy to production
- Monitor error rates
- Estimated time: 2-3 hours

**Phase 4 Total: 9-12 hours**

---

### **Total Implementation Time: 37-49 hours**

**Breakdown:**
- Phase 1 (Foundation): 10-13 hours
- Phase 2 (API Layer): 11-14 hours
- Phase 3 (Security & Polish): 7-10 hours
- Phase 4 (Testing & Deployment): 9-12 hours

**Timeline:**
- **Full-time (8 hrs/day):** 5-6 working days
- **Part-time (4 hrs/day):** 10-12 working days
- **Spare time (2 hrs/day):** 19-25 days

---

### **MVP Implementation (Reduced Scope)**

If you need faster delivery, here's a minimal viable product:

**MVP Scope:**
- GroupInvitation model (basic fields only)
- Simple `create_invitation()` service method
- Single email template (works for both new/existing users)
- Basic `invite_member` endpoint (no rate limiting)
- Basic `accept_invitation` endpoint
- Manual invitation expiry (no automated cleanup)

**Excluded from MVP:**
- Decline functionality
- Revoke functionality
- Advanced rate limiting
- Disposable email blocking
- Bounce tracking
- Analytics dashboard
- Reminder emails
- Invitation resending

**MVP Timeline: 12-15 hours** (3-4 days part-time)

---

## Monitoring & Success Metrics

### **Key Metrics to Track**

**Invitation Funnel:**
1. Invitations sent (total, per day, per leader)
2. Emails delivered (bounce rate)
3. Invitation links clicked (email open rate)
4. Registration started (for new users)
5. Registration completed
6. Email verification completed
7. Invitation accepted
8. First group interaction (message/prayer request)

**Conversion Rates:**
- Invite → Click: Target 60-70%
- Click → Register: Target 40-50%
- Register → Verify: Target 70-80%
- Verify → Accept: Target 90-95%
- Overall: Invite → Active Member: Target 25-35%

**Time Metrics:**
- Time from invitation to acceptance (median, p50, p95)
- Time from registration to verification
- Time from acceptance to first group interaction
- Identify drop-off points (longest delays)

**Leader Engagement:**
- % of leaders who have sent invitations
- Average invitations per leader
- Leaders with highest acceptance rates
- Groups growing fastest via invitations

**Health Metrics:**
- Invitation expiry rate (target: <20%)
- Decline rate (target: <10%)
- Bounce rate (target: <5%)
- Rate limit violations (should be rare)
- Duplicate invitation attempts

---

## Conclusion & Recommendations

### **✅ Feasibility Assessment: HIGHLY FEASIBLE**

Your application has excellent foundations for this feature:
- **Existing User Model:** Email-based auth, inactive account support, verification system
- **Group Infrastructure:** Membership tracking with status field (pending/active)
- **Email System:** Async sending, template support, verification flows
- **Database Design:** UUID primary keys, well-indexed, scalable

**No major architectural changes needed.** This feature fits naturally into your existing patterns.

---

### **🎯 Recommended Approach Summary**

**Invite with Pending Account** is the best strategy because:

1. **Security:** Accounts remain inactive until user explicitly accepts
2. **Privacy:** GDPR-compliant (requires user consent before activation)
3. **User Experience:** Clear, guided flow with progress indicators
4. **Trackability:** Leaders can see invitation status and acceptance rates
5. **Spam Prevention:** Inactive accounts don't clutter user metrics
6. **Audit Trail:** Complete history of who invited whom and when
7. **Leverages Existing Code:** Uses your email verification system
8. **Database Hygiene:** Automated cleanup of expired invitations

---

### **⚠️ Critical Downsides to Address**

1. **Multi-Step Friction:** 7-step process for new users (high drop-off risk)
   - **Mitigation:** Combine invitation + verification into single flow
   
2. **Email Deliverability:** Entire feature depends on email reaching inbox
   - **Mitigation:** SPF/DKIM/DMARC setup, monitor bounce rates
   
3. **Shadow Account Pollution:** Uninvited users create database clutter
   - **Mitigation:** Automated cleanup after 30 days
   
4. **Invitation Expiry:** Users may miss 7-day window
   - **Mitigation:** Longer window (14 days), reminder emails, grace period
   
5. **Username Generation:** Auto-generated usernames may look ugly
   - **Mitigation:** Generate from email, allow customization during onboarding
   
6. **Spam Potential:** Bad actors could abuse invitation system
   - **Mitigation:** Multi-layer rate limiting, CAPTCHA, pattern detection
   
7. **Mobile UX:** Email-to-browser flow is clunky on mobile
   - **Mitigation:** Deep links, PWA support, SMS alternative
   
8. **Duplicate Confusion:** Same user invited multiple times
   - **Mitigation:** Duplicate detection, auto-resend logic
   
9. **Privacy Leaks:** Invitation system could reveal user existence
   - **Mitigation:** Don't expose user_exists in API responses
   
10. **Registration Abandonment:** Users start but don't finish flow
    - **Mitigation:** Save progress, send reminders, simplified registration

---

### **📅 Recommended Timeline**

**For Full Implementation (37-49 hours):**
- **Week 1:** Database models, service layer, email templates (10-13 hrs)
- **Week 2:** API endpoints, permissions, validation (11-14 hrs)
- **Week 3:** Security hardening, rate limiting, cleanup jobs (7-10 hrs)
- **Week 4:** Testing, documentation, deployment (9-12 hrs)

**For MVP (12-15 hours):**
- **Weekend 1:** Models, basic service, single template (6-7 hrs)
- **Weekend 2:** Basic endpoints, testing, deployment (6-8 hrs)
- **Follow-up:** Add advanced features incrementally

---

### **🚀 Next Steps**

1. **Decision Point:** MVP vs Full Implementation?
   - MVP if you need this feature ASAP (2 weekends)
   - Full if you want production-ready, scalable solution (4 weeks)

2. **Create Feature Branch:**
   ```bash
   git checkout -b feature/group-leader-invitations
   ```

3. **Start with Database:**
   - Create GroupInvitation model
   - Run migration
   - Test in Django shell

4. **Build Service Layer:**
   - Implement create_invitation()
   - Add validation and error handling
   - Write unit tests

5. **Create Email Templates:**
   - Design HTML templates
   - Test with MailHog locally
   - Iterate on copy and design

6. **Build API Endpoints:**
   - Start with invite_member
   - Add acceptance flow
   - Test end-to-end

7. **Add Security:**
   - Implement rate limiting
   - Add spam prevention
   - Security audit

8. **Test & Deploy:**
   - Comprehensive testing
   - Deploy to staging
   - Monitor and iterate

---

### **💡 Alternative Considerations**

**If time is extremely limited, consider:**

1. **Django Packages:**
   - `django-invitations`: Pre-built invitation system
   - Pros: Faster implementation, maintained by community
   - Cons: Less customization, may not fit your UX exactly

2. **Third-Party Services:**
   - SendGrid invitation templates
   - Auth0 invitation system
   - Pros: Managed infrastructure, analytics included
   - Cons: Additional cost, vendor lock-in

3. **Simplified Flow:**
   - Skip pending accounts entirely
   - Just send invitation link to registration page
   - Pre-fill email, auto-join group after registration
   - Pros: Simpler, fewer steps
   - Cons: No tracking, less control

**Recommendation:** Build it yourself. Your architecture is ready, and you'll have full control over UX, security, and scalability. The 37-49 hour investment will pay off with a feature tailored exactly to your needs.

---

**Ready to proceed? Let me know if you'd like to start implementation or need clarification on any aspect of this design.** 🎉
