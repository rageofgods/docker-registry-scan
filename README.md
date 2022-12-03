# docker-registry-scan
Just a simple tool to check target nexus docker registry images with clair in ad-hoc manner


```
usage: main.py [-h] -n NEXUS_SERVER -r NEXUS_REPO -c CLAIR_SERVER [-p CLAIR_REPORTS_PATH] [-f CLAIR_REPORTS_FORMAT] [-b CLAIR_BINARY_PATH] [-a CLAIR_ASYNC_NUM] [-m MAPPING_CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  -n NEXUS_SERVER, --nexus-server NEXUS_SERVER
                        Nexus server name (abc.xyz:443)
  -r NEXUS_REPO, --nexus_repo NEXUS_REPO
                        Nexus server target repository
  -c CLAIR_SERVER, --clair-server CLAIR_SERVER
                        Clair server name (abc.xyz:443
  -p CLAIR_REPORTS_PATH, --clair-reports-path CLAIR_REPORTS_PATH
                        Clair path to reports archive
  -f CLAIR_REPORTS_FORMAT, --clair-reports-format CLAIR_REPORTS_FORMAT
                        Clair supported reports format
  -b CLAIR_BINARY_PATH, --clair-binary-path CLAIR_BINARY_PATH
                        Path to clair binary control file 'clairctl'
  -a CLAIR_ASYNC_NUM, --clair-async-num CLAIR_ASYNC_NUM
                        Set clair maximum async workers
  -m MAPPING_CONFIG, --mapping-config MAPPING_CONFIG
                        Path to yaml config with registry name to repository name mapping
```