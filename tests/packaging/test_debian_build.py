# ClamUI Debian Build Tests
"""
Tests for Debian build script and package structure.

Tests cover:
- Version extraction from pyproject.toml
- Absolute import validation (blocks src.* imports)
- Launcher script correctness
- Package structure (FHS compliance)
- Control file validation

These tests prevent build regressions that would only surface in production.
"""

import re
import subprocess
from pathlib import Path

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestVersionExtraction:
    """Tests for version extraction from pyproject.toml."""

    def test_pyproject_exists(self):
        """Test that pyproject.toml exists."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml not found"

    def test_version_in_pyproject(self):
        """Test that version is defined in pyproject.toml."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        # Should have a version line
        assert re.search(r'^version\s*=\s*["\']', content, re.MULTILINE), (
            "version not defined in pyproject.toml"
        )

    def test_version_format_semantic(self):
        """Test version follows semantic versioning (X.Y.Z)."""
        pyproject = PROJECT_ROOT / "pyproject.toml"
        content = pyproject.read_text()

        # Extract version
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        assert match, "Could not extract version from pyproject.toml"

        version = match.group(1)
        # Should match X.Y.Z pattern (with optional pre-release)
        assert re.match(r"^\d+\.\d+\.\d+", version), (
            f"Version '{version}' doesn't follow semantic versioning"
        )

    def test_version_can_be_extracted_via_shell(self):
        """Test version can be extracted using grep/sed (as build script does)."""
        pyproject = PROJECT_ROOT / "pyproject.toml"

        # Same extraction method as build-deb.sh
        result = subprocess.run(
            ["grep", "-E", r"^version\s*=", str(pyproject)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, "grep failed to find version line"
        assert "version" in result.stdout


class TestAbsoluteImportValidation:
    """Tests for absolute import validation (blocks src.* imports)."""

    def test_no_absolute_src_imports_in_source(self):
        """Test no absolute src.* imports exist in src/ directory."""
        src_dir = PROJECT_ROOT / "src"

        # Find all Python files
        py_files = list(src_dir.rglob("*.py"))
        assert len(py_files) > 0, "No Python files found in src/"

        violations = []
        pattern = re.compile(r"^(from|import)\s+src\.", re.MULTILINE)

        for py_file in py_files:
            content = py_file.read_text()
            if pattern.search(content):
                violations.append(str(py_file.relative_to(PROJECT_ROOT)))

        assert len(violations) == 0, f"Found absolute src.* imports in: {violations}"

    def test_relative_imports_are_allowed(self):
        """Test relative imports (from ..core) are used correctly."""
        src_dir = PROJECT_ROOT / "src"

        # At least some files should use relative imports
        relative_pattern = re.compile(r"^from\s+\.", re.MULTILINE)

        files_with_relative = []
        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            if relative_pattern.search(content):
                files_with_relative.append(py_file.name)

        # Core modules should use relative imports
        assert len(files_with_relative) > 0, (
            "No relative imports found - expected in multi-module package"
        )


class TestLauncherScript:
    """Tests for the launcher script in debian/build-deb.sh."""

    def test_build_script_exists(self):
        """Test that build-deb.sh exists."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        assert build_script.exists(), "debian/build-deb.sh not found"

    def test_build_script_is_executable(self):
        """Test that build-deb.sh is executable."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        assert build_script.stat().st_mode & 0o100, "build-deb.sh is not executable"

    def test_launcher_uses_clamui_module(self):
        """Test launcher imports from clamui, not src."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        content = build_script.read_text()

        # The launcher script in build-deb.sh should use 'clamui.main'
        assert "clamui.main" in content, "Launcher should import from 'clamui.main', not 'src.main'"

        # Should NOT use src.main
        assert "src.main" not in content, "Launcher should NOT import from 'src.main'"


class TestPackageStructure:
    """Tests for Debian package structure (FHS compliance)."""

    def test_debian_directory_exists(self):
        """Test debian/ directory exists."""
        debian_dir = PROJECT_ROOT / "debian"
        assert debian_dir.is_dir(), "debian/ directory not found"

    def test_control_file_exists(self):
        """Test DEBIAN/control template exists."""
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        assert control.exists(), "debian/DEBIAN/control not found"

    def test_control_has_required_fields(self):
        """Test control file has required Debian fields."""
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        content = control.read_text()

        required_fields = [
            "Package:",
            "Version:",
            "Section:",
            "Priority:",
            "Architecture:",
            "Depends:",
            "Maintainer:",
            "Description:",
        ]

        for field in required_fields:
            assert field in content, f"Missing required field: {field}"

    def test_control_version_placeholder(self):
        """Test control file has VERSION placeholder."""
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        content = control.read_text()

        # Should have VERSION placeholder that gets substituted
        assert "Version: VERSION" in content or re.search(r"Version:\s*\d", content), (
            "Control file should have VERSION placeholder or actual version"
        )

    def test_package_name_is_clamui(self):
        """Test package name in control is 'clamui'."""
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        content = control.read_text()

        assert "Package: clamui" in content, "Package name should be 'clamui'"

    def test_architecture_is_all(self):
        """Test architecture is 'all' (pure Python)."""
        control = PROJECT_ROOT / "debian" / "DEBIAN" / "control"
        content = control.read_text()

        assert "Architecture: all" in content, (
            "Architecture should be 'all' for pure Python package"
        )

    def test_build_script_installs_dolphin_service_menus_to_kio_and_legacy_paths(self):
        """Test Debian build script packages Dolphin service menus for KDE6 and KDE5."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        content = build_script.read_text()

        assert "/usr/share/kio/servicemenus" in content
        assert "/usr/share/kservices5/ServiceMenus" in content


class TestMaintainerScripts:
    """Tests for Debian maintainer scripts."""

    def test_postinst_exists(self):
        """Test postinst script exists."""
        postinst = PROJECT_ROOT / "debian" / "DEBIAN" / "postinst"
        assert postinst.exists(), "debian/DEBIAN/postinst not found"

    def test_postinst_is_valid_shell(self):
        """Test postinst is valid shell script."""
        postinst = PROJECT_ROOT / "debian" / "DEBIAN" / "postinst"
        content = postinst.read_text()

        # Should start with shebang
        assert content.startswith("#!/"), "postinst should start with shebang"

    def test_prerm_exists(self):
        """Test prerm script exists."""
        prerm = PROJECT_ROOT / "debian" / "DEBIAN" / "prerm"
        assert prerm.exists(), "debian/DEBIAN/prerm not found"

    def test_postrm_exists(self):
        """Test postrm script exists."""
        postrm = PROJECT_ROOT / "debian" / "DEBIAN" / "postrm"
        assert postrm.exists(), "debian/DEBIAN/postrm not found"

    @pytest.mark.skipif(
        subprocess.run(["which", "bash"], capture_output=True).returncode != 0,
        reason="bash not available",
    )
    def test_maintainer_scripts_syntax_valid(self):
        """Test maintainer scripts have valid shell syntax."""
        scripts = ["postinst", "prerm", "postrm"]
        debian_dir = PROJECT_ROOT / "debian" / "DEBIAN"

        for script_name in scripts:
            script = debian_dir / script_name
            if script.exists():
                result = subprocess.run(
                    ["bash", "-n", str(script)],
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0, f"{script_name} has syntax errors: {result.stderr}"


class TestExcludesPycache:
    """Tests for __pycache__ exclusion."""

    def test_build_script_excludes_pycache(self):
        """Test build script excludes __pycache__ directories."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        content = build_script.read_text()

        # Should exclude __pycache__
        assert "__pycache__" in content, "Build script should handle __pycache__ exclusion"

    def test_build_script_excludes_pyc_files(self):
        """Test build script excludes .pyc files."""
        build_script = PROJECT_ROOT / "debian" / "build-deb.sh"
        content = build_script.read_text()

        # Should exclude .pyc files
        assert ".pyc" in content, "Build script should handle .pyc file exclusion"
