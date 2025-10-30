"""
Django management command for running API performance benchmarks.

Usage:
    python manage.py benchmark_api
    python manage.py benchmark_api --endpoint profiles --iterations 50
    python manage.py benchmark_api --full-suite
"""

import time
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from profiles.models import UserProfileBasic
from recovery.models import RecoveryProfile, RecoveryGoal

User = get_user_model()


class Command(BaseCommand):
    help = 'Run API performance benchmarks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--endpoint',
            type=str,
            choices=['profiles', 'recovery', 'auth', 'all'],
            default='all',
            help='Which endpoints to benchmark'
        )
        parser.add_argument(
            '--iterations',
            type=int,
            default=20,
            help='Number of iterations per endpoint'
        )
        parser.add_argument(
            '--target-time',
            type=float,
            default=0.2,
            help='Target response time in seconds'
        )
        parser.add_argument(
            '--full-suite',
            action='store_true',
            help='Run full benchmark suite with detailed output'
        )
        parser.add_argument(
            '--output-format',
            choices=['table', 'json'],
            default='table',
            help='Output format'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting API Performance Benchmarks')
        )

        # Setup test data
        self.setup_test_data()

        # Setup authenticated client
        self.setup_client()

        # Run benchmarks
        if options['endpoint'] == 'all' or options['full_suite']:
            results = self.run_full_benchmark_suite(options)
        else:
            results = self.run_specific_benchmark(options['endpoint'], options)

        # Output results
        self.output_results(results, options)

        # Check if targets were met
        self.check_performance_targets(results, options['target_time'])

    def setup_test_data(self):
        """Create test user and associated data."""
        # Clean up any existing test user
        User.objects.filter(username='benchmark_user').delete()

        # Create test user
        self.user = User.objects.create_user(
            username='benchmark_user',
            email='benchmark@example.com',
            password='testpass123'  # nosec - test password
        )

        # Create profiles
        self.basic_profile = UserProfileBasic.objects.create(
            user=self.user,
            display_name='Benchmark User',
            bio='Performance testing user'
        )

        self.recovery_profile = RecoveryProfile.objects.create(
            user=self.user
        )

        # Create some recovery goals
        for i in range(3):
            RecoveryGoal.objects.create(
                user=self.user,
                goal_type='sobriety',
                target_value=30 + (i * 10),
                current_value=i * 5,
                description=f'Benchmark goal {i+1}'
            )

    def setup_client(self):
        """Setup authenticated API client."""
        self.client = APIClient()

        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def benchmark_endpoint(self, url, method='GET', data=None, iterations=20):
        """
        Benchmark a single endpoint.

        Returns dict with performance statistics.
        """
        response_times = []
        successful_requests = 0

        for _ in range(iterations):
            start_time = time.time()

            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, data or {})
            elif method == 'PATCH':
                response = self.client.patch(url, data or {})
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_time = time.time() - start_time
            response_times.append(response_time)

            if 200 <= response.status_code < 300:
                successful_requests += 1

        if not response_times:
            return None

        sorted_times = sorted(response_times)
        return {
            'url': url,
            'method': method,
            'iterations': iterations,
            'successful_requests': successful_requests,
            'success_rate': (successful_requests / iterations) * 100,
            'min_time': min(response_times),
            'max_time': max(response_times),
            'avg_time': sum(response_times) / len(response_times),
            'median_time': sorted_times[len(sorted_times) // 2],
            'p95_time': sorted_times[int(0.95 * len(sorted_times))],
            'p99_time': sorted_times[int(0.99 * len(sorted_times))],
        }

    def run_full_benchmark_suite(self, options):
        """Run comprehensive benchmark suite."""
        results = {}
        iterations = options['iterations']

        # Profile endpoints
        self.stdout.write('📊 Benchmarking Profile endpoints...')
        results['profiles'] = {
            'list': self.benchmark_endpoint(
                reverse('userprofile-list'), iterations=iterations
            ),
            'detail': self.benchmark_endpoint(
                reverse('userprofile-detail',
                        kwargs={'pk': self.basic_profile.pk}),
                iterations=iterations
            ),
            'update': self.benchmark_endpoint(
                reverse('userprofile-detail',
                        kwargs={'pk': self.basic_profile.pk}),
                method='PATCH',
                data={'display_name': 'Updated Name'},
                iterations=iterations // 2  # Fewer iterations for write operations
            ),
        }

        # Recovery endpoints
        self.stdout.write('🎯 Benchmarking Recovery endpoints...')
        goal = RecoveryGoal.objects.filter(user=self.user).first()
        results['recovery'] = {
            'goals_list': self.benchmark_endpoint(
                reverse('recoverygoal-list'), iterations=iterations
            ),
            'dashboard': self.benchmark_endpoint(
                reverse('recovery-dashboard'), iterations=iterations
            ),
        }

        if goal:
            results['recovery']['goal_detail'] = self.benchmark_endpoint(
                reverse('recoverygoal-detail', kwargs={'pk': goal.pk}),
                iterations=iterations
            )

        return results

    def run_specific_benchmark(self, endpoint, options):
        """Run benchmark for specific endpoint category."""
        iterations = options['iterations']

        if endpoint == 'profiles':
            return {
                'profiles': {
                    'list': self.benchmark_endpoint(
                        reverse('userprofile-list'), iterations=iterations
                    ),
                    'detail': self.benchmark_endpoint(
                        reverse('userprofile-detail',
                                kwargs={'pk': self.basic_profile.pk}),
                        iterations=iterations
                    ),
                }
            }
        elif endpoint == 'recovery':
            return {
                'recovery': {
                    'goals_list': self.benchmark_endpoint(
                        reverse('recoverygoal-list'), iterations=iterations
                    ),
                    'dashboard': self.benchmark_endpoint(
                        reverse('recovery-dashboard'), iterations=iterations
                    ),
                }
            }

        return {}

    def output_results(self, results, options):
        """Output benchmark results."""
        if options['output_format'] == 'json':
            self.stdout.write(json.dumps(results, indent=2))
            return

        # Table format
        self.stdout.write('\n📈 Performance Benchmark Results')
        self.stdout.write('=' * 50)

        for category, endpoints in results.items():
            self.stdout.write(f'\n{category.upper()} Endpoints:')
            self.stdout.write('-' * 30)

            for endpoint_name, stats in endpoints.items():
                if not stats:
                    continue

                self.stdout.write(f'\n{endpoint_name}:')
                self.stdout.write(f'  Iterations: {stats["iterations"]}')
                self.stdout.write(
                    f'  Success Rate: {stats["success_rate"]:.1f}%')
                self.stdout.write(
                    f'  Avg Time: {stats["avg_time"]*1000:.1f}ms')
                self.stdout.write(
                    f'  P95 Time: {stats["p95_time"]*1000:.1f}ms')
                self.stdout.write(
                    f'  Max Time: {stats["max_time"]*1000:.1f}ms')

    def check_performance_targets(self, results, target_time):
        """Check if performance targets were met."""
        self.stdout.write('\n🎯 Performance Target Analysis')
        self.stdout.write('=' * 40)

        failed_targets = []

        for category, endpoints in results.items():
            for endpoint_name, stats in endpoints.items():
                if not stats:
                    continue

                avg_time = stats['avg_time']
                p95_time = stats['p95_time']

                # Check average time target
                if avg_time > target_time:
                    failed_targets.append(
                        f'{category}.{endpoint_name} avg: {avg_time*1000:.1f}ms')

                # Check P95 time target (allow 50% higher than target)
                if p95_time > target_time * 1.5:
                    failed_targets.append(
                        f'{category}.{endpoint_name} P95: {p95_time*1000:.1f}ms')

        if failed_targets:
            self.stdout.write(
                self.style.ERROR(
                    f'❌ Failed targets (>{target_time*1000:.0f}ms):')
            )
            for failure in failed_targets:
                self.stdout.write(f'   {failure}')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ All endpoints met target of {target_time*1000:.0f}ms')
            )

        # Cleanup
        self.cleanup_test_data()

    def cleanup_test_data(self):
        """Clean up test data."""
        User.objects.filter(username='benchmark_user').delete()
        self.stdout.write('\n🧹 Test data cleaned up')
