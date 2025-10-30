#!/bin/bash
# Git Security Setup Script for Vineyard Group Fellowship
# This script sets up security measures to prevent sensitive data from being committed

set -e  # Exit on any error

echo "🔒 Setting up Git Security for Vineyard Group Fellowship..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if we're in the correct directory
if [ ! -f "manage.py" ]; then
    print_error "This script must be run from the Django project root directory"
    exit 1
fi

# 1. Initialize git repository if not already done
if [ ! -d ".git" ]; then
    print_info "Initializing git repository..."
    git init
    print_status "Git repository initialized"
else
    print_status "Git repository already exists"
fi

# 2. Set up git hooks directory
mkdir -p .git/hooks

# 3. Create pre-commit hook for secret scanning
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook to prevent secrets from being committed

echo "🔍 Scanning for secrets and sensitive data..."

# Check for .env files (except examples)
if git diff --cached --name-only | grep -E "^\.env$|^\.env\.local$|^\.env\.production$" > /dev/null; then
    echo "❌ ERROR: .env files should not be committed!"
    echo "   Found: $(git diff --cached --name-only | grep -E '^\.env')"
    echo "   Use .env.example instead for templates"
    exit 1
fi

# Check for common secret patterns
if git diff --cached | grep -iE "(password|api_key|secret_key|private_key|access_token)\s*=\s*[\"'][^\"']*[\"']" | grep -v "# nosec" | grep -v "test" | grep -v "example" > /dev/null; then
    echo "❌ ERROR: Potential hardcoded secrets detected!"
    echo "   Use environment variables instead"
    echo "   If this is intentional, add '# nosec' comment"
    exit 1
fi

# Check for default Django secret key
if git diff --cached | grep -E "SECRET_KEY.*=.*[\"']your-secret-key-here[\"']" > /dev/null; then
    echo "❌ ERROR: Default Django SECRET_KEY detected!"
    echo "   Please change the secret key before committing"
    exit 1
fi

# Check for database files
if git diff --cached --name-only | grep -E "\.(db|sqlite|sqlite3)$" > /dev/null; then
    echo "❌ ERROR: Database files should not be committed!"
    echo "   Found: $(git diff --cached --name-only | grep -E '\.(db|sqlite|sqlite3)$')"
    exit 1
fi

# Check for large files (>10MB)
if git diff --cached --name-only | xargs -I {} sh -c 'test -f "{}" && test $(stat -f%z "{}" 2>/dev/null || stat -c%s "{}" 2>/dev/null || echo 0) -gt 10485760' 2>/dev/null; then
    echo "❌ ERROR: Large files detected (>10MB)!"
    echo "   Consider using Git LFS for large files"
    exit 1
fi

# Check for private keys
if git diff --cached | grep -E "BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY" > /dev/null; then
    echo "❌ ERROR: Private key detected!"
    echo "   Private keys should never be committed"
    exit 1
fi

# Check for AWS keys
if git diff --cached | grep -iE "(AKIA[0-9A-Z]{16}|aws_secret_access_key)" > /dev/null; then
    echo "❌ ERROR: AWS credentials detected!"
    echo "   Use AWS IAM roles or environment variables"
    exit 1
fi

echo "✅ Security scan passed!"
EOF

# Make the pre-commit hook executable
chmod +x .git/hooks/pre-commit
print_status "Pre-commit security hook installed"

# 4. Set up git configuration for security
git config --local core.autocrlf false
git config --local core.filemode false
git config --local push.default simple
git config --local pull.rebase false

print_status "Git configuration set for security"

# 5. Check current .env file situation
print_info "Checking environment files..."

if [ -f ".env" ]; then
    print_warning ".env file exists - this contains sensitive data"
    print_info "Make sure it's in .gitignore (it should be)"
fi

if [ ! -f ".env.example" ]; then
    print_warning ".env.example not found - creating template"
    cat > .env.example << 'EOF'
# Django Configuration Template
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_HOST=your.smtp.host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password

# External API Keys (use your own values)
SENDGRID_API_KEY=your_sendgrid_api_key_here
STRIPE_SECRET_KEY=your_stripe_secret_key_here

