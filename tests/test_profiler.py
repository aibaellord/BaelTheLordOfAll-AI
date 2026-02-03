"""
Unit tests for core.performance.profiler module
"""

import asyncio
import time
from pathlib import Path

import pytest

from core.performance.profiler import (PerformanceMetrics, PerformanceProfiler,
                                       ProfileResult, profile_cpu,
                                       profile_section, profile_time)


class TestProfileDecorators:
    """Test performance profiling decorators"""

    @pytest.mark.asyncio
    async def test_profile_time_async(self):
        """Test @profile_time decorator with async function"""

        @profile_time("test_async")
        async def async_function(duration: float):
            await asyncio.sleep(duration)
            return "done"

        result = await async_function(0.1)

        assert result == "done"

        # Check metrics were recorded
        metrics = PerformanceProfiler.get_metrics()
        assert "test_async" in metrics.call_counts
        assert metrics.call_counts["test_async"] == 1
        assert metrics.total_times["test_async"] >= 0.1

    def test_profile_time_sync(self):
        """Test @profile_time decorator with sync function"""

        @profile_time("test_sync")
        def sync_function(duration: float):
            time.sleep(duration)
            return "done"

        result = sync_function(0.05)

        assert result == "done"

        metrics = PerformanceProfiler.get_metrics()
        assert "test_sync" in metrics.call_counts
        assert metrics.call_counts["test_sync"] >= 1
        assert metrics.total_times["test_sync"] >= 0.05

    def test_profile_time_with_error(self):
        """Test profiler handles exceptions correctly"""

        @profile_time("test_error")
        def error_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_function()

        # Metrics should still be recorded
        metrics = PerformanceProfiler.get_metrics()
        assert "test_error" in metrics.call_counts

    def test_profile_cpu(self):
        """Test @profile_cpu decorator"""

        @profile_cpu("cpu_test")
        def cpu_intensive():
            # Simulate CPU work
            total = 0
            for i in range(100000):
                total += i * i
            return total

        result = cpu_intensive()
        assert result > 0

        metrics = PerformanceProfiler.get_metrics()
        assert "cpu_test" in metrics.call_counts


class TestProfileSection:
    """Test profile_section context manager"""

    @pytest.mark.asyncio
    async def test_profile_section_basic(self):
        """Test basic profiling section"""

        async with profile_section("section_test"):
            await asyncio.sleep(0.05)

        metrics = PerformanceProfiler.get_metrics()
        assert "section_test" in metrics.call_counts
        assert metrics.call_counts["section_test"] == 1
        assert metrics.total_times["section_test"] >= 0.05

    @pytest.mark.asyncio
    async def test_profile_section_nested(self):
        """Test nested profiling sections"""

        async with profile_section("outer"):
            await asyncio.sleep(0.02)

            async with profile_section("inner"):
                await asyncio.sleep(0.02)

            await asyncio.sleep(0.02)

        metrics = PerformanceProfiler.get_metrics()
        assert "outer" in metrics.call_counts
        assert "inner" in metrics.call_counts
        assert metrics.total_times["outer"] >= 0.06
        assert metrics.total_times["inner"] >= 0.02

    @pytest.mark.asyncio
    async def test_profile_section_with_error(self):
        """Test profiling section with exception"""

        with pytest.raises(RuntimeError):
            async with profile_section("error_section"):
                raise RuntimeError("Test error")

        # Metrics should still be recorded
        metrics = PerformanceProfiler.get_metrics()
        assert "error_section" in metrics.call_counts


