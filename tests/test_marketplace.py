"""
Tests for Plugin Marketplace system
"""

from datetime import datetime

import pytest

from core.marketplace.marketplace import (PluginCategory, PluginMarketplace,
                                          PluginMetadata, PluginRating,
                                          PluginVersion, SecurityLevel,
                                          SecurityScan)


@pytest.fixture
def marketplace():
    """Create test marketplace"""
    return PluginMarketplace()


@pytest.fixture
def sample_plugin():
    """Create sample plugin metadata"""
    return PluginMetadata(
        id="test-plugin",
        name="Test Plugin",
        author="test-author",
        author_email="test@example.com",
        description="A test plugin",
        long_description="A longer description",
        category=PluginCategory.TOOL,
        version="1.0.0",
        homepage="https://example.com",
        repository="https://github.com/test/test",
        keywords=["test", "example"],
        published_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )


class TestPluginMarketplace:
    """Test marketplace core functionality"""

    def test_register_plugin(self, marketplace, sample_plugin):
        """Test plugin registration"""
        success = marketplace.register_plugin(sample_plugin)
        assert success
        assert sample_plugin.id in marketplace.plugins

    def test_duplicate_registration(self, marketplace, sample_plugin):
        """Test duplicate registration fails"""
        marketplace.register_plugin(sample_plugin)
        success = marketplace.register_plugin(sample_plugin)
        assert not success

    def test_get_plugin(self, marketplace, sample_plugin):
        """Test plugin retrieval"""
        marketplace.register_plugin(sample_plugin)
        plugin = marketplace.get_plugin(sample_plugin.id)
        assert plugin is not None
        assert plugin.name == "Test Plugin"

    def test_get_nonexistent_plugin(self, marketplace):
        """Test getting nonexistent plugin"""
        plugin = marketplace.get_plugin("nonexistent")
        assert plugin is None

    def test_update_plugin(self, marketplace, sample_plugin):
        """Test plugin update"""
        marketplace.register_plugin(sample_plugin)
        sample_plugin.name = "Updated Plugin"
        success = marketplace.update_plugin(sample_plugin.id, sample_plugin)
        assert success
        assert marketplace.get_plugin(sample_plugin.id).name == "Updated Plugin"


