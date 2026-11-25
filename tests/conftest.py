import pytest

from edupipe.simulate import simulate
from edupipe.spec import TemplateSpec, load_rules
from edupipe.template import build_template


@pytest.fixture(scope="session")
def spec():
    return TemplateSpec.load()


@pytest.fixture(scope="session")
def rules():
    return load_rules()


@pytest.fixture(scope="session")
def template(tmp_path_factory, spec):
    return build_template(spec, tmp_path_factory.mktemp("tpl") / "template_en.xlsx")


@pytest.fixture(scope="session")
def submissions(tmp_path_factory, spec):
    d = tmp_path_factory.mktemp("subs")
    simulate(spec, d, n=12)
    return d
