"""Refactorized script to create the Gotham IoT simulation topology."""

import configparser
import ipaddress
import sys
import time

from gns3utils import *

PROJECT_NAME = "MQTT_scenario"
AUTO_CONFIGURE_ROUTERS = True

check_resources()
check_local_gns3_config()
server = Server(*read_local_gns3_config())

check_server_version(server)

project = get_project_by_name(server, PROJECT_NAME)

if project:
    print(f"Project {PROJECT_NAME} exists. ", project)
else:
    project = create_project(server, PROJECT_NAME, 5000, 7500, 15)
    print("Created project ", project)

open_project_if_closed(server, project)

if len(get_all_nodes(server, project)) > 0:
    print("Project is not empty!")
    sys.exit(1)

# Create the templates manually using the GNS3 GUI
# get templates
templates = get_all_templates(server)


# Template IDs
router_template_id = get_template_id_from_name(templates, "VyOS 1.3.0")
assert router_template_id
switch_template_id = get_template_id_from_name(templates, "Open vSwitch")
assert switch_template_id

DNS_template_id = get_template_id_from_name(templates, "iotsim-dns")
assert DNS_template_id
## En el escenario CoAP no se necesita NTP porque se usa PSK
NTP_template_id = get_template_id_from_name(templates, "iotsim-ntp")
assert NTP_template_id

mqtt_broker_1_6_template_id = get_template_id_from_name(templates, "iotsim-mqtt-broker-1.6")
assert mqtt_broker_1_6_template_id
mqtt_broker_1_6_auth_template_id = get_template_id_from_name(templates, "iotsim-mqtt-broker-1.6-auth")
assert mqtt_broker_1_6_auth_template_id
mqtt_broker_tls_template_id = get_template_id_from_name(templates, "iotsim-mqtt-broker-tls")
assert mqtt_broker_tls_template_id
mqtt_client_t1_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-t1")
assert mqtt_client_t1_template_id
mqtt_client_t2_template_id = get_template_id_from_name(templates, "iotsim-mqtt-client-t2")
assert mqtt_client_t2_template_id
air_quality_template_id = get_template_id_from_name(templates, "iotsim-air-quality")
assert air_quality_template_id
cooler_motor_template_id = get_template_id_from_name(templates, "iotsim-cooler-motor")
assert cooler_motor_template_id
predictive_maintenance_template_id = get_template_id_from_name(templates, "iotsim-predictive-maintenance")
assert predictive_maintenance_template_id
hydraulic_system_template_id = get_template_id_from_name(templates, "iotsim-hydraulic-system")
assert hydraulic_system_template_id
building_monitor_template_id = get_template_id_from_name(templates, "iotsim-building-monitor")
assert building_monitor_template_id
domotic_monitor_template_id = get_template_id_from_name(templates, "iotsim-domotic-monitor")
assert domotic_monitor_template_id

scanner_template_id = get_template_id_from_name(templates, "iotsim-scanner")
assert scanner_template_id
mqtt_attacks_template_id = get_template_id_from_name(templates, "iotsim-mqtt-attacks")
assert mqtt_attacks_template_id

# Config file
sim_config = configparser.ConfigParser()
with open("../iot-mqtt-sim.config", "r", encoding="utf-8") as cf:
    sim_config.read_string(f"[main]\n{cf.read()}")
    sim_config = sim_config["main"]
    
lab_dns_addr = sim_config["LAB_DNS_IPADDR"]

input("Open the GNS3 project GUI. Press enter to continue...")

nodes_list = {}

## ROUTERS BACKBONES - 3 Primeros routers (y sus switches)
### Coordenadas
coord_base = Position(0, 0) # Primera coordenada random
coord_rnorth = coord_base
coord_rwest = Position(coord_rnorth.x - project.grid_unit * 2, coord_rnorth.y + project.grid_unit * 4)
coord_reast = Position(coord_rnorth.x + project.grid_unit * 2, coord_rnorth.y + project.grid_unit * 4)

### Nodos
rNorth = create_node(server, project, coord_rnorth.x, coord_rnorth.y, router_template_id)
nodes_list["rNorth"] = rNorth
rWest = create_node(server, project, coord_rwest.x, coord_rwest.y, router_template_id)
nodes_list["rWest"] = rWest
rEast = create_node(server, project, coord_reast.x, coord_reast.y, router_template_id)
nodes_list["rEast"] = rEast

### Conexiones
# create_link(server, project, nodo1_id, interfaz1, nodo2_id, interfaz2)
create_link(server, project, rNorth["node_id"], 1, rWest["node_id"], 1)
create_link(server, project, rNorth["node_id"], 2, rEast["node_id"], 1)
create_link(server, project, rWest["node_id"], 2, rEast["node_id"], 2)

