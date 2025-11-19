# Requirements Agent - Quick Start Guide

Get started with the Requirements Agent in **5 minutes**! 🚀

## Prerequisites

- Open WebUI installed and running
- Admin access to install tools and functions

## Step-by-Step Setup

### 1. Install the Requirements Toolkit (2 minutes)

1. **Open Open WebUI** in your browser
2. Navigate to **Workspace** → **Tools**
3. Click **"+ Create New Tool"**
4. **Copy the entire contents** of `requirements_toolkit.py`
5. **Paste** into the tool editor
6. Click **"Save"**

✅ You should see: "Requirements Management Toolkit" in your tools list

**Note**: The toolkit will automatically create the folder structure at `backend/data/requirements/` on first use.

### 2. Install Dependencies (1 minute)

The toolkit requires two Python packages. They're specified in the tool's frontmatter, so Open WebUI will auto-install them, but you can also install manually:

```bash
# If running Open WebUI locally
cd backend
source venv/bin/activate  # or your virtualenv
pip install pyyaml python-slugify
```

### 3. Install the Requirements Agent Filter (2 minutes)

1. Navigate to **Admin Panel** → **Functions**
2. Click **"+ Create New Function"**
3. Select type: **"Filter"**
4. **Copy the entire contents** of `requirements_agent_filter.py`
5. **Paste** into the function editor
6. In the **Valves** section, set:
   - `agent_mode`: `"assistant"` (or `"analyst"` for more proactive behavior)
   - `enable_auto_extraction`: `true`
   - `require_confirmation`: `true`
7. Click **"Save"**
8. **Toggle the filter to "Enabled"** (globally or per-model)

✅ You should see: "Requirements Agent Filter" active in your functions list

### 4. Start Your First Requirements Session (30 seconds)

1. **Start a new chat**
2. Click the **Tools icon** (🔧)
3. **Enable** "Requirements Management Toolkit"
4. Start talking about your project!

---

## Your First Requirements Extraction

Let's capture your first requirement in a conversational way.

### Example Session

**You**:
```
Let's talk about user authentication for my SaaS application.
Users should be able to sign up with their email and create a password.
```

**Requirements Agent**:
```
Great! I'd be happy to help you capture requirements for user authentication.

I'm hearing a functional requirement about user registration. Let me clarify a few details:

1. Email verification - should users verify their email before accessing the account?
2. Password requirements - any minimum length, complexity rules?
3. What happens after successful signup - automatic login or redirect to login page?
```

**You**:
```
Yes, email verification required before login.
Password must be at least 8 characters.
After signup, send verification email, then show "Check your email" message.
```

**Requirements Agent**:
```
Perfect! Here's what I've captured:

**Title**: User registration with email and password
**Area**: authentication
**Type**: functional
**Priority**: high

**Summary**: As a new user, I want to sign up with my email and password so that I can create an account and access the application.

**Details**:
- Email verification required before first login
- Password minimum length: 8 characters
- After signup: Send verification email to user
- Show "Check your email" confirmation message
- User cannot log in until email is verified

**Would you like me to add any Gherkin scenarios (Given-When-Then examples) for this requirement?**
```

**You**:
```
Yes, add a scenario for successful signup and one for email verification.
```

**Requirements Agent**:
```
Excellent! I'll create two scenarios:

**Scenario 1: Successful user signup**
```gherkin
Given a new user visits the signup page
When they enter email "user@example.com"
And enter password "SecurePass123"
And click "Sign Up"
Then a verification email should be sent to "user@example.com"
And they should see message "Check your email to verify your account"
And their account status should be "pending_verification"
```

**Scenario 2: Email verification**
```gherkin
Given a user with pending email verification
When they click the verification link in their email
Then their account status should change to "active"
And they should be redirected to the login page
And see message "Email verified! You can now log in."
```

**Shall I store this requirement now?**
```

**You**:
```
Yes, store it!
```

**Requirements Agent**:
```
✅ Requirement stored successfully!

**ID**: REQ-001
**Title**: User registration with email and password
**File**: backlog/REQ-001-user-registration-email-password.md
**Status**: proposed

The requirement has been saved to your requirements database.
You can view it at: `backend/data/requirements/backlog/REQ-001-user-registration-email-password.md`

Would you like to continue discussing more authentication requirements, or move to a different area?
```

---

## Common Commands

Once your requirements are stored, you can query and manage them:

### View All Requirements

**You**:
```
Show me all requirements
```

**Agent** (uses `requirements_overview`):
```
Here are all your requirements:

| ID      | Title                                   | Status   | Priority | Area           |
|---------|-----------------------------------------|----------|----------|----------------|
| REQ-001 | User registration with email/password   | proposed | high     | authentication |
| REQ-002 | Password reset flow                     | proposed | medium   | authentication |
| REQ-003 | User profile management                 | proposed | low      | user-profile   |

Total: 3 requirements
```

### Filter Requirements by Area

**You**:
```
Show me authentication requirements only
```

**Agent** (uses `requirements_overview` with filter):
```
Authentication Requirements (2):

| ID      | Title                                   | Status   | Priority |
|---------|-----------------------------------------|----------|----------|
| REQ-001 | User registration with email/password   | proposed | high     |
| REQ-002 | Password reset flow                     | proposed | medium   |
```

### Get Specific Requirement Details

**You**:
```
Show me REQ-001 in detail
```

**Agent** (uses `requirements_get`):
```
**REQ-001: User registration with email and password**

Status: proposed
Priority: high
Area: authentication
Created: 2025-11-18T10:30:00Z

**Summary**:
As a new user, I want to sign up with my email and password so that I can create an account and access the application.

**Details**:
- Email verification required before first login
- Password minimum length: 8 characters
- After signup: Send verification email
- Show "Check your email" confirmation message
- User cannot log in until email is verified

**Examples**:
[Shows Gherkin scenarios...]

File: backlog/REQ-001-user-registration-email-password.md
```

