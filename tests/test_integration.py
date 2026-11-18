import pytest
from glitchstudy import ARTIFACT
from glitchstudy.baseline import analyze_file
from glitchstudy.command_rule import CommandAwareVisitor


@pytest.mark.parametrize("tech,suffix,source", [
    ("ansible", ".yml", '- name: Database maintenance\n  command: "mysql -uroot -e SELECT"\n'),
    ("chef", ".rb", 'execute "dbcheck" do\n  command "mysql -uroot -e SELECT"\nend\n'),
    ("puppet", ".pp", "exec { 'dbcheck':\n  command => 'mysql -uroot -e SELECT',\n}\n"),
])
def test_shared_rule_across_original_parsers(tmp_path, tech, suffix, source):
    path = tmp_path / ("fixture" + suffix)
    path.write_text(source)
    config = ARTIFACT / "GLITCH/configs/improved.ini"
    original, _ = analyze_file(path, tech, config)
    corrected, status = analyze_file(path, tech, config, CommandAwareVisitor)
    assert status["parsed"]
    assert not [r for r in original if r["ERROR"] == "admin-by-default"]
    assert [(r["LINE"], r["ERROR"]) for r in corrected if r["ERROR"] == "admin-by-default"] == [(2, "admin-by-default")]
