from nexus_parser import NexusParser
from worker_pool import WorkerPool
from clair_checker import ClairChecker
import os
import argparse
import sys
from loguru import logger as logging
import yaml


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", "--nexus-server",
                        dest="nexus_server",
                        help="Nexus server name (abc.xyz:443)",
                        required=True)
    parser.add_argument("-r", "--nexus_repo",
                        dest="nexus_repo",
                        help="Nexus server target repository",
                        required=True)
    parser.add_argument("-c", "--clair-server",
                        dest="clair_server",
                        help="Clair server name (abc.xyz:443",
                        required=True)
    parser.add_argument("-p", "--clair-reports-path",
                        dest="clair_reports_path",
                        help="Clair path to reports archive",
                        default="/tmp/reports")
    parser.add_argument("-f", "--clair-reports-format",
                        dest="clair_reports_format",
                        default="json",
                        help="Clair supported reports format")
    parser.add_argument("-b", "--clair-binary-path",
                        dest="clair_binary_path",
                        default="clairctl",
                        help="Path to clair binary control file 'clairctl'")
    parser.add_argument("-a", "--clair-async-num",
                        dest="clair_async_num",
                        default="3",
                        help="Set clair maximum async workers")
    parser.add_argument("-m", "--mapping-config",
                        dest="mapping_config",
                        default="registry_map.yaml",
                        help="Path to yaml config with registry name to repository name mapping")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if not args.nexus_server:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if not args.clair_server:
        parser.print_help(sys.stderr)
        sys.exit(1)
    if not args.nexus_repo:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args


def get_env_vars() -> dict:
    result = {}
    try:
        result['username'] = os.environ['DRS_USER']
    except KeyError:
        result['username'] = ''
        logging.warning('NO env.DRS_USER was set. Skipping.')
    try:
        result['password'] = os.environ['DRS_PASS']
    except KeyError:
        result['password'] = ''
        logging.warning('NO env.DRS_PASS was set. Skipping.')
    try:
        result['log_level'] = os.environ['DRS_LOG_LEVEL']
    except KeyError:
        result['log_level'] = 'WARNING'
        logging.warning('NO env.DRS_LOG_LEVEL was set. Default to [WARNING]')

    return result


def get_registry_by_repo_name(mapping_config_name: str, repo_name: str):
    parsed_yaml = read_config_file(mapping_config_name)

    result = ''
    try:
        registry_map = parsed_yaml['registryMap']
        for repo, registry in registry_map.items():
            if repo == repo_name:
                result = registry
                break
    except KeyError:
        logging.error(f"Can't find 'registryMap' section in mapping config: {mapping_config_name}")
        sys.exit(1)

    if result == '':
        logging.error(f"Can't find repository name: {repo_name} in mapping config: {mapping_config_name}")
        sys.exit(1)

    logging.info(f"found registry mapping for repo name {repo_name}: {result}")
    return result


def read_config_file(config_name: str) -> yaml:
    with open(config_name, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(f"Can't parse yaml file: {exc}")


def main():
    # Get valuable environment variables
    env_vars = get_env_vars()
    # Get script execution command line arguments
    args = get_args()
    logging.add(sys.stdout, level=env_vars['log_level'])

    # Querying nexus server for some interesting data
    ic = NexusParser(args.nexus_server, args.nexus_repo, env_vars['username'], env_vars['password'])
    ic.init_pool_manager(retries=3)
    logging.info('Start analyzing remote docker registry...')
    nexus_results = ic.get_all_comps()
    logging.debug(f'Total images found: {len(nexus_results)}')
    logging.info('Analyzing complete.')

    # Init clair constructor
    clair = ClairChecker(server_name=args.clair_server,
                         reports_file_name=f'{args.nexus_repo}.zip',
                         reports_path=args.clair_reports_path,
                         report_format=args.clair_reports_format,
                         binary_path=args.clair_binary_path)
    # Create new worker pool for spawned processes and limit bucket size
    wp = WorkerPool(limit=int(args.clair_async_num))
    # Start image checking with clair
    for image_name_tag in nexus_results.values():
        image_name = list(image_name_tag.keys())[0]
        tag_name = list(image_name_tag.values())[0]
        wp.add_to_pool(clair.scan,
                       (clair.get_image_full_path(
                           get_registry_by_repo_name(args.mapping_config, args.nexus_repo), image_name, tag_name),
                        clair.gen_report_file_name(image_name, tag_name)))
    # Clean up
    wp.end_pool()
    # Archiving reports
    clair.archive_reports()


if __name__ == '__main__':
    main()
