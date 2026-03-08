"""Exceptions used in this module."""


class UnauthorizedException(Exception):
    """User is unauthorized."""


class InvalidRequestException(Exception):
    """Something went wrong with the request."""


class ForbiddenException(Exception):
    """User is forbidden to access the resource."""


class InvalidResponseException(Exception):
    """Something went wrong with the response."""
