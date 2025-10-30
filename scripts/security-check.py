#!/usr/bin/env python3
"""
Security Validation Script for Vineyard Group Fellowship
Checks for common security issues before deployment or git commits
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple


class SecurityValidator:
    """Validates security configuration and checks for vulnerabilities."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.warnings = []

    def check_environment_files(self) -> None:
        """Check for .env files and sensitive data exposure."""
        print("🔍 Checking environment files...")

        # Check for .env files in git tracking
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            tracked_files = result.stdout.strip().split(
                '\n') if result.stdout.strip() else []
            env_files = [f for f in tracked_files if f.endswith(
                '.env') and not f.endswith('.env.example')]

            if env_files:
                self.issues.append(
                    f"❌ .env files are tracked by git: {', '.join(env_files)}")
            else:
                print("✅ No .env files tracked by git")

        except subprocess.SubprocessError:
            self.warnings.append("⚠️ Could not check git tracked files")

        # Check if .env.example exists
        env_example = self.project_root / '.env.example'
        if not env_example.exists():
            self.warnings.append("⚠️ .env.example template not found")
        else:
            print("✅ .env.example template exists")

        # Check .env file content for hardcoded secrets
        env_file = self.project_root / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()

            # Check for default values that should be changed
            if 'your-secret-key-here' in content:
                self.issues.append(
                    "❌ Django SECRET_KEY is still default value")

            if 'your_' in content.lower():
                self.warnings.append(
                    "⚠️ .env contains template values (your_*)")

    def check_django_settings(self) -> None:
        """Check Django settings for security issues."""
        print("🔍 Checking Django settings...")

        settings_files = [
            'vineyard_group_fellowship/settings.py',
            'vineyard_group_fellowship/settings/base.py',
            'vineyard_group_fellowship/settings/production.py',
        ]

        for settings_file in settings_files:
            file_path = self.project_root / settings_file
            if file_path.exists():
                self._check_settings_file(file_path)

    def _check_settings_file(self, file_path: Path) -> None:
        """Check individual settings file."""
        with open(file_path, 'r') as f:
            content = f.read()

        # Check for hardcoded secrets
        secret_patterns = [
            r"SECRET_KEY\s*=\s*['\"](?!.*config\(|.*getenv|.*env\.|.*os\.environ)[^'\"]*['\"]",
            r"(API_KEY|PASSWORD|TOKEN)\s*=\s*['\"][^'\"]*['\"]",
        ]

        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append(f"❌ Hardcoded secret in {file_path.name}")

        # Check for debug mode in production-like files
        if 'production' in file_path.name.lower():
            if re.search(r"DEBUG\s*=\s*True", content):
                self.issues.append(f"❌ DEBUG=True in {file_path.name}")

        # Check for security headers
        security_settings = [
            'SECURE_SSL_REDIRECT',
            'SECURE_HSTS_SECONDS',
            'X_FRAME_OPTIONS',
            'SECURE_CONTENT_TYPE_NOSNIFF',
        ]

        missing_security = []
        for setting in security_settings:
            if setting not in content:
                missing_security.append(setting)

        if missing_security and 'production' in file_path.name.lower():
            self.warnings.append(
                f"⚠️ Missing security settings in {file_path.name}: {', '.join(missing_security)}")

    def check_dependencies(self) -> None:
        """Check for vulnerable dependencies."""
        print("🔍 Checking dependencies for vulnerabilities...")

        # Check if safety is available
        try:
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )

            if result.returncode != 0:
                if result.stdout:
                    # Parse safety output
                    try:
                        vulnerabilities = json.loads(result.stdout)
                        if vulnerabilities:
                            self.issues.append(
                                f"❌ {len(vulnerabilities)} vulnerable dependencies found")
                            for vuln in vulnerabilities[:3]:  # Show first 3
                                self.issues.append(
                                    f"   - {vuln.get('package', 'Unknown')} {vuln.get('installed_version', '')}")
                    except json.JSONDecodeError:
                        self.warnings.append(
                            "⚠️ Could not parse safety check results")
                else:
                    self.warnings.append("⚠️ Safety check failed")
            else:
                print("✅ No known vulnerable dependencies")

        except FileNotFoundError:
            self.warnings.append(
                "⚠️ Safety tool not installed (pip install safety)")

    def check_git_configuration(self) -> None:
        """Check git configuration for security."""
        print("🔍 Checking git configuration...")

        # Check if .gitignore exists and has necessary entries
        gitignore = self.project_root / '.gitignore'
        if not gitignore.exists():
            self.issues.append("❌ .gitignore file missing")
            return

        with open(gitignore, 'r') as f:
            gitignore_content = f.read()

        required_patterns = [
            '.env',
            '*.key',
            '*.pem',
            'db.sqlite3',
            '__pycache__',
            '.venv',
        ]

        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)

        if missing_patterns:
            self.warnings.append(
                f"⚠️ .gitignore missing patterns: {', '.join(missing_patterns)}")
        else:
            print("✅ .gitignore has essential security patterns")

        # Check for pre-commit hooks
        pre_commit_hook = self.project_root / '.git' / 'hooks' / 'pre-commit'
        if pre_commit_hook.exists():
            print("✅ Pre-commit hook installed")
        else:
            self.warnings.append("⚠️ No pre-commit hook found")

    def check_file_permissions(self) -> None:
        """Check for sensitive files with wrong permissions."""
        print("🔍 Checking file permissions...")

        sensitive_files = [
            '.env',
            'private.key',
            'server.key',
        ]

        for filename in sensitive_files:
            file_path = self.project_root / filename
            if file_path.exists():
                # Check if file is readable by others
                stat_info = file_path.stat()
                permissions = oct(stat_info.st_mode)[-3:]

                if permissions[1:] != '00':  # Should be -rw-------
                    self.warnings.append(
                        f"⚠️ {filename} has permissive permissions: {permissions}")

    def check_database_security(self) -> None:
        """Check database configuration security."""
        print("🔍 Checking database security...")

        # Check if SQLite database files exist and are gitignored
        db_files = list(self.project_root.glob('*.db')) + \
            list(self.project_root.glob('*.sqlite*'))

        if db_files:
            try:
                result = subprocess.run(
                    ['git', 'check-ignore'] + [str(f) for f in db_files],
                    capture_output=True,
                    cwd=self.project_root
                )

                if result.returncode != 0:
                    self.warnings.append(
                        f"⚠️ Database files not gitignored: {[f.name for f in db_files]}")
                else:
                    print("✅ Database files are properly gitignored")

            except subprocess.SubprocessError:
                self.warnings.append(
                    "⚠️ Could not check if database files are gitignored")

    def run_validation(self) -> bool:
        """Run all security checks."""
        print("🔒 Running security validation for Vineyard Group Fellowship...\n")

        self.check_environment_files()
        self.check_django_settings()
        self.check_dependencies()
        self.check_git_configuration()
        self.check_file_permissions()
        self.check_database_security()

        print("\n" + "="*60)
        print("SECURITY VALIDATION RESULTS")
        print("="*60)

        if self.issues:
            print("\n🚨 CRITICAL ISSUES (must fix before commit/deploy):")
            for issue in self.issues:
                print(f"  {issue}")

        if self.warnings:
            print("\n⚠️ WARNINGS (should fix):")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.issues and not self.warnings:
            print("\n✅ All security checks passed!")

        print(
            f"\nSummary: {len(self.issues)} critical issues, {len(self.warnings)} warnings")

        return len(self.issues) == 0

    def generate_report(self) -> Dict[str, Any]:
        """Generate a detailed security report."""
        return {
            'timestamp': os.popen('date').read().strip(),
            'project': 'Vineyard Group Fellowship',
            'critical_issues': self.issues,
            'warnings': self.warnings,
            'total_issues': len(self.issues),
            'total_warnings': len(self.warnings),
            'passed': len(self.issues) == 0
        }


def main():
    """Main entry point."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root.endswith('/scripts'):
        project_root = os.path.dirname(project_root)

    validator = SecurityValidator(project_root)

    # Run validation
    passed = validator.run_validation()

    # Generate report if requested
    if '--report' in sys.argv:
        report = validator.generate_report()
        with open('security-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to security-report.json")

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
