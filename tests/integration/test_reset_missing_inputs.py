"""
reset_database.main() with missing optional inputs.

Data inputs are optional: a deployment may provide any subset of
spider_data/, container_data/, and software.csv. A configured-but-missing
location must be skipped with a warning, never crash the reset — a
CSV-only deployment is the minimal real-world case, and run.py always
passes default paths for all inputs whether they exist or not.
"""
import sys

import pytest

import reset_database
from app.models.software import Software
from app.models.software_edit import SoftwareEdit

CSV_CONTENT = (
    "software,resource,software_versions,software_description\n"
    "pytorch,gpu_cluster,2.0.1,PyTorch ML framework\n"
)


@pytest.fixture
def run_reset(databases, tmp_path, monkeypatch):
    """Run reset_database.main() sandboxed under tmp_path."""
    monkeypatch.setenv("SDS_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data" / "state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        reset_database, "LAST_UPDATED_PATH", str(tmp_path / "last_updated.txt")
    )

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["reset_database.py", *argv])
        reset_database.main()

    return run


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "software.csv"
    path.write_text(CSV_CONTENT)
    return path


@pytest.mark.parametrize("flag", ["-s_d", "-c_d"])
def test_missing_dir_is_skipped_and_csv_still_ingested(run_reset, csv_file, tmp_path, flag):
    run_reset(flag, str(tmp_path / "does_not_exist"), "-csv_f", str(csv_file))

    assert Software.get_or_none(Software.software_name == "pytorch") is not None


def test_missing_csv_file_is_skipped(run_reset, tmp_path):
    run_reset("-csv_f", str(tmp_path / "does_not_exist.csv"))

    assert Software.select().count() == 0


def test_all_inputs_missing_completes_with_empty_db(run_reset, tmp_path):
    # The shape run.py produces on a bare deployment: every flag passed,
    # nothing on disk.
    run_reset(
        "-s_d", str(tmp_path / "no_spider"),
        "-c_d", str(tmp_path / "no_containers"),
        "-csv_f", str(tmp_path / "no.csv"),
    )

    assert Software.select().count() == 0


def test_no_input_flags_at_all_exits(run_reset):
    # Direct CLI misuse (no flags) still fails fast with the help hint.
    with pytest.raises(SystemExit):
        run_reset()


def test_software_uses_defaults_to_data_dir(run_reset, csv_file, tmp_path):
    uses = tmp_path / "data" / "software_uses"
    uses.mkdir()
    (uses / "pytorch.md").write_text("# Run it\nuse pytorch like this")

    run_reset("-csv_f", str(csv_file))

    edit = SoftwareEdit.get(SoftwareEdit.software_name == "pytorch")
    assert "use pytorch like this" in edit.ai_example_use


def test_explicit_missing_software_uses_dir_is_skipped(run_reset, csv_file, tmp_path):
    run_reset(
        "-csv_f", str(csv_file),
        "-s_u_d", str(tmp_path / "no_uses_here"),
    )

    assert Software.get_or_none(Software.software_name == "pytorch") is not None
