# Git & Security Setup Guide - Vineyard Group Fellowship

## 🔒 Security Overview

This guide ensures that sensitive information like API keys, passwords, and secrets are never committed to your git repository. Follow these steps before making your first commit.

## ⚠️ Critical Security Rules

1. **NEVER commit `.env` files** - they contain real secrets
2. **NEVER commit database files** - they contain user data
3. **NEVER commit API keys or passwords** - use environment variables
4. **ALWAYS use `.env.example`** - for configuration templates
5. **ALWAYS run security checks** - before pushing to git

## 🚀 Quick Setup (Automated)

Run the automated security setup script:

```bash
# From the backend directory
./scripts/setup-git-security.sh
```

This script will:
- Set up `.gitignore` with security patterns
- Install pre-commit hooks for secret scanning
- Create security templates and checklists
- Configure git settings for security

## 📋 Manual Setup Steps

If you prefer manual setup or need to understand what's happening:

### 1. Initialize Git Repository

```bash
# Initialize git if not already done
git init

# Set safe git configuration
git config --local core.autocrlf false
git config --local core.filemode false
git config --local push.default simple
```

### 2. Verify .gitignore Coverage

Ensure your `.gitignore` includes these critical patterns:

```gitignore
# Environment files (CRITICAL)
.env
.env.*
!.env.example
!.env.docker.example

# Database files (CRITICAL)
*.db
*.sqlite3
db.sqlite3

# API Keys and Secrets (CRITICAL)
*.key
*.pem
*.p12
*.pfx
api_keys.txt
credentials.json

# Django specific
media/
staticfiles/
__pycache__/
*.log
```

### 3. Set Up Environment Files

```bash
# Copy template and add real values (NEVER commit the real .env)
cp .env.example .env

# Edit .env with your real values
nano .env

# Verify .env is gitignored
git check-ignore .env  # Should return ".env"
```

### 4. Install Security Tools

```bash
# Activate virtual environment first
source .venv/bin/activate  # or however you activate yours

# Install security scanning tools
pip install bandit detect-secrets pre-commit safety

# Install pre-commit hooks
pre-commit install
```

### 5. Run Security Validation

```bash
# Run comprehensive security check
python scripts/security-check.py

# Run dependency vulnerability scan
safety check

# Run code security scan
bandit -r . -f json -o security-report.json
```

## 🔍 Pre-Commit Security Checks

Every commit automatically runs these security checks:

1. **Secret Detection**: Scans for API keys, passwords, tokens
2. **Environment File Check**: Prevents committing `.env` files
3. **Large File Detection**: Prevents committing files >10MB
4. **Private Key Detection**: Prevents committing certificates/keys
5. **Default Value Check**: Ensures no default Django secret keys

## 🛡️ Environment Variables Security

### Required Environment Variables

Create these in your `.env` file (NEVER commit):

```bash
# Django Security
SECRET_KEY=your-actual-secret-key-here-make-it-long-and-random
DEBUG=True  # False in production

# Database Credentials
DB_NAME=vineyard_group_fellowship
DB_USER=your_db_user
DB_PASSWORD=your_secure_db_password
DB_HOST=localhost
DB_PORT=5432

# External API Keys
SENDGRID_API_KEY=SG.your_actual_sendgrid_key_here
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here

# Security Settings (production)
SECURE_SSL_REDIRECT=True  # Production only
SESSION_COOKIE_SECURE=True  # Production only
CSRF_COOKIE_SECURE=True  # Production only
```

### Environment Template (.env.example)

Keep safe templates in `.env.example` (this CAN be committed):

```bash
# Template - replace with real values
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_PASSWORD=your_database_password
SENDGRID_API_KEY=your_sendgrid_api_key_here
```

## 🚨 Emergency: Secrets Accidentally Committed

If you accidentally commit secrets:

### 1. Immediate Response (CRITICAL)
```bash
# Immediately rotate ALL exposed credentials
# - Change Django SECRET_KEY
# - Regenerate API keys (SendGrid, Stripe, etc.)
# - Change database passwords
# - Revoke OAuth tokens
```

### 2. Remove from Git History
```bash
# Remove file from git history (DESTRUCTIVE)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all

# Or use BFG (recommended for large repos)
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive
```

### 3. Force Push (if remote exists)
```bash
# WARNING: This rewrites history for all collaborators
git push --force-with-lease origin main
```

### 4. Audit and Monitor
- Check access logs for unauthorized usage
- Monitor for unusual account activity
- Set up alerts for the affected services

## 📊 Security Monitoring

### Regular Security Checks

Run these commands regularly:

```bash
# Full security validation
python scripts/security-check.py --report

# Check for vulnerable dependencies
safety check

# Scan code for security issues
bandit -r . -f json -o security-report.json

# Update security tools
pre-commit autoupdate
pip install --upgrade bandit safety detect-secrets
```

### Git Security Commands

```bash
# Check what's staged before committing
git diff --cached --name-only

# Scan staged changes for secrets
git diff --cached | grep -iE "(password|api_key|secret|token)"

# Check if sensitive files are tracked
git ls-files | grep -E "\.(env|key|pem)$"

# See what would be committed
git status --porcelain
```

## 🔧 IDE/Editor Security Settings

### VS Code Settings

Add to `.vscode/settings.json`:

```json
{
    "files.exclude": {
        "**/.env": true,
        "**/*.key": true,
        "**/*.pem": true,
        "**/db.sqlite3": true
    },
    "search.exclude": {
        "**/.env": true,
        "**/logs": true
    }
}
```

### Environment Variables in IDE

Never put real secrets in:
- VS Code launch configurations
- PyCharm run configurations
- Jupyter notebook cells
- Debug configurations

## 📝 Security Checklist

Before each commit:

- [ ] `.env` file is not staged (`git status` shows it's untracked/ignored)
- [ ] No hardcoded API keys in code
- [ ] No database files staged for commit
- [ ] No certificate/key files staged for commit
- [ ] Pre-commit hooks pass without errors
- [ ] Security scan shows no critical issues

Before deployment:

- [ ] `DEBUG = False` in production settings
- [ ] Strong `SECRET_KEY` (not default value)
- [ ] All API keys are from environment variables
- [ ] Database credentials are secure
- [ ] HTTPS enforced in production
- [ ] Security headers configured
- [ ] Dependencies are up to date and secure

## 📞 Security Support

If you discover a security issue:

1. **Don't commit it** - stop and assess
2. **Rotate credentials** - if they might be exposed
3. **Run security scan** - `python scripts/security-check.py`
4. **Check git history** - ensure no secrets in past commits
5. **Document the issue** - for future prevention

## 🔗 Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/5.0/topics/security/)
- [Git Security Best Practices](https://git-scm.com/book/en/v2/GitHub-Account-Management-and-Security)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [12-Factor App Methodology](https://12factor.net/)

---

**Remember**: Security is not optional. Taking time to set up these protections now will save you from serious security incidents later.