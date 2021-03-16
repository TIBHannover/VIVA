class Error(Exception):
    pass


class NoURLError(Error):
    pass


class InvalidURLError(Error):
    pass


class FileTypeNotAcceptedError(Error):
    pass


class CouldNotReadFileError(Error):
    pass


class NoFileUploadedError(Error):
    pass


class NoELResultError(Error):
    pass


class ELParsingError(Error):
    pass


class NoImageFileError(Error):
    pass


class MaxResultsNoNumberError(Error):
    pass


class FormDataError(Error):
    pass


class NoImageSelectedError(Error):
    pass


class CouldNotFindFileError(Error):
    pass
