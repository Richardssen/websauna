"""Support for reading Pyramid configuration files and having rollbacked transactions in tests.

https://gist.github.com/inklesspen/4504383
"""


import os

import pytest

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid_web20.models import DBSession
from pyramid_web20.models import Base

_cached_config = None


@pytest.fixture(scope='function')
def ini_settings(request):

    global _cached_config

    if not hasattr(request.config.option, "ini"):
        raise RuntimeError("You need to give --ini test.ini command line option to py.test to find our test settings")

    if not _cached_config:
        config_uri = os.path.abspath(request.config.option.ini)
        setup_logging(config_uri)
        config = get_appsettings(config_uri)
        _cached_config = config

    # Export loaded config to the test case instance
    request.instance.config = _cached_config

    return _cached_config


@pytest.fixture(scope='session')
def sqlengine(request, appsettings):
    engine = engine_from_config(appsettings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)

    def teardown():
        Base.metadata.drop_all(engine)

    request.addfinalizer(teardown)
    return engine


@pytest.fixture()
def dbtransaction(request, sqlengine):
    connection = sqlengine.connect()
    transaction = connection.begin()
    DBSession.configure(bind=connection)

    def teardown():
        transaction.rollback()
        connection.close()
        DBSession.remove()

    request.addfinalizer(teardown)

    return connection


def pytest_addoption(parser):
    parser.addoption("--ini", action="store", metavar="INI_FILE", help="use INI_FILE to configure SQLAlchemy")
