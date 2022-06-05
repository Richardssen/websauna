# Pyramid
import transaction

from flaky import flaky

# Websauna
from websauna.system.user.models import User, Group
from websauna.tests.test_utils import create_logged_in_user
from websauna.utils.slug import uuid_to_slug


GROUP_NAME = "Sample Group"


def get_user(dbsession):
    return dbsession.query(User).first()


def test_add_group(web_server, browser, dbsession, init):
    """Create a new group through admin interface."""

    b = browser
    create_logged_in_user(
        dbsession, init.config.registry, web_server, b, admin=True
    )

    b.find_by_css("#nav-admin").click()

    b.find_by_css("#btn-panel-add-group").click()
    b.fill("name", GROUP_NAME)
    b.fill("description", "Foobar")
    b.find_by_name("add").click()

    assert b.is_text_present("Item added")

    # Check name uniqueness
    b.visit(f"{web_server}/admin/models/group/add")
    b.fill("name", GROUP_NAME)
    b.fill("description", "Foobar")
    b.find_by_name("add").click()
    assert b.is_text_present("There was a problem")
    assert b.is_text_present("Group with this `name` already exists")

    # Check we appear in the list
    b.visit(f"{web_server}/admin/models/group/listing")

    # The description appears in the listing
    assert b.is_text_present("Foobar")


def test_edit_group(web_server, browser, dbsession, init):
    """Edit existen group through admin interface."""

    b = browser
    create_logged_in_user(
        dbsession, init.config.registry, web_server, b, admin=True
    )

    GROUP_NAME2 = f"{GROUP_NAME}2"
    GROUP_NAME3 = f"{GROUP_NAME}3"

    # Create two groups with difference names
    with transaction.manager:
        for gname in (GROUP_NAME, GROUP_NAME2):
            g = Group(name=gname)
            dbsession.add(g)

    # Check name uniqueness: trying change GROUP_NAME2 to GROUP_NAME
    b.find_by_css("#nav-admin").click()
    b.find_by_css("#btn-panel-list-group").click()
    b.find_by_css(".crud-row-3 .btn-crud-listing-edit").click()
    b.fill("name", GROUP_NAME)
    b.find_by_name("save").click()
    assert b.is_text_present("There was a problem")
    assert b.is_text_present("Group with this `name` already exists")

    # Check empty Group name
    b.fill("name", "")
    b.find_by_name("save").click()
    assert b.is_text_present("There was a problem")

    # Set new name
    b.fill("name", GROUP_NAME3)
    b.find_by_name("save").click()
    assert b.is_text_present("Changes saved")
    # Check we appear in the list
    b.visit(f"{web_server}/admin/models/group/listing")

    # The new name appears in the listing
    assert b.is_text_present(GROUP_NAME3)


def test_put_user_to_group(web_server, browser, dbsession, init):
    """Check that we can assign users to groups in admin interface."""

    b = browser

    from websauna.system.user.models import Group

    create_logged_in_user(
        dbsession, init.config.registry, web_server, b, admin=True
    )

    # Create a group where we
    with transaction.manager:
        g = Group(name=GROUP_NAME)
        dbsession.add(g)
        dbsession.flush()
        group_uuid = uuid_to_slug(g.uuid)

    b.find_by_css("#nav-admin").click()
    b.find_by_css("#btn-panel-list-user").click()
    b.find_by_css(".crud-row-1 .btn-crud-listing-edit").click()

    # Check the group checkbox. We could put some more specific classes for controls here.
    b.find_by_css(f"input[type='checkbox'][value='{group_uuid}']").click()
    b.find_by_name("save").click()

    assert b.is_text_present("Changes saved")

    # Now we are on Show page of the user, having the new group name visible
    assert b.is_text_present(GROUP_NAME)


@flaky
def test_user_group_choices_preserved_on_validation_error(web_server, init, browser, dbsession):
    """When user edit form validation fails, we should preserve the existing group choices.

    This stresses out hacky implementation of websauna.system.form.colander and deserialization.
    """

    b = browser

    from websauna.system.user.models import Group

    create_logged_in_user(
        dbsession, init.config.registry, web_server, b, admin=True
    )

    # Create a group where we
    with transaction.manager:
        g = Group(name=GROUP_NAME)
        dbsession.add(g)
        u = get_user(dbsession)
        u.groups.append(g)
        dbsession.flush()
        group_uuid = uuid_to_slug(g.uuid)

    b.find_by_css("#nav-admin").click()
    b.find_by_css("#btn-panel-list-user").click()
    b.find_by_css(".crud-row-1 .btn-crud-listing-edit").click()

    # We are in group 2 initially, assert checkbox is checked
    assert b.find_by_css(
        f"input[type='checkbox'][value='{group_uuid}'][checked='True']"
    )


    # Do validation error by leaving username empty
    b.fill("username", "")
    b.find_by_name("save").click()
    assert b.is_text_present("There was a problem")

    # Both group checkboxes should be still selected
    with transaction.manager:
        for g in dbsession.query(Group).all():
            assert b.find_by_css(
                f"input[type='checkbox'][value='{uuid_to_slug(g.uuid)}'][checked='True']"
            )


def test_remove_user_from_group(web_server, init, browser, dbsession):
    """Remove users from assigned groups in admin."""

    b = browser

    from websauna.system.user.models import Group

    create_logged_in_user(
        dbsession, init.config.registry, web_server, b, admin=True
    )

    # Create a group where we
    with transaction.manager:
        g = Group(name=GROUP_NAME)
        dbsession.add(g)
        u = get_user(dbsession)
        u.groups.append(g)
        dbsession.flush()
        group_uuid = uuid_to_slug(g.uuid)

    b.find_by_css("#nav-admin").click()
    b.find_by_css("#btn-panel-list-user").click()
    b.find_by_css(".crud-row-1 .btn-crud-listing-edit").click()

    # Check the group checkbox. We could put some more specific classes for controls here.
    b.find_by_css(f"input[type='checkbox'][value='{group_uuid}']").click()
    b.find_by_name("save").click()

    assert b.is_text_present("Changes saved")

    # After removing we should no longer see the removed group name on user show page
    assert not b.is_text_present(GROUP_NAME)
