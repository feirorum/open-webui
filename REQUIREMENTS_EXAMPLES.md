# Requirements Examples

Example requirements demonstrating different types, formats, and best practices for the Requirements Agent system.

## Example 1: Functional Requirement with Gherkin Scenarios

```markdown
---
id: REQ-001
title: User can log in with email and password
status: accepted
type: functional
priority: high
area: authentication
created_at: 2025-11-18T10:00:00Z
updated_at: 2025-11-18T14:30:00Z
source_conversations:
  - convo_id: chat-2025-11-18-auth-session
    message_ids: ["msg_42", "msg_45", "msg_48"]
examples:
  - id: EX-001
    description: Successful login with valid credentials
    status: approved
  - id: EX-002
    description: Failed login with incorrect password
    status: approved
  - id: EX-003
    description: Account lockout after multiple failures
    status: approved
---

## Summary

As a registered user, I want to log in with my email and password so that I can securely access my account and personalized content.

## Details

**Authentication Method**: Email + Password

**Security Requirements**:
- Passwords must be at least 10 characters long
- Account locks after 5 consecutive failed login attempts
- Lockout duration: 15 minutes
- Failed attempts counter resets after successful login

**UX Requirements**:
- Show/hide password toggle
- "Remember me" checkbox (optional, 30-day session)
- Clear error messages without revealing whether email exists

**Technical Constraints**:
- Use bcrypt for password hashing (minimum 12 rounds)
- Store last login timestamp
- Log all login attempts (successful and failed) for security audit

## Examples (Spec-by-Example / BDD)

### EX-001: Successful login with valid credentials

```gherkin
Scenario: User logs in successfully with correct credentials
  Given a registered user with email "alice@example.com"
  And the user has a valid password "SecureP@ss123"
  And the account is not locked
  When the user navigates to the login page
  And enters email "alice@example.com"
  And enters password "SecureP@ss123"
  And clicks the "Log In" button
  Then the user should be redirected to the dashboard at "/dashboard"
  And the session cookie should be set with appropriate expiration
  And the last_login timestamp should be updated in the database
  And the failed_attempts counter should be reset to 0
```

### EX-002: Failed login with incorrect password

```gherkin
Scenario: User fails to log in with incorrect password
  Given a registered user with email "alice@example.com"
  And the user has failed 2 previous login attempts
  When the user navigates to the login page
  And enters email "alice@example.com"
  And enters incorrect password "WrongPassword"
  And clicks the "Log In" button
  Then the user should remain on the login page
  And see an error message "Invalid email or password"
  And the failed_attempts counter should increment to 3
  And no session cookie should be set
  And the failed attempt should be logged with timestamp and IP
```

### EX-003: Account lockout after multiple failures

```gherkin
Scenario: Account is locked after 5 consecutive failed attempts
  Given a registered user with email "alice@example.com"
  And the user has failed 4 previous login attempts
  When the user enters email "alice@example.com"
  And enters incorrect password "WrongPassword"
  And clicks the "Log In" button
  Then the user should see error message "Account locked due to multiple failed attempts. Try again in 15 minutes."
  And the account should be locked until [current_time + 15 minutes]
  And an account_locked event should be logged
  And a security notification email should be sent to "alice@example.com"

Scenario: Locked account cannot log in even with correct password
  Given a user account with email "alice@example.com" is currently locked
  And the lockout period has not expired
  When the user enters correct credentials
  And clicks the "Log In" button
  Then the user should see error message "Account locked. Try again in X minutes."
  And the login should be denied
  And the failed_attempts counter should NOT increment
```
\`\`\`

---

## Example 2: Non-Functional Requirement (Performance)

```markdown
---
id: REQ-015
title: Search results must load within 2 seconds
status: accepted
type: non-functional
priority: critical
area: search
created_at: 2025-11-18T11:00:00Z
updated_at: 2025-11-18T11:00:00Z
source_conversations:
  - convo_id: chat-2025-11-18-performance
    message_ids: ["msg_103"]
examples:
  - id: EX-015-1
    description: Typical search query performance
    status: draft
  - id: EX-015-2
    description: Complex search with filters performance
    status: draft
---

## Summary

As a user searching for content, I expect search results to load within 2 seconds so that I can quickly find information without frustration.

## Details

