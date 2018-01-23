"""
Pipe for downloading data to a local file from a source blob URL. Uses boto3
to access s3 instead of calling out to shell commands.

@author: twong / kyocum
@copyright: Human Longevity, Inc. 2017
@license: Apache 2.0
"""


from __future__ import print_function

import disdat.pipe as pipe
import disdat.utility.aws_s3 as s3
import logging
import luigi
import os
import shutil

from urlparse import urlparse

_logger = logging.getLogger(__name__)
_logger.debug(logging.DEBUG)


class Download(pipe.PipeTask):
    """Download data to a local file from a source blob URL. Disdat copies
    files referenced in bundles by file: URLs, so this pipe symlinks sources
    files instead of copying them, on the assumption that the source, having
    already been copied by Disdat into managed storage, will not be
    capriciously deleted out from under the link.
    """
    INPUT_URL_KEY = 'input_url'
    OUTPUT_FILE_KEY = 'file'

    input_url_key = luigi.Parameter(default=INPUT_URL_KEY)
    input_url = luigi.Parameter(default=None)

    _s3_client = None

    def _validate_and_get_input_url(self, df=None):
        input_url = self.input_url
        if input_url is None:
            if df is None or df.shape[0] != 1:
                raise ValueError('Got an invalid input bundle: Expected shape (1, *), got {}'.format(df.shape))
            input_row = df.iloc[0]
            _logger.debug('Input is {}'.format(input_row.values))
            input_url = input_row[self.input_url_key]
        return input_url

    @staticmethod
    def _download_blob(target, source_url):
        """Download data into a target from a source blob URL. We symlink
        local files.

        Args:
            target (`Luigi.Target`): A Luigi Target object
            source_url (str): Source data URL, accepts file:/// and s3://

        Returns:
            None
        """
        url = urlparse(source_url)
        if url.scheme.lower() == 'file':
            _logger.info('Copying {} from file {}'.format(target.path, url.path))
            if not os.path.exists(url.path):
                raise RuntimeError('Unable to find source file {}'.format(url.path))
            shutil.copyfile(url.path, target.path)
        elif url.scheme.lower() == 's3':
            _logger.info('Downloading to {} from {}'.format(target.path, url.geturl()))
            s3.get_s3_file(url.geturl(), target.path)
        else:
            _logger.info('Assuming file: Copying {} from file {}'.format(target.path, url.path))
            if not os.path.exists(url.path):
                raise RuntimeError('Unable to find source file {}'.format(url.path))
            shutil.copyfile(url.path, target.path)

    def pipe_run(self, pipeline_input=None):
        """Download data from a source blob URL.

        Args:
            pipeline_input (`pandas.DataFrame`): A single-row, single-column dataframe with a remote URL
        """
        source_url = self._validate_and_get_input_url(df=pipeline_input)
        target = self.create_output_file(os.path.basename(source_url))
        Download._download_blob(target, source_url)
        return {self.OUTPUT_FILE_KEY: [target.path]}
