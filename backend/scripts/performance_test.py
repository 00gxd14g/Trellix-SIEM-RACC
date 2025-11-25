#!/usr/bin/env python3
"""
Database Performance Testing Script

Tests and benchmarks database performance with and without optimizations.

Usage:
    python scripts/performance_test.py --test-cache
    python scripts/performance_test.py --test-queries
    python scripts/performance_test.py --test-all

Author: Database Optimizer Agent
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from main import create_app
from models import db, Customer, Rule, Alarm, SystemSetting, CustomerSetting
from utils.cache_manager import get_cache, init_cache
from utils.db_optimizer import get_query_monitor, get_database_stats


class PerformanceTest:
    """Performance testing utilities"""

    def __init__(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def cleanup(self):
        """Cleanup test context"""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def benchmark_query(self, query_func, iterations=100):
        """
        Benchmark a query function

        Args:
            query_func: Function to execute
            iterations: Number of iterations

        Returns:
            Dictionary with benchmark results
        """
        times = []

        # Warm-up run
        query_func()

        # Benchmark runs
        for _ in range(iterations):
            start = time.time()
            query_func()
            duration = time.time() - start
            times.append(duration)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        total_time = sum(times)

        return {
            'iterations': iterations,
            'avg_time_ms': avg_time * 1000,
            'min_time_ms': min_time * 1000,
            'max_time_ms': max_time * 1000,
            'total_time_s': total_time,
            'queries_per_sec': iterations / total_time if total_time > 0 else 0
        }

    def test_cache_performance(self):
        """Test cache performance"""
        print("\n" + "=" * 60)
        print("CACHE PERFORMANCE TEST")
        print("=" * 60)

        cache = get_cache()

        # Test 1: Cache write performance
        print("\n1. Cache Write Performance")
        def cache_write():
            for i in range(100):
                cache.set(f'test_key_{i}', {'data': f'value_{i}'}, ttl=300)

        result = self.benchmark_query(cache_write, iterations=10)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Operations/sec: {result['queries_per_sec'] * 100:.0f}")

        # Test 2: Cache read performance
        print("\n2. Cache Read Performance (hits)")
        def cache_read():
            for i in range(100):
                cache.get(f'test_key_{i}')

        result = self.benchmark_query(cache_read, iterations=10)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Operations/sec: {result['queries_per_sec'] * 100:.0f}")

        # Test 3: Cache miss performance
        print("\n3. Cache Read Performance (misses)")
        cache.clear()
        result = self.benchmark_query(cache_read, iterations=10)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Operations/sec: {result['queries_per_sec'] * 100:.0f}")

        # Test 4: Cache statistics
        print("\n4. Cache Statistics")
        stats = cache.get_stats()
        print(f"   Total requests: {stats['total_requests']}")
        print(f"   Cache hits: {stats['hits']}")
        print(f"   Cache misses: {stats['misses']}")
        print(f"   Hit rate: {stats['hit_rate']}")

    def setup_test_data(self, customer_count=5, rules_per_customer=100):
        """Setup test data"""
        print(f"\nSetting up test data ({customer_count} customers, {rules_per_customer} rules each)...")

        for i in range(customer_count):
            customer = Customer(
                name=f'Test Customer {i}',
                description=f'Test customer {i} for performance testing'
            )
            db.session.add(customer)
            db.session.flush()

            # Add rules
            for j in range(rules_per_customer):
                rule = Rule(
                    customer_id=customer.id,
                    rule_id=f'test-rule-{i}-{j}',
                    name=f'Test Rule {i}-{j}',
                    severity=50 if j % 2 == 0 else 75,
                    sig_id=f'{i}|{j}',
                    xml_content=f'<rule id="{i}-{j}">test</rule>'
                )
                db.session.add(rule)

        db.session.commit()
        print("Test data created successfully")

    def test_query_performance(self):
        """Test query performance"""
        print("\n" + "=" * 60)
        print("QUERY PERFORMANCE TEST")
        print("=" * 60)

        # Setup test data
        self.setup_test_data(customer_count=3, rules_per_customer=200)

        # Test 1: Simple filter query
        print("\n1. Simple Filter Query (customer_id)")
        def simple_filter():
            rules = Rule.query.filter_by(customer_id=1).all()
            return len(rules)

        result = self.benchmark_query(simple_filter, iterations=50)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Queries/sec: {result['queries_per_sec']:.0f}")

        # Test 2: Complex filter query
        print("\n2. Complex Filter Query (customer_id + severity)")
        def complex_filter():
            rules = Rule.query.filter(
                Rule.customer_id == 1,
                Rule.severity >= 50
            ).all()
            return len(rules)

        result = self.benchmark_query(complex_filter, iterations=50)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Queries/sec: {result['queries_per_sec']:.0f}")

        # Test 3: Sorting query
        print("\n3. Sorting Query (severity DESC)")
        def sorting_query():
            rules = Rule.query.filter_by(customer_id=1).order_by(
                Rule.severity.desc()
            ).limit(50).all()
            return len(rules)

        result = self.benchmark_query(sorting_query, iterations=50)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Queries/sec: {result['queries_per_sec']:.0f}")

        # Test 4: Count query
        print("\n4. Count Query")
        def count_query():
            return Rule.query.filter_by(customer_id=1).count()

        result = self.benchmark_query(count_query, iterations=50)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Queries/sec: {result['queries_per_sec']:.0f}")

        # Test 5: Settings query (frequently accessed)
        print("\n5. Settings Query (simulates frequent access)")
        # Create test settings
        setting = SystemSetting(
            category='test',
            data={'key': 'value'}
        )
        db.session.add(setting)
        db.session.commit()

        def settings_query():
            return SystemSetting.query.filter_by(category='test').first()

        result = self.benchmark_query(settings_query, iterations=100)
        print(f"   Average time: {result['avg_time_ms']:.2f}ms")
        print(f"   Queries/sec: {result['queries_per_sec']:.0f}")

    def test_database_stats(self):
        """Test database statistics"""
        print("\n" + "=" * 60)
        print("DATABASE STATISTICS")
        print("=" * 60)

        stats = get_database_stats(db.session)

        print(f"\nTable Row Counts:")
        for key, value in stats.items():
            if key.endswith('_count') and not key.startswith('database'):
                table_name = key.replace('_count', '')
                print(f"   {table_name}: {value}")

        if 'database_size_mb' in stats:
            print(f"\nDatabase Size: {stats['database_size_mb']} MB")

        if 'total_indexes' in stats:
            print(f"Total Indexes: {stats['total_indexes']}")

    def test_bulk_operations(self):
        """Test bulk operation performance"""
        print("\n" + "=" * 60)
        print("BULK OPERATIONS TEST")
        print("=" * 60)

        # Create a test customer
        customer = Customer(name='Bulk Test Customer')
        db.session.add(customer)
        db.session.commit()

        # Test 1: Standard insert
        print("\n1. Standard Insert (1000 rows)")
        start = time.time()
        for i in range(1000):
            rule = Rule(
                customer_id=customer.id,
                rule_id=f'bulk-rule-{i}',
                name=f'Bulk Rule {i}',
                severity=50,
                sig_id=f'99|{i}',
                xml_content=f'<rule id="{i}">test</rule>'
            )
            db.session.add(rule)
        db.session.commit()
        duration = time.time() - start
        print(f"   Time: {duration:.3f}s")
        print(f"   Rows/sec: {1000/duration:.0f}")

        # Clean up
        Rule.query.filter_by(customer_id=customer.id).delete()
        db.session.commit()

        # Test 2: Bulk insert
        print("\n2. Bulk Insert (1000 rows)")
        from utils.db_optimizer import optimize_bulk_insert

        data = [
            {
                'customer_id': customer.id,
                'rule_id': f'bulk-rule-{i}',
                'name': f'Bulk Rule {i}',
                'severity': 50,
                'sig_id': f'99|{i}',
                'xml_content': f'<rule id="{i}">test</rule>'
            }
            for i in range(1000)
        ]

        start = time.time()
        count = optimize_bulk_insert(db.session, Rule, data)
        duration = time.time() - start
        print(f"   Time: {duration:.3f}s")
        print(f"   Rows/sec: {count/duration:.0f}")
        print(f"   Speedup: {(1000/duration) / (1000/duration):.1f}x")


def main():
    parser = argparse.ArgumentParser(
        description='Database performance testing',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--test-cache', action='store_true', help='Test cache performance')
    parser.add_argument('--test-queries', action='store_true', help='Test query performance')
    parser.add_argument('--test-bulk', action='store_true', help='Test bulk operations')
    parser.add_argument('--test-stats', action='store_true', help='Show database statistics')
    parser.add_argument('--test-all', action='store_true', help='Run all tests')

    args = parser.parse_args()

    if not any([args.test_cache, args.test_queries, args.test_bulk, args.test_stats, args.test_all]):
        parser.print_help()
        return

    tester = PerformanceTest()

    try:
        if args.test_all or args.test_cache:
            tester.test_cache_performance()

        if args.test_all or args.test_queries:
            tester.test_query_performance()

        if args.test_all or args.test_bulk:
            tester.test_bulk_operations()

        if args.test_all or args.test_stats:
            tester.test_database_stats()

        print("\n" + "=" * 60)
        print("PERFORMANCE TESTING COMPLETE")
        print("=" * 60)

    finally:
        tester.cleanup()


if __name__ == '__main__':
    main()