**Performance Target**: 95th percentile response time ≤ 2 seconds

**Measurement Conditions**:
- Database contains up to 1 million indexed documents
- Average query: 2-5 keywords
- User located within same geographic region as server
- Normal system load (not during peak traffic)

**Constraints**:
- Measured from user clicking "Search" to results rendered in DOM
- Includes network latency + backend processing + frontend rendering
- Applies to both desktop and mobile web

**Acceptance Criteria**:
- P50 (median): ≤ 1 second
- P95: ≤ 2 seconds
- P99: ≤ 3 seconds
- Timeout error if > 5 seconds

**Technical Notes**:
- Use Elasticsearch or similar for full-text search
- Implement result caching for common queries (5-minute TTL)
- Lazy-load images and metadata
- Paginate results (20 per page)

## Examples (Spec-by-Example / BDD)

### EX-015-1: Typical search query performance

```gherkin
Scenario: User performs a simple keyword search
  Given the search index contains 500,000 documents
  And the user is on the search page
  And server response time is being measured
  When the user types "project management tools" in the search box
  And clicks the "Search" button
  Then the search results page should load within 2 seconds
  And display at least 20 relevant results
  And show the total result count
  And the P95 response time should be ≤ 2 seconds over 1000 test runs
```

### EX-015-2: Complex search with filters performance

```gherkin
Scenario: User performs a filtered search with multiple criteria
  Given the search index contains 1,000,000 documents
  And the user applies filters:
    | Filter Type | Value          |
    | category    | Technology     |
    | date_range  | Last 30 days   |
    | author      | John Doe       |
  When the user submits the filtered search query
  Then the filtered results should load within 2 seconds
  And display results matching all filter criteria
  And show filter application indicators
  And the response time should meet the 2-second P95 target
```
\`\`\`

---

## Example 3: Constraint Requirement

```markdown
---
id: REQ-027
title: System must comply with GDPR data protection requirements
status: accepted
type: constraint
priority: critical
area: compliance
created_at: 2025-11-18T12:00:00Z
updated_at: 2025-11-18T12:00:00Z
source_conversations:
  - convo_id: chat-2025-11-18-compliance
    message_ids: ["msg_78", "msg_82"]
examples:
  - id: EX-027-1
    description: User requests data export
    status: approved
  - id: EX-027-2
    description: User requests account deletion
    status: approved
---

## Summary

As a system operating in the EU, we must comply with GDPR (General Data Protection Regulation) to protect user privacy and avoid legal penalties.

## Details

**Scope**: All user personal data collected, processed, and stored by the system

**Key GDPR Requirements**:

1. **Right to Access** (Art. 15)
   - Users can request a copy of their personal data
   - Must provide data in machine-readable format (JSON/CSV)
   - Response within 30 days

2. **Right to Erasure** (Art. 17 - "Right to be Forgotten")
   - Users can request account deletion
   - Must delete all personal data within 30 days
   - Exceptions: legal obligations, archival purposes

3. **Right to Data Portability** (Art. 20)
   - Users can export their data
   - Must be in common, machine-readable format

4. **Consent Management** (Art. 7)
   - Explicit opt-in consent for data processing
   - Easy withdrawal of consent
   - Record consent timestamps and purposes

5. **Data Breach Notification** (Art. 33-34)
   - Notify authorities within 72 hours of breach
   - Notify affected users if high risk

**Personal Data Covered**:
- Email address
- Name
- Profile information
- IP addresses and logs
- User-generated content
- Usage analytics

**Technical Implementation**:
- Data encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Access logging and audit trails
- Data retention policies (auto-delete after 3 years of inactivity)
- Pseudonymization where possible

## Examples (Spec-by-Example / BDD)

### EX-027-1: User requests data export

```gherkin
Scenario: User requests full personal data export
  Given a logged-in user with email "user@example.com"
  And the user has been active for 2 years
  And the user has created 50 documents and 200 comments
  When the user navigates to Settings → Privacy → "Download My Data"
  And clicks "Request Data Export"
  Then the system should generate a data export package
  And send an email to "user@example.com" within 24 hours
  And the email should contain a secure download link valid for 7 days
  And the export should be in JSON format
  And include all personal data:
    | Data Type           |
    | Account information |
    | Profile details     |
    | Documents created   |
    | Comments posted     |
    | Activity logs       |
  And the export should be completed within 30 days
```

