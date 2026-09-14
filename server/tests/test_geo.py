from geotrigger.geo import haversine_m, is_inside


def test_haversine_zero():
    assert haversine_m(50.0, 14.0, 50.0, 14.0) == 0


def test_haversine_known_distance():
    # Roughly 1 km east at this latitude.
    distance = haversine_m(50.087, 14.421, 50.087, 14.435)
    assert 900 < distance < 1100


def test_inside_radius():
    assert is_inside(50.087, 14.421, 50.087, 14.421, 50)
    assert not is_inside(50.087, 14.421, 50.1, 14.5, 50)
