import logging
import subprocess
import sys
from zipfile import ZipFile
from loguru import logger as logging
import os
from os.path import basename as path_basename, join as path_join


class ClairChecker:
    reports_folder_name = 'clair-reports'

    def __init__(self,
                 server_name,
                 binary_path='clairctl',
                 report_format='json',
                 reports_path='/tmp/reports',
                 reports_file_name='reports.zip'):
        self.server_name = server_name
        self.binary_path = binary_path
        self.report_format = report_format
        self.reports_path = reports_path
        self.reports_file_name = reports_file_name

    def scan(self, image_to_scan: str, report_file_name: str):
        action = 'report'

        cmd = f'{self.binary_path} ' \
              f'{action} --out={self.report_format} ' \
              f'--host {self.server_name} {image_to_scan} > {self.__get_reports_path()}/{report_file_name}'
        logging.debug(cmd)

        child = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        child.wait()

        if child.returncode != 0:
            logging.error(f"Child process return non zero exit code. Called: {cmd}")
        # output = child.stdout.read()
        # print(output)

    @staticmethod
    def get_image_full_path(registry_url: str, image_name: str, image_tag: str):
        image_full_path = f'{registry_url.strip("/")}/{image_name}:{image_tag}'
        logging.debug(f'docker image full path is: {image_full_path}')
        return image_full_path

    def archive_reports(self):
        # Check if target clair dir is exists
        if not os.path.exists(self.__get_reports_path()):
            logging.warning(f'Clair reports dir not found: {self.reports_folder_name}. Skipping archiving')
            return

        # Archiving
        suc_archived_files_count = 0
        zip_file_path = self.__get_archive_file_full_path()
        logging.info(f'Will write report file to: {zip_file_path}')
        with ZipFile(zip_file_path, 'w') as zip_writer:
            for folder_name, _, file_names in os.walk(self.__get_reports_path()):
                if len(file_names) > 0:
                    for filename in file_names:
                        file_path = os.path.join(folder_name, filename)
                        if os.path.getsize(file_path) == 0:
                            logging.warning(f'Clair report file {filename} is zero size. Skipping archiving')
                            # Removing empty report file
                            os.remove(file_path)
                            continue
                        logging.debug(f'Archiving file: {file_path}')
                        suc_archived_files_count += 1
                        zip_writer.write(file_path, path_basename(file_path))
                else:
                    logging.warning(f'Nothing to archive. Reports directory {self.reports_path} is empty ')

        if suc_archived_files_count == 0:
            logging.error(f'Clair report archive contains zero files count.'
                          f' Something went wrong with report generation?')
            sys.exit(1)

    def __get_reports_path(self):
        return path_join(self.reports_path, self.reports_folder_name)

    def __get_archive_file_full_path(self):
        return path_join(self.reports_path, self.reports_file_name)

    def gen_report_file_name(self, image_name: str, image_tag: str) -> str:
        return f'{image_name.replace("/", "_")}--{image_tag}.{self.report_format}'

    def create_report_dir(self):
        if not os.path.exists(self.reports_path):
            logging.debug(f'Creating archive reports directory: {self.reports_path}')
            os.makedirs(self.reports_path)
        else:
            logging.debug(f'Archive reports target directory {self.reports_path} already exists. Will write into it.')

        clair_folder_name = self.__get_reports_path()
        if not os.path.exists(clair_folder_name):
            logging.debug(f'Creating reports directory: {clair_folder_name}')
            os.makedirs(clair_folder_name)
        else:
            logging.debug(f'Reports target directory {clair_folder_name} already exists. Will write report into it.')
