"""Run scenario using the iot simulation topology (gotham scenario)."""

import re
import sys
import time

import docker

from gns3utils import *

PROJECT_NAME = "CoAP_scenario"

check_resources()
check_local_gns3_config()
server = Server(*read_local_gns3_config())

check_server_version(server)

project = get_project_by_name(server, PROJECT_NAME)

if project:
    print(f"Project {PROJECT_NAME} exists. ", project)
else:
    print(f"Project {PROJECT_NAME} does not exsist!")
    sys.exit(1)

open_project_if_closed(server, project)

if len(get_all_nodes(server, project)) == 0:
    print(f"Project {PROJECT_NAME} is empty!")
    sys.exit(1)

check_ipaddrs(server, project)

docker_client = docker.from_env()
docker_client.ping()

#######
# Run #
#######

start_all_routers(server, project, sleeptime=30)
start_all_switches(server, project)

all_iot = get_nodes_id_by_name_regexp(server, project, re.compile("iotsim-.*", re.IGNORECASE))

general_services = list(filter(lambda n: re.search(re.compile(r"dns|ntp", re.IGNORECASE), n.name), all_iot))
iot_servers = list(filter(lambda n: re.search(re.compile(r"(combined|city|broker|stream)(?!.*(cloud|consumer))", re.IGNORECASE), n.name), all_iot))
iot_rest = set(all_iot) - set(general_services) - set(iot_servers)

assert len(iot_rest) + len(iot_servers) + len(general_services) == len(all_iot)

for n in general_services:
    print(f"Starting {n.name}")
    start_node(server, project, n.id)
    time.sleep(0.1)

for n in iot_servers:
    print(f"Starting {n.name}")
    start_node(server, project, n.id)
    time.sleep(0.1)

for n in sorted(iot_rest, key=lambda x: x.name):
    print(f"Starting {n.name}")
    start_node(server, project, n.id)
    time.sleep(0.1)
