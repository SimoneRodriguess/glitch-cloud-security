import pytest
from glitchstudy.command_rule import command_lines, explicit_root_command
from glitch.repr.inter import Attribute


@pytest.mark.parametrize("command", [
    "mysql -uroot -e 'SELECT 1'", "mysql -u root", "mysql --user=root",
    "mysql --user root", "/usr/bin/mysqladmin -u 'root' ping",
    "mysqldump -uroot db", "mysqlcheck -u root db", "X=1 mysql -uroot",
    "true && mysql -uroot", "mysql -p#{lookup('x')} -uroot -e 'SELECT 1'",
])
def test_literal_root_forms(command):
    assert explicit_root_command(command)


@pytest.mark.parametrize("command", [
    "mysql -u app", "mysql -u $DB_USER", "mysql -u #{node['user']}",
    "mysql --user={{ mysql_user }}", "echo 'mysql -uroot'", "printf '%s' 'mysql -uroot'",
    "notmysql -uroot", "mysql -u rootish", "mysql -u root -u app", "mysql -uroot --user=$USER",
    "mysql --defaults-file=/x", "mysql -u 'root", "documentation mysql -uroot",
])
def test_negative_and_unresolved_forms(command):
    assert not explicit_root_command(command)


def element(name, value, code, line=10):
    a = Attribute(name, value, True)
    a.code, a.line = code, line
    return a


def test_heredoc_source_location():
    a = element("code", "mysql -u root -e \"SELECT 1", 'code <<-EOH\n mysql -u root -e "SELECT 1\nEOH')
    assert command_lines(a) == [11]


def test_opaque_ruby_block_multiple_locations():
    a = element("block", "opaque", 'block do\n if not system "mysql -uroot -e \'SELECT 1\'" then\n %x[ mysql -uroot -e "SELECT 2"\n mysql -uroot -e "SELECT 3"\n ]\nend')
    assert command_lines(a) == [11, 12, 13]


def test_lowering_loss_command_assignment():
    a = element("get_config", "('x')", 'status_cmd="mysql -u root -p#{get_config(\'x\')} -e \\"SELECT 1\\""')
    assert command_lines(a) == [10]


def test_quoted_mentions_not_execution():
    a = element("command", "echo", 'command "echo \'mysql -uroot\'"')
    assert command_lines(a) == []


def test_noncommand_field_ignored():
    a = element("description", "mysql -uroot", 'description "mysql -uroot"')
    assert command_lines(a) == []