class TestPerformanceMetrics:
    """Test PerformanceMetrics class"""

    def test_record_call(self):
        """Test recording call metrics"""

        metrics = PerformanceMetrics()
        metrics.record_call("test_func", 0.5)

        assert metrics.call_counts["test_func"] == 1
        assert metrics.total_times["test_func"] == 0.5
        assert metrics.average_times["test_func"] == 0.5

    def test_record_multiple_calls(self):
        """Test recording multiple calls"""

        metrics = PerformanceMetrics()
        metrics.record_call("test_func", 0.5)
        metrics.record_call("test_func", 1.0)
        metrics.record_call("test_func", 1.5)

        assert metrics.call_counts["test_func"] == 3
        assert metrics.total_times["test_func"] == 3.0
        assert metrics.average_times["test_func"] == 1.0

    def test_get_hotspots(self):
        """Test identifying performance hotspots"""

        metrics = PerformanceMetrics()
        metrics.record_call("fast_func", 0.01)
        metrics.record_call("slow_func", 2.0)
        metrics.record_call("medium_func", 0.5)

        hotspots = metrics.get_hotspots(top_n=2)

        assert len(hotspots) == 2
        assert hotspots[0][0] == "slow_func"
        assert hotspots[1][0] == "medium_func"

    def test_get_summary(self):
        """Test metrics summary generation"""

        metrics = PerformanceMetrics()
        metrics.record_call("func1", 0.5)
        metrics.record_call("func2", 1.0)

        summary = metrics.get_summary()

        assert summary["total_calls"] == 2
        assert summary["total_time"] == 1.5
        assert "functions" in summary
        assert len(summary["functions"]) == 2


class TestPerformanceProfiler:
    """Test PerformanceProfiler singleton"""

    def test_singleton(self):
        """Test PerformanceProfiler is singleton"""

        profiler1 = PerformanceProfiler()
        profiler2 = PerformanceProfiler()

        assert profiler1 is profiler2

    def test_start_stop_profiling(self):
        """Test starting and stopping profiling"""

        profiler = PerformanceProfiler()

        # Start profiling
        profiler.start("test_op")
        time.sleep(0.05)
        result = profiler.stop("test_op")

        assert isinstance(result, ProfileResult)
        assert result.name == "test_op"
        assert result.duration >= 0.05

    def test_get_metrics(self):
        """Test getting current metrics"""

        profiler = PerformanceProfiler()
        metrics = profiler.get_metrics()

        assert isinstance(metrics, PerformanceMetrics)
        assert hasattr(metrics, "call_counts")
        assert hasattr(metrics, "total_times")

    def test_clear_metrics(self):
        """Test clearing metrics"""

        profiler = PerformanceProfiler()

        # Record some metrics
        profiler.start("test")
        profiler.stop("test")

        metrics_before = profiler.get_metrics()
        assert len(metrics_before.call_counts) > 0

        # Clear metrics
        profiler.clear()

        metrics_after = profiler.get_metrics()
        assert len(metrics_after.call_counts) == 0

    @pytest.mark.asyncio
    async def test_export_report(self):
        """Test exporting profiling report"""

        profiler = PerformanceProfiler()

        # Generate some data
        @profile_time("export_test")
        async def test_func():
            await asyncio.sleep(0.01)

        await test_func()

        # Export report
        report_path = Path("/tmp/test_profile_report.json")
        await profiler.export_report(report_path)

        assert report_path.exists()

        # Cleanup
        report_path.unlink()


class TestIntegration:
    """Integration tests for profiling system"""

    @pytest.mark.asyncio
    async def test_multiple_operations(self):
        """Test profiling multiple operations"""

        @profile_time("op1")
        async def operation1():
            await asyncio.sleep(0.01)
            return "op1"

        @profile_time("op2")
        async def operation2():
            await asyncio.sleep(0.02)
            return "op2"

        @profile_time("op3")
        async def operation3():
            await asyncio.sleep(0.03)
            return "op3"

        # Run operations
        results = await asyncio.gather(
            operation1(),
            operation2(),
            operation3()
        )

        assert results == ["op1", "op2", "op3"]

        # Check metrics
        metrics = PerformanceProfiler.get_metrics()
        assert "op1" in metrics.call_counts
        assert "op2" in metrics.call_counts
        assert "op3" in metrics.call_counts

        # Check hotspots
        hotspots = metrics.get_hotspots(top_n=3)
        assert len(hotspots) == 3
        assert hotspots[0][0] == "op3"  # Slowest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
