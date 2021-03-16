class Error(Exception):
    pass

class ModelNotFoundError(Error):
	pass

class DetectorNotFoundError(Error):
    pass

class AlignerNotFoundError(Error):
    pass

class IndexNotFoundError(Error):
    pass

class CouldNotReadFileError(Error):
    pass

class NoSimilarFacesError(Error):
    pass

class NoFaceInImageError(Error):
    pass

class NotAlignedError(Error):
    pass

