FROM ubuntu:focal

RUN apt update && DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
    python3 \
    python3-pip \
    tshark \
    git \
    ca-certificates \
    nano \
    && rm -rf /var/lib/apt/lists/*

#RUN pip3 install --no-cache-dir paho-mqtt fpdf2 pyshark
RUN pip3 install --no-cache-dir paho-mqtt==1.6.1 fpdf2 pyshark

RUN git clone https://github.com/GenjiM1n4moto/SlowTT-Attack.git &&\
    # git clone https://github.com/etactica/mqtt-malaria.git &&\
    git clone https://github.com/stfbk/mqttsa.git

COPY --from=iotsim/certificates:latest /artifacts/pki/iot-sim-ca.crt /iot-sim-ca.crt

CMD ["/bin/bash"]