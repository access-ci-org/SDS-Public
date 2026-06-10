"""
Container parser pure functions:
- is_valid_package: heuristic for whether an extracted token is a real package name
- extract_SDS_software: legacy `## SDS Software` comment block
- extract_SDS_software_v1: `## SDS Software v1` YAML block
- extract_packages_strings: auto-extraction from RUN / %post commands
"""
import pytest

from parsers.container.parse_containers import (
    extract_SDS_software,
    extract_SDS_software_v1,
    extract_packages_strings,
    is_valid_package,
)


# ---- is_valid_package ----

class TestIsValidPackage:
    def test_valid_alpha_name(self):
        assert is_valid_package("numpy")

    def test_valid_with_version(self):
        assert is_valid_package("pytorch-2.0.1")

    def test_empty_string_rejected(self):
        assert not is_valid_package("")

    def test_starts_with_dash_rejected(self):
        assert not is_valid_package("-flag")

    def test_starts_with_dot_rejected(self):
        assert not is_valid_package(".hidden")

    def test_no_alpha_chars_rejected(self):
        assert not is_valid_package("12345")

    def test_just_version_number_rejected(self):
        assert not is_valid_package("1.2.3")

    def test_numeric_underscore_prefix_rejected(self):
        assert not is_valid_package("1_2_3_name")


# ---- extract_SDS_software (legacy block) ----

class TestExtractSDSSoftware:
    def test_extracts_def_file(self, fixture_path):
        content = fixture_path("containers/legacy.def").read_text()
        _, container_file, def_file = extract_SDS_software(content)
        assert def_file == "lcc/legacy.def"

    def test_extracts_container_file(self, fixture_path):
        content = fixture_path("containers/legacy.def").read_text()
        _, container_file, _ = extract_SDS_software(content)
        assert container_file == "lcc/legacy.sif"

    def test_extracts_software_entries_with_commands(self, fixture_path):
        content = fixture_path("containers/legacy.def").read_text()
        sw, _, _ = extract_SDS_software(content)
        # pytorch and scipy each have a command; numpy/1.24.0 has no command
        names = [entry[0] for entry in sw]
        assert "pytorch" in names
        assert "scipy/1.10.0" in names

    def test_extracts_software_entry_without_command(self, fixture_path):
        content = fixture_path("containers/legacy.def").read_text()
        sw, _, _ = extract_SDS_software(content)
        numpy_entry = next(e for e in sw if e[0] == "numpy/1.24.0")
        assert numpy_entry[1] == ""

    def test_no_sds_block_returns_empty(self):
        content = "FROM ubuntu\nRUN echo hi\n"
        sw, container_file, def_file = extract_SDS_software(content)
        assert sw == []
        assert container_file == ""
        assert def_file == ""


# ---- extract_SDS_software_v1 (YAML block) ----

class TestExtractSDSSoftwareV1:
    def test_extracts_def_and_container_files(self, fixture_path):
        content = fixture_path("containers/v1.def").read_text()
        _, container_file, def_file = extract_SDS_software_v1(content)
        assert container_file == "lcc/v1.sif"
        assert def_file == "lcc/v1.def"

    def test_extracts_software_with_versions(self, fixture_path):
        content = fixture_path("containers/v1.def").read_text()
        sw, _, _ = extract_SDS_software_v1(content)
        keys = [entry[0] for entry in sw]
        assert "pytorch/2.0.1" in keys
        assert "pytorch/1.13.1" in keys
        assert "numpy/1.24.0" in keys

    def test_extracts_command_per_version(self, fixture_path):
        content = fixture_path("containers/v1.def").read_text()
        sw, _, _ = extract_SDS_software_v1(content)
        pytorch_201 = next(e for e in sw if e[0] == "pytorch/2.0.1")
        assert pytorch_201[1] == "module load pytorch/2.0.1"

    def test_no_v1_block_returns_empty_tuple(self):
        content = "FROM ubuntu\nRUN echo hi\n"
        sw, container_file, def_file = extract_SDS_software_v1(content)
        assert sw == []
        assert container_file == ""
        assert def_file == ""

    def test_malformed_yaml_raises(self):
        content = (
            "## SDS Software v1\n"
            "# sds_software:\n"
            "#   invalid: : : yaml\n"
            "# --- END SDS Software ---\n"
        )
        with pytest.raises(ValueError):
            extract_SDS_software_v1(content)


# ---- extract_packages_strings (auto-extraction) ----

class TestExtractPackagesStrings:
    def test_extracts_apt_get_install(self):
        content = "%post\n  apt-get install -y python3 vim\n"
        out = extract_packages_strings(content)
        assert "python3" in out or "vim" in out

    def test_extracts_pip_install(self):
        content = "%post\n  pip install numpy pandas\n"
        out = extract_packages_strings(content)
        assert any(pkg in out for pkg in ("numpy", "pandas"))

    def test_extracts_conda_install(self):
        content = "%post\n  conda install -c conda-forge scipy\n"
        out = extract_packages_strings(content)
        assert "scipy" in out

    def test_no_install_commands_returns_empty(self):
        content = "%post\n  echo hello world\n"
        out = extract_packages_strings(content)
        assert out == []
