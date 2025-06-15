"""Refactorized script to create the Gotham IoT simulation topology."""

import configparser
import ipaddress
import sys
import time

from gns3utils import *

PROJECT_NAME = "CoAP_scenario"
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
# NTP_template_id = get_template_id_from_name(templates, "iotsim-ntp")
# assert NTP_template_id

city_power_template_id = get_template_id_from_name(templates, "iotsim-city-power")
assert city_power_template_id
city_power_tls_template_id = get_template_id_from_name(templates, "iotsim-city-power-tls")
assert city_power_tls_template_id
combined_cycle_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle")
assert combined_cycle_template_id
combined_cycle_tls_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle-tls")
assert combined_cycle_tls_template_id
city_power_cloud_template_id = get_template_id_from_name(templates, "iotsim-city-power-cloud")
assert city_power_cloud_template_id
combined_cycle_cloud_template_id = get_template_id_from_name(templates, "iotsim-combined-cycle-cloud")
assert combined_cycle_cloud_template_id

scanner_template_id = get_template_id_from_name(templates, "iotsim-scanner")
assert scanner_template_id
amplification_coap_template_id = get_template_id_from_name(templates, "iotsim-amplification-coap")
assert amplification_coap_template_id

# Config file
sim_config = configparser.ConfigParser()
with open("../iot-coap-sim.config", "r", encoding="utf-8") as cf:
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
#NTP_CLOUD_NAME = (f"ntp.{sim_config['LOCAL_DOMAIN']}", "192.168.0.3")

topology_nodes = [
    {"type": "router", "name": "rGetafe", "coord_x": -10, "coord_y": 8, "conexion": "sWest", "template": router_template_id},
    {"type": "router", "name": "rLeganes", "coord_x": 0, "coord_y": 8, "conexion": "sWest", "template": router_template_id},
    {"type": "router", "name": "rHacker", "coord_x": 6, "coord_y": 8, "conexion": "sEast", "template": router_template_id},
    {"type": "switch", "name": "sGetafe", "coord_x": -10, "coord_y": 12, "conexion": "rGetafe", "template": switch_template_id},
    {"type": "switch", "name": "sLeganes", "coord_x": 0, "coord_y": 12, "conexion": "rLeganes", "template": switch_template_id},
    {"type": "switch", "name": "sHacker", "coord_x": 6, "coord_y": 12, "conexion": "rHacker", "template": switch_template_id},
    {"type": "switch", "name": "sInfoCloud", "coord_x": 6, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "host", "name": "dns", "coord_x": 6, "coord_y": -12, "conexion": "sInfoCloud", "template": DNS_template_id, "ip": f"{lab_dns_addr}/20", "gw": "192.168.0.1"},
    #{"type": "host", "name": "ntp", "coord_x": 30, "coord_y": -10, "conexion": "sInfoCloud", "template": NTP_template_id, "ip": f"{NTP_CLOUD_NAME[1]}/20", "gw": "192.168.0.1"}, 
    {"type": "host", "name": "scanner", "coord_x": 6, "coord_y": 16, "conexion": "sHacker", "template": scanner_template_id, "ip": "192.168.33.10/24", "gw": "192.168.33.1"}, 
    {"type": "host", "name": "amplification_coap", "coord_x": 11, "coord_y": 16, "conexion": "sHacker", "template": amplification_coap_template_id, "ip": "192.168.33.11/24", "gw": "192.168.33.1"}, 
    {"type": "cluster", "name": "comb_cycle_tls", "coord_x": 5, "coord_y": 16, "conexion": "sLeganes", "numNodos": 2, "template": combined_cycle_tls_template_id, "ip": "192.168.18.20/24", "gw": "192.168.18.1"}, 
    {"type": "cluster", "name": "comb_cycle", "coord_x": -5, "coord_y": 16, "conexion": "sGetafe", "numNodos": 2, "template": combined_cycle_template_id, "ip": "192.168.17.20/24", "gw": "192.168.17.1"}, 
    {"type": "cluster", "name": "city_power_tls", "coord_x": 0, "coord_y": 16, "conexion": "sLeganes", "numNodos": 2, "template": city_power_tls_template_id, "ip": "192.168.18.10/24", "gw": "192.168.18.1"}, 
    {"type": "cluster", "name": "city_power", "coord_x": -10, "coord_y": 16, "conexion": "sGetafe", "numNodos": 2, "template": city_power_template_id, "ip": "192.168.17.10/24", "gw": "192.168.17.1"}, 
    {"type": "switch", "name": "sLeganesCloud", "coord_x": -6, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "switch", "name": "sGetafeCloud", "coord_x": 0, "coord_y": -8, "conexion": "sNorth", "template": switch_template_id},
    {"type": "cloud", "name": "comb_cycle_cloud", "coord_x": -2, "coord_y": -12, "conexion": "sGetafeCloud", "template": combined_cycle_cloud_template_id, "ip": "192.168.1.1/20", "gw": "192.168.0.1", "cluster": "comb_cycle"}, 
    {"type": "cloud", "name": "city_power_cloud", "coord_x": 2, "coord_y": -12, "conexion": "sGetafeCloud", "template": city_power_cloud_template_id, "ip": "192.168.1.2/20", "gw": "192.168.0.1", "cluster": "city_power"}, 
    {"type": "cloud", "name": "comb_cycle_tls_cloud", "coord_x": -8, "coord_y": -12, "conexion": "sLeganesCloud", "template": combined_cycle_cloud_template_id, "ip": "192.168.2.1/20", "gw": "192.168.0.1", "cluster": "comb_cycle_tls"}, 
    {"type": "cloud", "name": "city_power_tls_cloud", "coord_x": -4, "coord_y": -12, "conexion": "sLeganesCloud", "template": city_power_cloud_template_id, "ip": "192.168.2.2/20", "gw": "192.168.0.1", "cluster": "city_power_tls"}, 
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
        elif node["type"] == "cloud":
            set_node_network_interfaces(server, project, new_nodo["node_id"], "eth0", ipaddress.IPv4Interface(node["ip"]), node["gw"], lab_dns_addr)
            cluster_ip = nodes_list[node["cluster"]]["ip"]
            cluster_numNodos = nodes_list[node["cluster"]]["numNodos"] - 1
            ip_sin_mask = cluster_ip.split("/")[0]
            partes_ip = ip_sin_mask.split(".")
            base_last_ip = ".".join(partes_ip[:3])
            last_ip = int(partes_ip[-1]) + cluster_numNodos
            ip_list = ip_sin_mask + "-" + base_last_ip + "." + str(last_ip)
            env = environment_string_to_dict(get_docker_node_environment(server, project, new_nodo["node_id"])) 
            env["COAP_ADDR_LIST"] = ip_list
            update_docker_node_environment(server, project, new_nodo["node_id"], environment_dict_to_string(env))
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
        nodes_list[node["name"]] = {"ip": node["ip"],"numNodos": node["numNodos"]}
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

## Otras gestiones
node = nodes_list["city_power_tls_cloud"]["node"]
env = environment_string_to_dict(get_docker_node_environment(server, project, node["node_id"])) 
env["PSK"] = "True"
update_docker_node_environment(server, project, node["node_id"], environment_dict_to_string(env))

node = nodes_list["comb_cycle_tls_cloud"]["node"]
env = environment_string_to_dict(get_docker_node_environment(server, project, node["node_id"])) 
env["PSK"] = "True"
update_docker_node_environment(server, project, node["node_id"], environment_dict_to_string(env))

check_ipaddrs(server, project)
