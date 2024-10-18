import os
import re
from glob import glob
from types import SimpleNamespace

from pfs.datamodel import *

from ..setup_logger import logger

from ..constants import Constants
from .intfilter import IntFilter
from .hexfilter import HexFilter
from .datefilter import DateFilter
from .stringfilter import StringFilter

class FileSystemConnector():
    """
    Implements routines to find data products in the file system.
    This is a replacement of Butler for local development.

    The class works by querying the file system with glob for files that match the specified parameters.
    The parameters can either be defined on the class level or passed as arguments to the methods.
    Method arguments always take precedence over class-level parameters.

    Variables
    ---------
    datadir : str
        Path to the data directory. Set to GAPIPE_DATADIR by default.
    rerundir : str
        Path to the rerun directory. Set to GAPIPE_RERUNDIR by default.
    PfsDesignId : HexFilter
        Filter for PfsDesign identifier.
    catId : IntFilter
        Filter for catalog identifier.
    tract : IntFilter
        Filter for tract number.
    patch : StringFilter
        Filter for patch identifier.
    objId : HexFilter
        Filter for object identifier.
    visit : IntFilter
        Filter for visit number.
    date : DateFilter
        Filter for observation date.
    """

    def __init__(self,
                 datadir=None,
                 rerundir=None,
                 orig=None):
        
        if not isinstance(orig, FileSystemConnector):
            self.__datadir = datadir if datadir is not None else self.__get_envvar('GAPIPE_DATADIR')
            self.__rerundir = rerundir if rerundir is not None else self.__get_envvar('GAPIPE_RERUNDIR')

            self.__pfsDesignId = HexFilter(name='pfsDesignId', format='{:016x}')
            self.__catId = IntFilter(name='catid', format='{:05d}')
            self.__tract = IntFilter(name='tract', format='{:05d}')
            self.__patch = StringFilter(name='patch')
            self.__objId = HexFilter(name='objid', format='{:016x}')
            self.__visit = IntFilter(name='visit', format='{:06d}')
            self.__date = DateFilter(name='date', format='{:%Y-%m-%d}')
        else:
            self.__datadir = datadir if datadir is not None else orig.__datadir
            self.__rerundir = rerundir if rerundir is not None else orig.__rerundir

            self.__pfsDesignId = orig.__pfsDesignId
            self.__catId = orig.__catId
            self.__tract = orig.__tract
            self.__patch = orig.__patch
            self.__objId = orig.__objId
            self.__visit = orig.__visit
            self.__date = orig.__date

    #region Properties

    def __get_datadir(self):
        return self.__datadir
    
    def __set_datadir(self, value):
        self.__datadir = value

    datadir = property(__get_datadir, __set_datadir)

    def __get_rerundir(self):
        return self.__rerundir
    
    def __set_rerundir(self, value):
        self.__rerundir = value

    rerundir = property(__get_rerundir, __set_rerundir)

    def __get_pfsDesignId(self):
        return self.__pfsDesignId
    
    pfsDesignId = property(__get_pfsDesignId)

    def __get_catId(self):
        return self.__catId
    
    catId = property(__get_catId)

    def __get_tract(self):
        return self.__tract
    
    tract = property(__get_tract)

    def __get_patch(self):
        return self.__patch
    
    def __set_patch(self, value):
        self.__patch = value
    
    patch = property(__get_patch, __set_patch)

    def __get_objId(self):
        return self.__objId
    
    objId = property(__get_objId)

    def __get_visit(self):
        return self.__visit
    
    visit = property(__get_visit)

    #endregion
    #region Utility functions

    def __get_envvar(self, key):
        if key in os.environ:
            return os.environ[key]
        else:
            return None

    def __throw_or_warn(self, message, required, exception_type=ValueError):
        """
        If required is True, raises an exception with the specified message, otherwise logs a warning.

        Arguments
        ---------
        message : str
            Message to log or raise.
        required : bool
            If True, an exception is raised. Otherwise, a warning is logged.
        exception_type : Exception
            Type of the exception to raise. Default is ValueError.
        """

        if required:
            raise exception_type(message)
        else:
            logger.warning(message)

    def __ensure_one_param(self, **kwargs):
        """
        Ensures that only one parameter is specified in the keyword arguments.

        Arguments
        ---------
        kwargs : dict
            Keyword arguments to check.

        Returns
        -------
        str
            Name of the parameter that is specified.
        """

        if sum([1 for x in kwargs.values() if x is not None]) != 1:
            names = ', '.join(kwargs.keys())
            raise ValueError(f'Only one of the parameters {names} can be specified .')

    def __parse_filename_params(self, path: str, params: SimpleNamespace, regex: str, required=True):
        """
        Parses parameters from the filename using the specified regex pattern.

        Arguments
        ---------
        path : str
            Path to the file.
        params : SimpleNamespace
            Parameters to parse from the filename.
        regex : str
            Regular expression pattern to match the filename. The regex should contain named groups
            that correspond to the parameters in the SimpleNamespace.
        """

        # Unwrap the parameters
        params = params.__dict__

        # Match the filename pattern to find the IDs
        match = re.search(regex, path)
        if match is not None:
            return SimpleNamespace(**{ k: p.parse_value(match.group(k)) for k, p in params.items() })
        else:
            self.__throw_or_warn(f'Filename does not match expected format: {path}', required)
            return None

    def __find_files_and_match_params(self, patterns: list, params: SimpleNamespace, param_values: SimpleNamespace, regex: str):
        """
        Given a list of directory name glob pattern template strings, substitute the parameters
        and find files that match the glob pattern. Match IDs is in the file names with the
        parameters and return the matched IDs, as well as the paths to the files. The final
        list is filtered by the parameters.

        Arguments
        ---------
        patterns : str
            List of directory name glob pattern template strings.
        params : SimpleNamespace
            Parameters to match the IDs in the file names.
        regex : str
            Regular expression pattern to match the filename. The regex should contain named groups
            that correspond to the parameters in the Simple

        Returns
        -------
        list of str
            List of paths to the files that match the query.
        SimpleNamespace
            List of identifiers that match the query.
        """

        # Unwrap the parameters
        params = params.__dict__

        # Update the parameters with the values
        for k, v in param_values.items():
            if k in params:
                if v is not None:
                    params[k].values = v
                elif hasattr(self, k):
                    params[k].values = getattr(self, k)

        # Evaluate the glob pattern for each filter parameter
        glob_pattern_parts = { k: p.get_glob_pattern() for k, p in params.items() }

        # Compose the full glob pattern
        glob_pattern = os.path.join(*[ p.format(**glob_pattern_parts) for p in patterns ])

        # Find the files that match the glob pattern
        paths = glob(glob_pattern)


        ids = { k: [] for k in params.keys() }
        values = { k: None for k in params.keys() }
        filenames = []
        for path in paths:
            # Match the filename pattern to find the IDs
            match = re.search(regex, path)
            
            if match is not None:
                # If all parameters match the param filters, add the IDs to the list
                good = True
                for k, param in params.items():
                    # Parse the string value from the match and convert it to the correct type
                    values[k] = param.parse_value(match.group(k))

                    # Match the parameter against the filter. This is a comparison
                    # against the values and value ranges specified in the filter.
                    good &= param.match(values[k])

                if good:
                    filenames.append(path)
                    for k, v in values.items():
                        ids[k].append(v)

        return filenames, SimpleNamespace(**ids)
    
    def __get_single_file(self, files, ids):
        """
        Given a list of files and a list of identifiers, returns the single file that matches the query.
        If more than one file is found, an exception is raised. If no files are found, an exception is raised.

        Arguments
        ---------
        files : list of str
            List of paths to the files that match the query.
        ids : SimpleNamespace
            List of identifiers that match the query.

        Returns
        -------
        str
            Path to the file that matches the query.
        SimpleNamespace
            Identifiers that match the query.
        """

        if len(files) == 0:
            raise FileNotFoundError(f'No file found matching the query.')
        elif len(files) > 1:
            raise FileNotFoundError(f'Multiple files found matching the query.')
        else:
            return files[0], SimpleNamespace(**{ k: v[0] for k, v in ids.__dict__.items() })
        
    #endregion
    #region Repository location functions

    def get_datadir(self, reference_path=None, required=False):
        """
        Returns the path to the data directory. If the reference path is provided, the path
        to the data directory is inferred from the reference path, if possible. If `required`
        is True and the data directory cannot be inferred, an exception is raised. Otherwise,
        a warning is logged and the default data directory is returned.

        Arguments
        ---------
        reference_path : str
            Path to a file referencing the data directory. The path will be used to
            discover the path to the data directory.
        required : bool
            If True, an exception is raised if the data directory cannot be inferred from
            the reference path. Otherwise, a warning is logged and the default data directory
            is returned.

        Returns
        -------
        str
            Path to the data directory.
        """

        rerun_index = -1
        if reference_path is not None:
            # Split path into list of directories
            dirs = reference_path.split(os.sep)

            # Find the parent directory of data in filename
            if 'rerun' in dirs:
                rerun_index = dirs.index('rerun')
            elif 'pfsConfig' in dirs:
                rerun_index = dirs.index('pfsConfig')
            elif 'pfsDesign' in dirs:
                rerun_index = dirs.index('pfsDesign')
            else:
                self.__throw_or_warn('Data directory cannot be inferred from reference path.', required)
            
        if rerun_index != -1:
            return os.path.abspath(os.sep.join(dirs[:rerun_index]))
        else:
            return os.path.abspath(self.__datadir)

    def get_rerundir(self, reference_path=None, required=False):  
        """
        Returns the path to the rerun directory. If the reference path is provided, the path
        to the rerun directory is inferred from the reference path, if possible. If `required`
        is True and the rerun directory cannot be inferred, an exception is raised. Otherwise,
        a warning is logged and the default rerun directory is returned.

        Arguments
        ---------
        reference_path : str
            Path to a file referencing the rerun directory. The path will be used to
            discover the path to the rerun directory.
        required : bool
            If True, an exception is raised if the rerun directory cannot be inferred from
            the reference path. Otherwise, a warning is logged and the default rerun directory
            is returned.

        Returns
        -------
        str
            Path to the rerun directory.
        """

        rerun_index = -1
        if reference_path is not None:
            # Split path into list of directories
            dirs = reference_path.split(os.sep)

            # Find the parent directory of any of the PFS products
            # TODO: extend list
            for product in [ 'pfsArm', 'pfsMerged', 'pfsSingle', 'pfsObject', 'pfsGAObject' ]:
                if product in dirs:
                    rerun_index = dirs.index(product)
                    break

            if rerun_index == -1:
                self.__throw_or_warn('Rerun directory cannot be inferred from reference path.', required)

        if rerun_index != -1:
            return os.path.abspath(os.sep.join(dirs[:rerun_index]))
        else:
            return os.path.abspath(os.path.join(self.__datadir, self.__rerundir))
        
    #endregion
    #region PfsDesign

    def __get_pfsDesign_identity_fields(self):
        return SimpleNamespace(
            pfsDesignId = HexFilter(name='pfsDesignId', format='{:016x}'),
        )

    def parse_pfsDesign(self, path):
        """
        Parse the identifiers from the PfsDesign file name.

        Arguments
        ---------
        path : str
            Path to the PfsDesign file.

        Returns
        -------
        SimpleNamespace
            Identifiers parsed from the file name.
        """

        dir, basename = os.path.split(path)

        identity = self.__parse_filename_params(
            basename,
            params = self.__get_pfsDesign_identity_fields(),
            regex = Constants.PFSDESIGN_FILENAME_REGEX
        )

        return identity

    def find_pfsDesign(self, *, reference_path=None, **kwargs):
        """
        Find PfsDesign files.

        Arguments
        ---------
        pfsDesignId : HexIDFilter or int or None
            PfsDesign identifier.
        reference_path : str
            Path to a file referencing the PfsDesign file. The path will be used to
            discover the path to the PfsDesign file.

        Returns
        -------
        list of str
            List of paths to the files that match the query.
        SimpleNamespace
            List of identifiers that match the query.
        """

        return self.__find_files_and_match_params(
            patterns = [
                self.get_datadir(reference_path=reference_path),
                Constants.PFSDESIGN_DIR_GLOB,
                Constants.PFSDESIGN_FILENAME_GLOB,
            ],
            regex = Constants.PFSDESIGN_FILENAME_REGEX,
            params = self.__get_pfsDesign_identity_fields(),
            param_values = kwargs)
    
    def locate_pfsDesign(self, *, reference_path=None, **kwargs):
        """
        Find a specific PfsDesign file.

        Arguments
        ---------
        pfsDesignId : int
            PfsDesign identifier.
        reference_path : str
            Path to a file referencing the PfsDesign file. The path will be used to
            discover the path to the PfsDesign file.
        """

        files, ids = self.find_pfsDesign(reference_path=reference_path, **kwargs)
        return self.__get_single_file(files, ids)
    
    def load_pfsDesign(self, filename=None, identity=None):
        """
        Load a PfsDesign file based on the filename or the identity. Only
        one of `filename` or `identity` can be specified.

        Arguments
        ---------
        filename : str
            Name of the file to load.
        identity : SimpleNamespace
            Identifiers.

        Returns
        -------
        PfsDesign
            PfsDesign object.
        """

        self.__ensure_one_param(filename=filename, identity=identity)
        
        if filename is not None:
            # Extract pfsDesignId and visit from the filename
            dir, basename = os.path.split(filename)
            identity = self.__parse_filename_params(
                basename,
                params = SimpleNamespace(
                    pfsDesignId = HexFilter(),
                ),
                regex = Constants.PFSDESIGN_FILENAME_REGEX
            )
        elif identity is not None:
            dir = ''

        dir = os.path.join(
            self.__datadir,
            Constants.PFSDESIGN_DIR_FORMAT.format(**identity.__dict__))

        return PfsDesign.read(identity.pfsDesignId, dirName=dir,), identity

    #endregion    
    #region PfsConfig

    def __get_pfsConfig_identity_fields(self):
        return SimpleNamespace(
            pfsDesignId = HexFilter(name='pfsDesignId', format='{:016x}'),
            visit = IntFilter(name='visit', format='{:06d}'),
            date = DateFilter(name='date', format='{:%Y-%m-%d}'),
        )

    def parse_pfsConfig(self, path):
        """
        Parse the identifiers from the PfsConfig file name.

        Arguments
        ---------
        path : str
            Path to the PfsConfig file.

        Returns
        -------
        SimpleNamespace
            Identifiers parsed from the file name.
        """

        # PfsConfig cannot read from a file directly, so figure out parameters from the filename
        dir, basename = os.path.split(path)

        # Extract pfsDesignId and visit from the filename
        # First attempt to parse the observation date (it is in the path, when provided),
        # then fall back to using the filename only.
        if dir is not None and dir != '':
            identity = self.__parse_filename_params(
                path,
                params = self.__get_pfsConfig_identity_fields(),
                regex = Constants.PFSCONFIG_PATH_REGEX,
            )
        else:
            identity = self.__parse_filename_params(
                basename,
                params = SimpleNamespace(
                    pfsDesignId = HexFilter(),
                    visit = IntFilter(),
                ),
                regex = Constants.PFSCONFIG_FILENAME_REGEX
            )

        return identity
    
    def find_pfsConfig(self, *, reference_path=None, **kwargs):
        """
        Find PfsConfig files.

        Arguments
        ---------
        pfsDesignId : HexIDFilter or int or None
            PfsDesign identifier.
        visit : IntIDFilter or int or None
            Visit number.
        reference_path : str
            Path to a file referencing the PfsConfig file. The path will be used to
            discover the path to the PfsConfig file.
        """

        return self.__find_files_and_match_params(
            patterns = [
                self.get_datadir(reference_path=reference_path),
                Constants.PFSCONFIG_DIR_GLOB,
                Constants.PFSCONFIG_FILENAME_GLOB,
            ],
            regex = Constants.PFSCONFIG_PATH_REGEX,
            params = self.__get_pfsConfig_identity_fields(),
            param_values = kwargs)
    
    def locate_pfsConfig(self, reference_path=None, **kwargs):
        """
        Find a specific PfsConfig file.

        Arguments
        ---------
        pfsDesignId : int
            PfsDesign identifier.
        visit : int
            Visit number.
        reference_path : str
            Path to a file referencing the PfsConfig file. The path will be used to
            discover the path to the PfsConfig file.
        filename : str
            Name of the file to find. If None, the first file found is returned.
        """

        files, ids = self.find_pfsConfig(reference_path=reference_path, **kwargs)
        return self.__get_single_file(files, ids)
    
    def load_pfsConfig(self, filename=None, identity=None):
        """
        Load a PfsConfig file based on the filename or the identity. Only
        one of `filename` or `identity` can be specified.

        Arguments
        ---------
        filename : str
            Name of the file to load.
        identity : SimpleNamespace
            Identifiers.

        Returns
        -------
        PfsConfig
            PfsConfig object.
        """
        
        self.__ensure_one_param(filename=filename, identity=identity)
        
        if filename is not None:
            # PfsConfig cannot accept the file name directly, so figure out parameters
            # from the filename and then load via the parameters
            identity = self.parse_pfsConfig(filename)

            # If the observation date is not provided, we need to search for the file
            filename, identity = self.locate_pfsConfig(reference_path=filename, **identity.__dict__)
            dir = os.path.dirname(filename)
        elif identity is not None:
            dir = os.path.join(
                self.get_datadir(),
                Constants.PFSCONFIG_DIR_FORMAT.format(**identity.__dict__))

        return PfsConfig.read(identity.pfsDesignId, identity.visit, dirName=dir), identity
    
    #endregion
        
    def find_pfsArm(self, catId, tract, patch, objId, visit, arm):
        raise NotImplementedError()
    
    def find_pfsMerged(self, visit):
        raise NotImplementedError()
    
    #region PfsSingle

    def __get_identity_fields_pfsSingle(self):
        return SimpleNamespace(
            catId = IntFilter(name='catId', format='{:05d}'),
            tract = IntFilter(name='tract', format='{:05d}'),
            patch = StringFilter(name='patch'),
            objId = HexFilter(name='objId', format='{:016x}'),
            visit = IntFilter(name='visit', format='{:06d}'),
        )

    def parse_pfsSingle(self, path):
        dir, basename = os.path.split(path)

        identity = self.__parse_filename_params(
            basename,
            params = self.__get_identity_fields_pfsSingle(),
            regex = Constants.PFSSINGLE_FILENAME_REGEX
        )

        return identity
        
    def find_pfsSingle(self, reference_path=None, **kwargs):
        return self.__find_files_and_match_params(
            patterns = [
                self.get_datadir(reference_path=reference_path),
                self.get_rerundir(reference_path=reference_path),
                Constants.PFSSINGLE_DIR_GLOB,
                Constants.PFSSINGLE_FILENAME_GLOB
            ],
            regex = Constants.PFSSINGLE_FILENAME_REGEX,
            params = self.__get_identity_fields_pfsSingle(),
            param_values = kwargs)
    
    def locate_pfsSingle(self, reference_path=None, **kwargs):
        files, ids = self.find_pfsSingle(reference_path=reference_path, **kwargs)
        return self.__get_single_file(files, ids)

    def load_pfsSingle(self, filename=None, identity=None):
        self.__ensure_one_param(filename=filename, identity=identity)
        
        if filename is not None:
            # Extract pfsDesignId and visit from the filename
            dir, basename = os.path.split(filename)
            identity = self.__parse_filename_params(
                basename,
                params = self.__get_identity_fields_pfsSingle(),
                regex = Constants.PFSSINGLE_FILENAME_REGEX
            )
        elif identity is not None:
            dir = ''

        dir = os.path.join(
            self.__datadir,
            self.__rerundir,
            Constants.PFSSINGLE_DIR_FORMAT.format(**identity.__dict__),
            dir)

        return PfsSingle.read(identity.__dict__, dirName=dir,), identity

    #endregion
    #region PfsObject
    
    def find_pfsObject(self, catId, tract, patch, objId, nVisit, pfsVisitHash, reference_path=None):
        raise NotImplementedError()
    
    #endregion
    #region PfsGAObject

    #endregion