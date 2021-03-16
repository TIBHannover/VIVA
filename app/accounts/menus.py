from django.urls import reverse
from menu import Menu, MenuItem

from accounts.apps import AccountsConfig
from base.tools.checks import group_required

user_mgmt_children = (
    MenuItem("List users", reverse("accounts:user_list")),
    MenuItem("Create user", reverse("accounts:create_user")),
)

Menu.add_item(f"{AccountsConfig.name}_main", MenuItem("Profile", reverse("accounts:profile")))
Menu.add_item(f"{AccountsConfig.name}_main", MenuItem("Change password", reverse("accounts:change_password")))
Menu.add_item(f"{AccountsConfig.name}_main", MenuItem("User management", "acc:um", children=user_mgmt_children,
                                                      check=group_required("User manager")))