### router installation and configuration.
backbone_routers = [rNorth, rWest, rEast]
backbone_configs = ["../router/backbone/router_north.sh",
                    "../router/backbone/router_west.sh",
                    "../router/backbone/router_east.sh"]
if AUTO_CONFIGURE_ROUTERS:
    for router_node, router_config in zip(backbone_routers, backbone_configs):
        print(f"Installing {router_node['name']}")
        hostname, port = get_node_telnet_host_port(server, project, router_node["node_id"])
        terminal_cmd = f"konsole -e telnet {hostname} {port}"
        start_node(server, project, router_node["node_id"])
        install_vyos_image_on_node(router_node["node_id"], hostname, port, pre_exec=terminal_cmd)
        # time to close the terminals, else Telnet throws EOF errors
        time.sleep(10)
        print(f"Configuring {router_node['name']} with {router_config}")
        start_node(server, project, router_node["node_id"])
        configure_vyos_image_on_node(router_node["node_id"], hostname, port, router_config, pre_exec=terminal_cmd)
        time.sleep(10)

### switches
coord_snorth = Position(coord_rnorth.x, coord_rnorth.y - project.grid_unit * 4)
coord_swest = Position(coord_rwest.x - project.grid_unit * 4, coord_rwest.y)
coord_seast = Position(coord_reast.x + project.grid_unit * 4, coord_reast.y)

sNorth = create_node(server, project, coord_snorth.x, coord_snorth.y, switch_template_id)
sWest = create_node(server, project, coord_swest.x, coord_swest.y, switch_template_id)
sEast = create_node(server, project, coord_seast.x, coord_seast.y, switch_template_id)

create_link(server, project, rNorth["node_id"], 0, sNorth["node_id"], 0)
create_link(server, project, rWest["node_id"], 0, sWest["node_id"], 0)
create_link(server, project, rEast["node_id"], 0, sEast["node_id"], 0)
nodes_list["sNorth"] = {"node": sNorth,"freeport": 1}
nodes_list["sWest"] = {"node": sWest,"freeport": 1}
nodes_list["sEast"] = {"node": sEast,"freeport": 1}

# Unified node definitions
NTP_CLOUD_NAME = (f"ntp.{sim_config['LOCAL_DOMAIN']}", "192.168.0.3")

URBANO_BROKER_NAME = (f"broker.urbano.{sim_config['LOCAL_DOMAIN']}", "192.168.1.2")

INDUSTRIAL_TLS_BROKER_NAME = (sim_config["MQTT_TLS_BROKER_CN"], "192.168.2.2")
INDUSTRIAL_AUTH_BROKER_NAME = (f"broker.industrial.{sim_config['LOCAL_DOMAIN']}", "192.168.2.3")


