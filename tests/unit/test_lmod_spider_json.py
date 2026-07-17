"""
get_software_info_json parses `spider -o jsonSoftwarePage` dumps into
{name, description, url, versions} records where each version carries its
full module name and every load chain (parent modules) that reaches it.
Names and version keys go through the same user-configurable rules as the
text parser.
"""
import json

import pytest

from parsers.lmod.parse_spider import get_software_info
from parsers.lmod.parse_spider_json import get_software_info_json, is_hidden_module


@pytest.fixture
def parsed(fixture_path):
    return get_software_info_json(fixture_path("spider/json_software_page.json"))


def _entry(parsed, name):
    return next(e for e in parsed if e["name"] == name)


def test_packages_parsed(parsed):
    names = {e["name"] for e in parsed}
    assert {
        "proj", "slurmtools", "antlr", "bcftools", "parmetis", "mytool",
        "secrettool",
    } <= names


def test_package_description_used(parsed):
    proj = _entry(parsed, "proj")
    assert "Cartesian coordinates" in proj["description"]


def test_description_falls_back_to_version_level(parsed):
    # slurmtools has no package-level description, only a version-level one
    slurmtools = _entry(parsed, "slurmtools")
    assert "SLURM" in slurmtools["description"]


def test_no_description_anywhere_yields_empty(parsed):
    bcftools = _entry(parsed, "bcftools")
    assert bcftools["description"] == ""


def test_package_url_carried(parsed):
    assert _entry(parsed, "proj")["url"] == "https://example.org/proj"


def test_no_url_yields_empty(parsed):
    assert _entry(parsed, "bcftools")["url"] == ""


def test_entries_merge_by_full_module_name(parsed):
    # proj/8.1.1 appears once per toolchain in the raw dump; the record
    # merges them into one version with one chain per toolchain
    proj = _entry(parsed, "proj")
    v = proj["versions"]["8.1.1"]
    assert v["full"] == "proj/8.1.1"
    parents = [c["parents"] for c in v["chains"]]
    assert ["gcc/11.2.0"] in parents
    assert ["gcc/10.3.0"] in parents
    assert ["aocc/3.1.0"] in parents
    assert ["intel/.2021.4.0"] in parents
    assert len(v["chains"]) == 4


def test_chain_through_hidden_module_is_flagged(parsed):
    proj = _entry(parsed, "proj")
    chains = proj["versions"]["8.1.1"]["chains"]
    hidden_flags = {tuple(c["parents"]): c["hidden"] for c in chains}
    assert hidden_flags[("intel/.2021.4.0",)] is True
    assert hidden_flags[("gcc/11.2.0",)] is False


def test_multi_level_chain_preserves_load_order(parsed):
    parmetis = _entry(parsed, "parmetis")
    parents = [c["parents"] for c in parmetis["versions"]["4.0.3"]["chains"]]
    assert ["gcc/12.3.0", "openmpi/4.1.6"] in parents
    assert ["gcc/12.3.0", "mpich/4.1.2"] in parents


def test_no_parent_yields_single_direct_chain(parsed):
    antlr = _entry(parsed, "antlr")
    chains = antlr["versions"]["4.13.1"]["chains"]
    assert chains == [{"parents": [], "hidden": False}]


def test_versionless_modulefile_keyed_by_module_name(parsed):
    # matches the text parser: a full with no '/' keeps the module name
    slurmtools = _entry(parsed, "slurmtools")
    assert "slurmtools" in slurmtools["versions"]
    assert slurmtools["versions"]["slurmtools"]["full"] == "slurmtools"


def test_version_derived_from_full_not_display_name(parsed):
    # versionName can be a display string; the key comes from full
    mytool = _entry(parsed, "mytool")
    assert "2022.4" in mytool["versions"]
    assert "MyTool 2022.4 & Python 3.10" not in mytool["versions"]


def test_shared_display_name_keeps_distinct_modules(parsed):
    # two modulefiles share versionName "2024.1 Standard"; full-derived
    # keys must keep both instead of collapsing to the first
    mytool = _entry(parsed, "mytool")
    assert "2024.1_standard" in mytool["versions"]
    assert "2024.1_standard_ext" in mytool["versions"]
    assert mytool["versions"]["2024.1_standard_ext"]["full"] == "mytool/2024.1_standard_ext"


def test_boolean_default_version_tolerated(parsed):
    # slurmtools has "defaultVersionName": false in the dump; parsing must
    # not choke on the non-string value
    assert _entry(parsed, "slurmtools")


def test_hidden_version_skipped(parsed):
    secrettool = _entry(parsed, "secrettool")
    assert "2.0" in secrettool["versions"]
    assert ".1.0" not in secrettool["versions"]


def test_fully_hidden_package_dropped(parsed):
    names = {e["name"] for e in parsed}
    assert "ghostpkg" not in names


def _write_dump(tmp_path, data):
    dump = tmp_path / "dump.json"
    dump.write_text(json.dumps(data))
    return dump


def test_url_whitespace_stripped(tmp_path):
    dump = _write_dump(
        tmp_path,
        [{
            "package": "tool",
            "url": "  https://example.org/tool  ",
            "versions": [{"full": "tool/1.0"}],
        }],
    )

    parsed = get_software_info_json(dump)

    assert parsed[0]["url"] == "https://example.org/tool"


def test_user_version_cleaner_applies(tmp_path):
    dump = _write_dump(
        tmp_path,
        [{"package": "tool", "versions": [{"full": "tool/os8-2.5"}]}],
    )

    parsed = get_software_info_json(dump, version_cleaner=r"-")

    versions = parsed[0]["versions"]
    assert "2.5" in versions
    assert versions["2.5"]["full"] == "tool/os8-2.5"


def test_custom_hook_applies(tmp_path):
    dump = _write_dump(
        tmp_path,
        [{"package": "tool", "versions": [{"full": "tool/1.0", "parent": [["gcc/12.3.0"]]}]}],
    )

    def hook(name, versions, software_info):
        return "renamed", versions, software_info

    parsed = get_software_info_json(dump, custom_name_version_parser=hook)

    assert parsed[0]["name"] == "renamed"
    # cleaning still runs after the hook, and chains stay attached
    assert parsed[0]["versions"]["1.0"]["chains"] == [
        {"parents": ["gcc/12.3.0"], "hidden": False}
    ]


def test_text_and_json_derive_identical_names_and_versions(tmp_path):
    # the same modules through both parsers, under a custom rule, must
    # yield the same software name and version keys
    text_file = tmp_path / "dump.txt"
    text_file.write_text("  tool: tool/os8-2.5, tool/os8-3.1\n")
    dump = _write_dump(
        tmp_path,
        [{"package": "tool", "versions": [
            {"full": "tool/os8-2.5"}, {"full": "tool/os8-3.1"},
        ]}],
    )

    from_text = get_software_info(text_file, version_cleaner=r"-")
    from_json = get_software_info_json(dump, version_cleaner=r"-")

    assert from_text[0]["name"] == from_json[0]["name"]
    assert set(from_text[0]["versions"]) == set(from_json[0]["versions"]) == {"2.5", "3.1"}


def test_non_array_json_raises_value_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"not": "an array"}')
    with pytest.raises(ValueError):
        get_software_info_json(bad)


@pytest.mark.parametrize(
    "module_name,hidden",
    [
        ("intel/.2021.4.0", True),
        ("intel/2021.4.0", False),
        (".hiddenpkg", True),
        ("gcc/12.3.0", False),
        ("proj", False),
    ],
)
def test_is_hidden_module(module_name, hidden):
    assert is_hidden_module(module_name) is hidden