### EX-027-2: User requests account deletion

```gherkin
Scenario: User requests complete account deletion
  Given a logged-in user with email "user@example.com"
  When the user navigates to Settings → Privacy → "Delete Account"
  And clicks "Request Account Deletion"
  And confirms by entering their password
  And checks the confirmation box "I understand this is permanent"
  Then the system should display a confirmation message
  And send a confirmation email to "user@example.com"
  And schedule the account for deletion within 30 days
  And delete all personal data:
    | Data Type                    |
    | User account record          |
    | Email and profile info       |
    | User-generated content       |
    | Session tokens               |
    | IP addresses and access logs |
  And anonymize any data required for legal compliance
  And send a final "Account Deleted" email confirmation

Scenario: Deleted account cannot be recovered
  Given a user account was deleted 7 days ago
  When the user attempts to log in with the old email
  Then the login should fail
  And display message "No account found with this email"
  And the user data should not be recoverable
```
\`\`\`

---

## Example 4: User Story with Acceptance Criteria

```markdown
---
id: REQ-042
title: Admin can export user activity reports
status: proposed
type: functional
priority: medium
area: admin-tools
created_at: 2025-11-18T13:00:00Z
updated_at: 2025-11-18T13:00:00Z
source_conversations:
  - convo_id: chat-2025-11-18-admin-features
    message_ids: ["msg_156"]
examples: []
---

## Summary

As a system administrator, I want to export user activity reports in CSV format so that I can analyze usage patterns and generate compliance reports.

## Details

**User Role**: Admin with "reports" permission

**Report Types**:
1. User login history
2. Document access logs
3. Feature usage statistics
4. API call logs

**Export Format**: CSV (comma-separated values)

**Filtering Options**:
- Date range (required)
- Specific user(s) (optional)
- Activity type (optional)
- Department/team (optional)

**Acceptance Criteria**:
- [ ] Admin can access Reports page from admin dashboard
- [ ] Admin can select report type from dropdown
- [ ] Admin can specify date range using date picker
- [ ] Admin can optionally filter by user/activity/team
- [ ] Report generation starts within 1 second of clicking "Generate"
- [ ] Large reports (>10,000 rows) are processed asynchronously
- [ ] Admin receives email notification when async report is ready
- [ ] CSV file includes header row with column names
- [ ] CSV file is downloadable via secure link (expires in 24 hours)
- [ ] Export action is logged in admin audit trail

**Technical Notes**:
- Max report size: 100,000 rows (paginate if larger)
- CSV encoding: UTF-8 with BOM
- Date format: ISO 8601 (YYYY-MM-DD HH:MM:SS)
- Sanitize data to prevent CSV injection

## Examples (Spec-by-Example / BDD)

_No examples defined yet. Examples should demonstrate:_
- Generating a small report synchronously
- Generating a large report asynchronously with email notification
- Filtering reports by various criteria
- Error handling for invalid date ranges

---

## Example 5: Non-Functional Requirement (Security)