topology_nodes = [
    {"type": "switch", "name": "sInfoCloud", "coord_x": 6, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "host", "name": "dns", "coord_x": 6, "coord_y": -12, "conexion": "sInfoCloud", "template": DNS_template_id, "ip": f"{lab_dns_addr}/20", "gw": "192.168.0.1"},
    {"type": "host", "name": "ntp", "coord_x": 11, "coord_y": -12, "conexion": "sInfoCloud", "template": NTP_template_id, "ip": f"{NTP_CLOUD_NAME[1]}/20", "gw": "192.168.0.1"}, 

    {"type": "router", "name": "rIndustrial", "coord_x": -32, "coord_y": 8, "conexion": "sWest", "template": router_template_id},
    {"type": "switch", "name": "sIndustrial", "coord_x": -32, "coord_y": 12, "conexion": "rIndustrial", "template": switch_template_id},
    {"type": "cluster", "name": "air_quality_tls", "coord_x": -48, "coord_y": 16, "conexion": "sIndustrial", "numNodos": 2, "template": air_quality_template_id, "ip": "192.168.17.5/24", "gw": "192.168.17.1", "broker": INDUSTRIAL_TLS_BROKER_NAME[0], "tls": "True"}, 
    {"type": "cluster", "name": "cooler_motor", "coord_x": -40, "coord_y": 16, "conexion": "sIndustrial", "numNodos": 2, "template": cooler_motor_template_id, "ip": "192.168.17.10/24", "gw": "192.168.17.1", "broker": INDUSTRIAL_AUTH_BROKER_NAME[0], "auth": "admin:adminpass"}, 
    {"type": "cluster", "name": "hydraulic_system", "coord_x": -32, "coord_y": 16, "conexion": "sIndustrial", "numNodos": 2, "template": hydraulic_system_template_id, "ip": "192.168.17.15/24", "gw": "192.168.17.1", "broker": INDUSTRIAL_AUTH_BROKER_NAME[0], "auth": "production:passw0rd"}, 
    {"type": "cluster", "name": "pred_maintenance", "coord_x": -24, "coord_y": 16, "conexion": "sIndustrial", "numNodos": 2, "template": predictive_maintenance_template_id, "ip": "192.168.17.20/24", "gw": "192.168.17.1", "broker": INDUSTRIAL_TLS_BROKER_NAME[0], "tls": "True"}, 

    {"type": "switch", "name": "sIndustrialCloud", "coord_x": 0, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "host", "name": "indutrial_tls_cloud", "coord_x": 0, "coord_y": -12, "conexion": "sIndustrialCloud", "template": mqtt_broker_tls_template_id, "ip": f"{INDUSTRIAL_TLS_BROKER_NAME[1]}/20", "gw": "192.168.0.1"}, 
    {"type": "host", "name": "indutrial_auth_cloud", "coord_x": -5, "coord_y": -12, "conexion": "sIndustrialCloud", "template": mqtt_broker_1_6_auth_template_id, "ip": f"{INDUSTRIAL_AUTH_BROKER_NAME[1]}/20", "gw": "192.168.0.1"}, 

    {"type": "router", "name": "rUrbano", "coord_x": -8, "coord_y": 8, "conexion": "sWest", "template": router_template_id},
    {"type": "switch", "name": "sUrbano", "coord_x": -8, "coord_y": 12, "conexion": "rUrbano", "template": switch_template_id},
    {"type": "cluster", "name": "air_quality", "coord_x": -16, "coord_y": 16, "conexion": "sUrbano", "numNodos": 2, "template": air_quality_template_id, "ip": "192.168.18.5/24", "gw": "192.168.18.1", "broker": URBANO_BROKER_NAME[0]}, 
    {"type": "cluster", "name": "building_monitor", "coord_x": -8, "coord_y": 16, "conexion": "sUrbano", "numNodos": 2, "template": building_monitor_template_id, "ip": "192.168.18.10/24", "gw": "192.168.18.1", "broker": URBANO_BROKER_NAME[0]}, 
    {"type": "cluster", "name": "domotic_monitor", "coord_x": 0, "coord_y": 16, "conexion": "sUrbano", "numNodos": 2, "template": domotic_monitor_template_id, "ip": "192.168.18.15/24", "gw": "192.168.18.1", "broker": URBANO_BROKER_NAME[0]}, 

    {"type": "switch", "name": "sUrbanoCloud", "coord_x": -10, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "host", "name": "urbano_cloud", "coord_x": -10, "coord_y": -12, "conexion": "sUrbanoCloud", "template": mqtt_broker_1_6_template_id, "ip": f"{URBANO_BROKER_NAME[1]}/20", "gw": "192.168.0.1"}, 

    {"type": "router", "name": "rHacker", "coord_x": 8, "coord_y": 8, "conexion": "sEast", "template": router_template_id},
    {"type": "switch", "name": "sHacker", "coord_x": 8, "coord_y": 12, "conexion": "rHacker", "template": switch_template_id},
    {"type": "host", "name": "scanner", "coord_x": 8, "coord_y": 16, "conexion": "sHacker", "template": scanner_template_id, "ip": "192.168.33.10/24", "gw": "192.168.33.1"}, 
    {"type": "host", "name": "mqtt_attacks", "coord_x": 12, "coord_y": 16, "conexion": "sHacker", "template": mqtt_attacks_template_id, "ip": "192.168.33.11/24", "gw": "192.168.33.1"}, 
]

# Crear nodos
for node in topology_nodes:
    nodo_cx = nodes_list[node["conexion"]]["node"]
    nodo_cx_freeport = nodes_list[node["conexion"]]["freeport"]
    if node["type"] != "cluster":
        coord = Position(coord_base.x + project.grid_unit * node["coord_x"], coord_base.y + project.grid_unit * node["coord_y"])
        new_nodo = create_node(server, project, coord.x, coord.y, node["template"])
        nodes_list[node["name"]] = {"node": new_nodo,"freeport": 0}
        new_nodo_freeport = nodes_list[node["name"]]["freeport"]
        # El orden logico es usar switch -> dispositivo
        create_link(server, project, nodo_cx["node_id"], nodo_cx_freeport, new_nodo["node_id"], new_nodo_freeport)
        # Sumamos para no reutilizar los puertos
        nodes_list[node["name"]]["freeport"] += 1
        if node["type"] == "host":
            dns_addr = lab_dns_addr
            if node["name"] == "dns":
                dns_addr = "127.0.0.1"
            set_node_network_interfaces(server, project, new_nodo["node_id"], "eth0", ipaddress.IPv4Interface(node["ip"]), node["gw"], dns_addr)
    else:   
        cluster = create_cluster_of_nodes(
            server,                         # Conexión al servidor GNS3
            project,                        # Proyecto actual
            node["numNodos"],                              # Número de nodos a crear
            coord_base.x + project.grid_unit * node["coord_x"],   # Coordenada X inicial
            coord_base.y + project.grid_unit * node["coord_y"],   # Coordenada Y inicial
            5,                             # Separación vertical entre nodos
            switch_template_id,            # Plantilla del switch que conecta los nodos
            node["template"],              # Plantilla de los nodos (con DTLS)
            nodo_cx["node_id"],            # ID del switch donde se conectan
            nodo_cx_freeport,                    # Puerto inicial en el switch
            ipaddress.IPv4Interface(node["ip"]), # IP inicial para nodos
            node["gw"],                 # Gateway
            lab_dns_addr,               # DNS
            1.5                         # Separación horizontal entre nodos
        )
        for d in cluster[1]:
            env = environment_string_to_dict(get_docker_node_environment(server, project, d["node_id"]))
            env["MQTT_BROKER_ADDR"] = node["broker"]
            env["TLS"] = node.get("tls", "")
            # See the file Dockerfiles/iot/mqtt_broker/mosquitto_1.6.auth.passwd
            env["MQTT_AUTH"] = node.get("auth", "")
            env["NTP_SERVER"] = NTP_CLOUD_NAME[0]
            update_docker_node_environment(server, project, d["node_id"], environment_dict_to_string(env))
    # Sumamos para no reutilizar los puertos
    nodes_list[node["conexion"]]["freeport"] += 1