class TestPluginSearch:
    """Test marketplace search functionality"""

    def test_search_by_keyword(self, marketplace, sample_plugin):
        """Test searching by keyword"""
        marketplace.register_plugin(sample_plugin)
        results = marketplace.search("test")
        assert len(results) > 0
        assert sample_plugin.id in [p.id for p in results]

    def test_search_by_name(self, marketplace, sample_plugin):
        """Test searching by plugin name"""
        marketplace.register_plugin(sample_plugin)
        results = marketplace.search("Test Plugin")
        assert len(results) > 0
        assert sample_plugin.id in [p.id for p in results]

    def test_search_by_category(self, marketplace, sample_plugin):
        """Test filtering by category"""
        marketplace.register_plugin(sample_plugin)
        results = marketplace.search("test", category=PluginCategory.TOOL)
        assert len(results) > 0
        assert all(p.category == PluginCategory.TOOL for p in results)

    def test_search_with_sorting(self, marketplace):
        """Test search with different sort orders"""
        plugin1 = PluginMetadata(
            id="plugin-1",
            name="Plugin One",
            author="author1",
            author_email="a@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            downloads_total=100,
            rating_average=4.5,
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        plugin2 = PluginMetadata(
            id="plugin-2",
            name="Plugin Two",
            author="author2",
            author_email="b@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            downloads_total=50,
            rating_average=5.0,
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        marketplace.register_plugin(plugin1)
        marketplace.register_plugin(plugin2)

        # Sort by downloads
        results = marketplace.search("plugin", sort_by="downloads")
        assert results[0].id == "plugin-1"

        # Sort by rating
        results = marketplace.search("plugin", sort_by="rating")
        assert results[0].id == "plugin-2"

    def test_search_with_pagination(self, marketplace):
        """Test search pagination"""
        for i in range(25):
            plugin = PluginMetadata(
                id=f"plugin-{i}",
                name=f"Test Plugin {i}",
                author=f"author-{i}",
                author_email=f"a{i}@example.com",
                description="Test",
                long_description="",
                category=PluginCategory.TOOL,
                version="1.0.0",
                published_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            marketplace.register_plugin(plugin)

        page1 = marketplace.search("test", limit=10, offset=0)
        page2 = marketplace.search("test", limit=10, offset=10)

        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].id != page2[0].id


class TestPluginRatings:
    """Test plugin rating system"""

    def test_add_rating(self, marketplace, sample_plugin):
        """Test adding a rating"""
        marketplace.register_plugin(sample_plugin)
        rating = PluginRating(
            user_id="user-1",
            rating=5,
            review="Great plugin!",
            timestamp=datetime.utcnow().isoformat(),
        )
        success = marketplace.add_rating(sample_plugin.id, rating)
        assert success

    def test_rating_average(self, marketplace, sample_plugin):
        """Test rating average calculation"""
        marketplace.register_plugin(sample_plugin)

        ratings = [5, 4, 3, 4, 5]
        for i, r in enumerate(ratings):
            rating = PluginRating(
                user_id=f"user-{i}",
                rating=r,
                review="",
                timestamp=datetime.utcnow().isoformat(),
            )
            marketplace.add_rating(sample_plugin.id, rating)

        plugin = marketplace.get_plugin(sample_plugin.id)
        expected_avg = sum(ratings) / len(ratings)
        assert plugin.rating_average == expected_avg

    def test_invalid_rating_value(self, marketplace, sample_plugin):
        """Test that invalid rating values are rejected"""
        marketplace.register_plugin(sample_plugin)
        rating = PluginRating(
            user_id="user-1",
            rating=10,  # Invalid: > 5
            review="",
            timestamp=datetime.utcnow().isoformat(),
        )
        success = marketplace.add_rating(sample_plugin.id, rating)
        assert not success


class TestPluginVersions:
    """Test plugin version management"""

    def test_version_compatibility(self, sample_plugin):
        """Test version compatibility checking"""
        v1 = PluginVersion(
            version="1.0.0",
            release_date=datetime.utcnow().isoformat(),
            size_bytes=1000,
            min_bael_version="2.0.0",
        )
        v2 = PluginVersion(
            version="2.0.0",
            release_date=datetime.utcnow().isoformat(),
            size_bytes=2000,
            min_bael_version="2.1.0",
        )

        sample_plugin.versions = [v1, v2]

        # Check compatibility
        compatible = sample_plugin.get_compatible_versions("2.1.0")
        assert len(compatible) == 2

        compatible = sample_plugin.get_compatible_versions("2.0.5")
        assert len(compatible) == 1
        assert compatible[0].version == "1.0.0"

    def test_breaking_changes_tracking(self, sample_plugin):
        """Test breaking changes documentation"""
        version = PluginVersion(
            version="2.0.0",
            release_date=datetime.utcnow().isoformat(),
            size_bytes=2000,
            breaking_changes=["API changed", "Config format changed"],
        )

        assert "API changed" in version.breaking_changes


class TestPluginDiscovery:
    """Test plugin discovery features"""

    def test_featured_plugins(self, marketplace):
        """Test getting featured plugins"""
        plugin1 = PluginMetadata(
            id="featured-1",
            name="Featured Plugin 1",
            author="author1",
            author_email="a@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            featured=True,
            downloads_total=1000,
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        plugin2 = PluginMetadata(
            id="featured-2",
            name="Featured Plugin 2",
            author="author2",
            author_email="b@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            featured=True,
            downloads_total=500,
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        marketplace.register_plugin(plugin1)
        marketplace.register_plugin(plugin2)

        featured = marketplace.get_featured(limit=10)
        assert len(featured) == 2
        assert featured[0].id == "featured-1"  # Sorted by downloads

    def test_trending_plugins(self, marketplace):
        """Test getting trending plugins"""
        for i in range(5):
            plugin = PluginMetadata(
                id=f"trending-{i}",
                name=f"Trending {i}",
                author=f"author-{i}",
                author_email=f"a{i}@example.com",
                description="Test",
                long_description="",
                category=PluginCategory.TOOL,
                version="1.0.0",
                downloads_total=1000 - (i * 100),
                published_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            marketplace.register_plugin(plugin)

        trending = marketplace.get_trending(limit=5)
        assert len(trending) == 5
        assert trending[0].downloads_total > trending[1].downloads_total

    def test_recommendations(self, marketplace):
        """Test plugin recommendations"""
        for i in range(5):
            plugin = PluginMetadata(
                id=f"rec-{i}",
                name=f"Recommended {i}",
                author=f"author-{i}",
                author_email=f"a{i}@example.com",
                description="Test",
                long_description="",
                category=PluginCategory.TOOL,
                version="1.0.0",
                downloads_total=100 * (i + 1),
                rating_average=4.0 + (i * 0.1),
                rating_count=50 + (i * 10),
                published_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            marketplace.register_plugin(plugin)

        recommendations = marketplace.get_recommendations(limit=5)
        assert len(recommendations) > 0


class TestPluginSecurity:
    """Test security scanning and verification"""

    def test_security_scan(self, marketplace, sample_plugin):
        """Test security scanning"""
        marketplace.register_plugin(sample_plugin)

        scan = SecurityScan(
            timestamp=datetime.utcnow().isoformat(),
            level=SecurityLevel.LOW,
            issues=[],
            permissions_requested={"network", "filesystem"},
            dependencies_audited=True,
            malware_check=True,
        )

        success = marketplace.scan_security(sample_plugin.id, scan)
        assert success

        plugin = marketplace.get_plugin(sample_plugin.id)
        assert plugin.security_scan.level == SecurityLevel.LOW

    def test_author_verification(self, marketplace):
        """Test author verification"""
        plugin1 = PluginMetadata(
            id="verified-1",
            name="Plugin 1",
            author="verified-author",
            author_email="v@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
        plugin2 = PluginMetadata(
            id="verified-2",
            name="Plugin 2",
            author="verified-author",
            author_email="v@example.com",
            description="Test",
            long_description="",
            category=PluginCategory.TOOL,
            version="1.0.0",
            published_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        marketplace.register_plugin(plugin1)
        marketplace.register_plugin(plugin2)

        marketplace.verify_author("verified-author")

        assert marketplace.get_plugin("verified-1").verified_author
        assert marketplace.get_plugin("verified-2").verified_author

    def test_trust_plugin(self, marketplace, sample_plugin):
        """Test plugin trust marking"""
        marketplace.register_plugin(sample_plugin)

        success = marketplace.trust_plugin(sample_plugin.id)
        assert success

        plugin = marketplace.get_plugin(sample_plugin.id)
        assert plugin.trusted


class TestMarketplaceStatistics:
    """Test marketplace statistics"""

    def test_get_statistics(self, marketplace):
        """Test statistics calculation"""
        for i in range(3):
            plugin = PluginMetadata(
                id=f"stat-{i}",
                name=f"Stat Plugin {i}",
                author=f"author-{i}",
                author_email=f"a{i}@example.com",
                description="Test",
                long_description="",
                category=PluginCategory.TOOL,
                version="1.0.0",
                downloads_total=100 * (i + 1),
                trusted=i == 0,  # First one is trusted
                published_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
            )
            marketplace.register_plugin(plugin)

        stats = marketplace.get_statistics()
        assert stats["total_plugins"] == 3
        assert stats["active_plugins"] == 3
        assert stats["total_downloads"] == 600  # 100 + 200 + 300
        assert stats["trusted_plugins"] == 1

    def test_export_catalog(self, marketplace, sample_plugin):
        """Test catalog export"""
        marketplace.register_plugin(sample_plugin)

        catalog = marketplace.export_catalog()
        assert "version" in catalog
        assert "generated_at" in catalog
        assert "plugins" in catalog
        assert "statistics" in catalog
        assert sample_plugin.id in catalog["plugins"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