# Security Settings
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
EOF
    print_status ".env.example template created"
fi

# 6. Install security development dependencies
print_info "Installing security development tools..."

# Check if we're in a virtual environment
if [ -n "$VIRTUAL_ENV" ] || [ -d ".venv" ]; then
    # Use the appropriate pip
    if [ -d ".venv" ]; then
        PIP_CMD=".venv/bin/pip"
    else
        PIP_CMD="pip"
    fi
    
    # Install security tools
    $PIP_CMD install --quiet bandit detect-secrets pre-commit safety
    print_status "Security tools installed"
else
    print_warning "Virtual environment not detected - skipping tool installation"
    print_info "Run: pip install bandit detect-secrets pre-commit safety"
fi

# 7. Set up pre-commit hooks (if pre-commit is available)
if command -v pre-commit >/dev/null 2>&1; then
    print_info "Installing pre-commit hooks..."
    pre-commit install
    print_status "Pre-commit hooks installed"
else
    print_warning "pre-commit not available - install with: pip install pre-commit"
fi

# 8. Create security checklist
cat > SECURITY_CHECKLIST.md << 'EOF'
# Security Checklist - Vineyard Group Fellowship

## Before First Git Commit

- [ ] `.gitignore` file is properly configured
- [ ] `.env` files are in `.gitignore` 
- [ ] `.env.example` template exists (without real secrets)
- [ ] Django `SECRET_KEY` is not the default value
- [ ] Database credentials are in environment variables, not hardcoded
- [ ] API keys are in environment variables, not hardcoded
- [ ] Pre-commit hooks are installed and working
- [ ] No sensitive files are staged for commit

## Regular Security Checks

- [ ] Run `bandit -r .` to scan for security issues
- [ ] Run `safety check` to check for vulnerable dependencies
- [ ] Review `.env` files to ensure no secrets are hardcoded
- [ ] Check that production settings use strong security headers
- [ ] Verify that debug mode is disabled in production
- [ ] Ensure all external API keys are properly secured

## Git Security Commands

```bash
# Scan for secrets before committing
git diff --cached | grep -iE "(password|api_key|secret|token)" || echo "No secrets found"

# Check for large files
git diff --cached --name-only | xargs ls -la

# Run security scan
bandit -r . -f json -o security-report.json

# Check dependencies for vulnerabilities
safety check

# Update pre-commit hooks
pre-commit autoupdate
```

## Production Deployment Security

- [ ] `DEBUG = False` in production settings
- [ ] Strong `SECRET_KEY` (not the default)
- [ ] Database credentials from environment/secrets manager
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT = True`)
- [ ] Secure cookie settings enabled
- [ ] HSTS headers configured
- [ ] CSP headers configured
- [ ] Regular security audits scheduled

## Emergency Response

If secrets are accidentally committed:

1. **Immediate**: Rotate all exposed credentials
2. **Git**: Remove from history with `git filter-branch` or BFG
3. **Audit**: Check access logs for unauthorized usage
4. **Prevent**: Review and strengthen security measures
EOF

print_status "Security checklist created (SECURITY_CHECKLIST.md)"

# 9. Final security scan
print_info "Running final security checks..."

# Check if any .env files are tracked
if git ls-files | grep -E "^\.env$" > /dev/null; then
    print_error ".env file is currently tracked by git!"
    print_info "Run: git rm --cached .env"
fi

# Check for any currently staged sensitive files
if git diff --cached --name-only | grep -E "\.(key|pem|p12|pfx)$" > /dev/null; then
    print_error "Certificate/key files are staged for commit!"
fi

print_status "Security setup complete!"
echo ""
print_info "Next steps:"
echo "  1. Review .gitignore and SECURITY_CHECKLIST.md"
echo "  2. Copy .env.example to .env and add your real values"
echo "  3. Run: git add . && git commit -m 'Initial commit with security setup'"
echo "  4. The pre-commit hook will automatically scan for secrets"
echo ""
print_warning "Remember: Never commit real secrets, API keys, or passwords!"