# Config scripts
routers_zone = [nodes_list[node["name"]]["node"] for node in topology_nodes if node["type"] == "router"]
router_configs = [f"../router/locations/{node["name"]}.sh" for node in topology_nodes if node["type"] == "router"]

if AUTO_CONFIGURE_ROUTERS:
    for router_node, router_config in zip(routers_zone, router_configs):
        print(f"Installing {router_node['name']}")
        hostname, port = get_node_telnet_host_port(server, project, router_node["node_id"])
        terminal_cmd = f"konsole -e telnet {hostname} {port}"
        start_node(server, project, router_node["node_id"])
        install_vyos_image_on_node(router_node["node_id"], hostname, port, pre_exec=terminal_cmd)
        # time to close the terminals, else Telnet throws EOF errors
        time.sleep(10)
        print(f"Configuring {router_node['name']} with {router_config}")
        start_node(server, project, router_node["node_id"])
        configure_vyos_image_on_node(router_node["node_id"], hostname, port, router_config, pre_exec=terminal_cmd)
        time.sleep(10)


EXTRA_HOSTS = {NTP_CLOUD_NAME[0]: NTP_CLOUD_NAME[1],
               URBANO_BROKER_NAME[0]: URBANO_BROKER_NAME[1], #  MQTT
               INDUSTRIAL_TLS_BROKER_NAME[0]: INDUSTRIAL_TLS_BROKER_NAME[1], # MQTT
               INDUSTRIAL_AUTH_BROKER_NAME[0]: INDUSTRIAL_AUTH_BROKER_NAME[1]} # mqtt

update_docker_node_extrahosts(server, project, nodes_list["dns"]["node"]["node_id"], extrahosts_dict_to_string(EXTRA_HOSTS))

## Otras gestiones

check_ipaddrs(server, project)


    # # decoration
    # payload = {"x": int(start_x + project.grid_unit * spacing), "y": int(start_y - 15),
    #            "svg": f"<svg><text font-family=\"monospace\" font-size=\"12\">Start addr: {node_start_ip_iface.ip}/{node_start_ip_iface.netmask}</text></svg>"}
    # req = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/drawings", data=json.dumps(payload), auth=(server.user, server.password))
    # req.raise_for_status()

    # payload = {"x": int(start_x + project.grid_unit * spacing), "y": int(start_y),
    #            "svg": f"<svg><text font-family=\"monospace\" font-size=\"12\">End addr  : {device_ip_iface.ip}/{device_ip_iface.netmask}</text></svg>"}
    # req = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/drawings", data=json.dumps(payload), auth=(server.user, server.password))
    # req.raise_for_status()

    # payload = {"x": int(start_x + project.grid_unit * spacing), "y": int(start_y + 15),
    #            "svg": f"<svg><text font-family=\"monospace\" font-size=\"12\">Gateway   : {gateway}</text></svg>"}
    # req = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/drawings", data=json.dumps(payload), auth=(server.user, server.password))
    # req.raise_for_status()

    # payload = {"x": int(start_x + project.grid_unit * spacing), "y": int(start_y + 30),
    #            "svg": f"<svg><text font-family=\"monospace\" font-size=\"12\">Nameserver: {nameserver}</text></svg>"}
    # req = requests.post(f"http://{server.addr}:{server.port}/v2/projects/{project.id}/drawings", data=json.dumps(payload), auth=(server.user, server.password))
    # req.raise_for_status()
