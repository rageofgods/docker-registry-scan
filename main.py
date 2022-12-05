import config
import sys
from nexus_parser import NexusParser
from worker_pool import WorkerPool
from clair_checker import ClairChecker
from loguru import logger as logging


def main():
    # Get valuable environment variables
    env_vars = config.get_env_vars()
    # Get script execution command line arguments
    args = config.get_args()

    # Setup logger
    logging.remove(0)
    logging.add(sys.stdout, level=str(env_vars['log_level']).upper())

    # Querying nexus server for some interesting data
    np = NexusParser(args.nexus_server, args.nexus_repo, env_vars['username'], env_vars['password'])
    np.init_pool_manager(retries=3)
    logging.info('Start analyzing remote docker registry...')
    # Set required http headers
    np.setup_headers()
    # Query Nexus for interesting data
    np.analyse_all_comps()
    # Get results
    nexus_results = np.get_results()

    logging.info('Analyzing complete.')
    logging.info(f'Total images found: {len({list(value.keys())[0] for (key, value) in nexus_results.items()})}')
    logging.info(f'Total image tags found: {len(nexus_results)}')

    if len(nexus_results) == 0:
        logging.warning(f'Nothing to process. Exiting.')
        sys.exit(0)

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
                       (ClairChecker.get_image_full_path(
                           config.get_registry_by_repo_name(args.mapping_config, args.nexus_repo), image_name, tag_name),
                        clair.gen_report_file_name(image_name, tag_name)))
    # Clean up
    wp.end_pool()
    # Archiving reports
    clair.archive_reports()


if __name__ == '__main__':
    main()
