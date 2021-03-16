def group_required(*group_names):
    """Requires user membership in at least one of the groups passed in.
    :param group_names: the valid groups
    :return: a function that checks whether the user of a request matches this requirement
    """
    def user_in_groups(request):
        if bool(request.user.groups.filter(name__in=group_names)) | request.user.is_superuser:
            return True
        return False
    return user_in_groups


def is_user_authenticated():
    """Dummy method which returns a function that always returns True since
    the middleware already checks if an authenticated user made the request
    :return: a function that will always return True
    """
    return lambda x: True