```markdown
---
id: REQ-051
title: API endpoints must implement rate limiting
status: accepted
type: non-functional
priority: high
area: api-security
created_at: 2025-11-18T14:00:00Z
updated_at: 2025-11-18T14:00:00Z
source_conversations:
  - convo_id: chat-2025-11-18-security
    message_ids: ["msg_201", "msg_203"]
examples:
  - id: EX-051-1
    description: Rate limit enforced on API calls
    status: approved
---

## Summary

As a system architect, I want all public API endpoints to implement rate limiting so that we prevent abuse, DoS attacks, and ensure fair resource allocation.

## Details

**Rate Limits by User Type**:

| User Type        | Rate Limit                | Window  |
|------------------|---------------------------|---------|
| Anonymous        | 100 requests              | 1 hour  |
| Authenticated    | 1000 requests             | 1 hour  |
| Premium          | 5000 requests             | 1 hour  |
| API Partner      | 10,000 requests           | 1 hour  |

**Endpoints Covered**: All `/api/*` routes

**Rate Limiting Strategy**:
- Use sliding window algorithm
- Track by IP address (anonymous) or API key/user ID (authenticated)
- Return HTTP 429 (Too Many Requests) when limit exceeded
- Include rate limit headers in all API responses:
  - `X-RateLimit-Limit` (max requests allowed)
  - `X-RateLimit-Remaining` (requests left in window)
  - `X-RateLimit-Reset` (timestamp when limit resets)

**Exemptions**:
- Internal service-to-service calls (localhost)
- Health check endpoints (`/health`, `/ping`)
- Admin users (configurable exemption)

**Error Response Format**:
```json
{
  "error": "Rate limit exceeded",
  "message": "You have exceeded the rate limit. Try again in 45 minutes.",
  "retry_after": 2700,
  "limit": 1000,
  "window": "1 hour"
}
```

## Examples (Spec-by-Example / BDD)

### EX-051-1: Rate limit enforced on API calls

```gherkin
Scenario: Authenticated user hits rate limit
  Given an authenticated user with API key "abc123"
  And the rate limit is 1000 requests per hour
  And the user has made 999 API calls in the current hour
  When the user makes their 1000th API call to "/api/search"
  Then the response should have status code 200
  And the response should include header "X-RateLimit-Remaining: 0"
  When the user makes their 1001st API call to "/api/search"
  Then the response should have status code 429
  And the response body should contain "Rate limit exceeded"
  And the response should include header "X-RateLimit-Reset" with future timestamp
  And the response should include "Retry-After" header in seconds

Scenario: Rate limit resets after time window
  Given an authenticated user who hit the rate limit at 14:00
  And the rate limit window is 1 hour
  When the user makes an API call at 15:01 (after reset)
  Then the request should succeed with status code 200
  And the rate limit counter should be reset to 1
  And the header "X-RateLimit-Remaining" should be 999
```
\`\`\`

---

## Best Practices Demonstrated

### ✅ Good Requirement Characteristics (from examples above)

1. **Clear User Value**: Each requirement explains WHO benefits and WHY
2. **Specific & Measurable**: "2 seconds" not "fast", "1000 requests/hour" not "reasonable limit"
3. **Testable**: Gherkin scenarios show exactly how to verify the requirement
4. **Independent**: Each requirement can be understood and implemented standalone
5. **Traceable**: Source conversations tracked in frontmatter
6. **Versioned**: Created/updated timestamps

### ✅ Gherkin Scenario Best Practices

1. **Use Concrete Data**: "alice@example.com" not "a user", "2 seconds" not "quickly"
2. **Focus on Behavior**: User actions and system responses, not implementation
3. **Cover Edge Cases**: Success path + error scenarios
4. **One Scenario = One Behavior**: Don't bundle multiple features
5. **Readable by Non-Technical Stakeholders**: Business language, not code

### ✅ Requirement Organization

1. **Meaningful Areas**: authentication, search, compliance, admin-tools (not "module1", "misc")
2. **Realistic Priorities**: Not everything is "critical"
3. **Appropriate Types**: functional vs non-functional vs constraints
4. **Status Progression**: proposed → accepted → implemented
5. **Examples Included**: Even non-functional requirements benefit from concrete scenarios

---

## Anti-Patterns to Avoid

### ❌ Vague Requirements

**Bad**: "The system should be fast."

**Good**: "Search results must load in < 2 seconds (P95) for queries on datasets up to 1M documents."

### ❌ Implementation Details in Requirements

**Bad**: "Use React hooks to manage login state."

**Good**: "User session should persist across page refreshes if 'Remember me' is checked."

### ❌ Multiple Concerns in One Requirement

**Bad**: "User can log in, reset password, and enable 2FA."

**Good**: Split into REQ-001 (login), REQ-002 (reset), REQ-003 (2FA)

### ❌ No Acceptance Criteria

**Bad**: Just a summary with no way to verify completion.

**Good**: Include Gherkin scenarios or explicit acceptance criteria checklist.

### ❌ Missing Context

**Bad**: "Implement caching."

**Good**: "Cache search results for 5 minutes to meet 2-second response time requirement (REQ-015)."

---

## Using These Examples

1. **Copy as Templates**: Use these as starting points for your own requirements
2. **Adapt to Your Domain**: Change areas, priorities, and specifics to match your project
3. **Maintain Consistency**: Follow the same format across all requirements in your project
4. **Evolve Over Time**: Update examples as you learn what works best for your team

Happy requirements writing! 🎯
