import pytest
from prop_signal import prop_signal


def row(**changes):
    return dict(Projection=20.,Line=18.5,Evidence='Current season',Sample=10,
                **{'Minutes low':28.,'Minutes high':34.,'Role status':'stable'},Status='Not listed — unconfirmed')|changes


def test_line_direction_and_gate_priority():
    assert prop_signal(row())[0:2]==('Above line','green')
    assert prop_signal(row(Line=21.))[0:2]==('Below line','red')
    assert prop_signal(row(Line=20.))[0]=='At line'
    assert prop_signal(row(Line=None))[0]=='Add line'
    assert prop_signal(row(Evidence='Prior-season reference'))[0]=='Research only'
    assert prop_signal(row(Sample=5))[0]=='Small sample'
    assert prop_signal(row(**{'Minutes high':45.}))[0]=='Minutes uncertain'
    assert prop_signal(row(Projection=None))[0]=='No estimate'
    assert prop_signal(row(Status='Out'))[0]=='Unavailable'
    assert prop_signal(row(Status='Questionable'))[0]=='Availability uncertain'
    assert prop_signal(row(Readiness='stale_history'))[0]=='Old history'
    assert prop_signal(row(Sample=None))[0]=='Small sample'


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True,-1])
def test_bad_values_do_not_become_green(value):
    assert prop_signal(row(Projection=value))[1]!='green'
    assert prop_signal(row(Line=value))[1]!='green'