### Search Requirements

**You**:
```
Find requirements about passwords
```

**Agent** (uses `requirements_search`):
```
Found 2 requirements matching "passwords":

1. **REQ-001**: User registration with email and password (authentication, high priority)
2. **REQ-002**: Password reset flow (authentication, medium priority)
```

### Update Requirement Status

**You**:
```
Change REQ-001 status to accepted
```

**Agent** (uses `requirements_store` to update):
```
✅ Updated REQ-001:
- Status changed: proposed → accepted
- File moved: backlog/ → decided/REQ-001-user-registration-email-password.md

The requirement is now approved and ready for implementation.
```

### Rebuild Index

**You**:
```
Rebuild the requirements index
```

**Agent** (uses `requirements_index`):
```
✅ Requirements index rebuilt successfully!

- Total requirements: 3
- Last updated: 2025-11-18T15:45:00Z

Status breakdown:
- proposed: 1
- accepted: 2
- implemented: 0
- deprecated: 0
```

---

## Tips for Effective Requirements Capture

### 💡 Speak Naturally

Don't try to speak in "requirement language". Just discuss your product:

✅ **Good**: "Users should be able to reset their password if they forget it."

❌ **Avoid**: "REQ-004 SHALL IMPLEMENT PASSWORD RESET FUNCTIONALITY."

The agent will structure it for you!

### 💡 Provide Concrete Examples

Examples make requirements clearer and testable:

✅ **Good**: "If a user enters the wrong password 5 times, lock their account for 15 minutes."

❌ **Vague**: "Protect against brute force attacks."

### 💡 One Conversation at a Time

Focus on one area or feature per conversation:

✅ **Good**: "Let's talk about authentication features."

❌ **Confusing**: "I need auth, payments, and reporting all at once."

### 💡 Use the Agent to Clarify

If you're unsure about a requirement, ask:

**You**: "What questions should I answer about the password reset feature?"

**Agent**: "Great question! For password reset, I'd need to know:
- How does the user initiate the reset? (email link, SMS, security questions?)
- How long should the reset link be valid?
- Should we verify identity before allowing reset?
- Any rate limiting (e.g., only 3 reset requests per day)?"

### 💡 Review and Iterate

Requirements aren't set in stone. You can update them:

**You**: "Actually, REQ-001 should also support OAuth login with Google."

**Agent**: "I'll update REQ-001 to include OAuth. Should this be:
- Added to the existing requirement, or
- A separate requirement (REQ-004: OAuth login)?

I recommend separating them for clearer acceptance criteria."

---

## Next Steps

### Enable RAG for Smart Duplicate Detection

1. **Create a Knowledge Base**:
   - Go to **Workspace** → **Knowledge**
   - Click **"+ Create Knowledge Base"**
   - Name: "Requirements Database"

2. **Add Requirements Folder**:
   - In your Knowledge Base, click **"+ Add Files"**
   - Upload `.md` files from `backend/data/requirements/`

3. **Link to Chat**:
   - In your chat, click the **Knowledge** icon
   - Select "Requirements Database"

Now the agent will automatically:
- Find similar requirements when you propose new ones
- Detect potential duplicates
- Show related requirements for context

### Customize Agent Behavior

In **Admin Panel** → **Functions** → **Requirements Agent Filter** → **Valves**:

**For Proactive Extraction** (analyst mode):
```python
agent_mode = "analyst"
enable_auto_extraction = True
```
The agent will actively extract requirements without being asked.

**For Manual Control** (silent mode):
```python
agent_mode = "silent"
enable_auto_extraction = False
```
The agent only responds when you explicitly ask.

**For Strict Gherkin** (enforce scenarios):
```python
enable_gherkin_prompts = True
```
The agent will always request Gherkin examples.

### Integrate with Git

Track your requirements in version control:

```bash
cd backend/data/requirements
git init
git add .
git commit -m "Initial requirements capture"
```

Now you can:
- Review requirements changes via pull requests
- Track requirement evolution over time
- Collaborate with team members
- Branch for different requirement proposals

---

## Troubleshooting

### "Tools not appearing in chat"

1. Verify tool is saved in **Workspace → Tools**
2. Refresh the browser page
3. Click the tools icon (🔧) in chat and toggle it on

### "Agent not extracting requirements"

1. Check Filter is enabled in **Admin Panel → Functions**
2. Verify `agent_mode` is set to `"assistant"` or `"analyst"`
3. Use trigger words: "requirement", "should", "user story", "feature"

### "Files not being created"

1. Check permissions on `backend/data/` folder
2. Verify dependencies installed: `pip install pyyaml python-slugify`
3. Check Open WebUI logs for errors

### "Can't find stored requirements"

1. Check `backend/data/requirements/` folder exists
2. Verify files are in correct subfolders (backlog, decided, etc.)
3. Rebuild index: "Rebuild the requirements index"

---

## What's Next?

You're now ready to:

✅ Capture requirements through natural conversation
✅ Structure them as Spec-by-Example with Gherkin scenarios
✅ Store them in a git-friendly format
✅ Search, filter, and manage your requirements

**Next explore**:
- [Full Setup Guide](REQUIREMENTS_AGENT_SETUP.md) - Detailed configuration
- [Requirements Examples](REQUIREMENTS_EXAMPLES.md) - Best practices and templates
- [Contributing](README.md) - Help improve the Requirements Agent

---

Happy requirements engineering! 🎯

**Questions?** Open an issue on the Open WebUI GitHub repo with the tag `requirements-agent`.
