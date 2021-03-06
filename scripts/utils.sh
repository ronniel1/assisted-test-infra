#!/usr/bin/env bash

set -o nounset

export KUBECONFIG=${KUBECONFIG:-$HOME/.kube/config}
export NAMESPACE=${NAMESPACE:-assisted-installer}

function get_namespace_index() {
    namespace=$1
    oc_flag=${2:-}

    index=$(skipper run python3 scripts/indexer.py --action set --namespace $namespace $oc_flag)
    if [[ -z $index ]]; then
        all_namespaces=$(skipper run python3 scripts/indexer.py --action list)
        echo "Maximum number of namespaces allowed are currently running: $all_namespaces"
        echo "Please remove an old namespace in order to create a new one, run:"
        echo "make delete_minikube_profile NAMESPACE=<namespace>"
        exit 1
    fi

    echo $index
}

function print_log() {
    echo "$(basename $0): $1"
}

function url_reachable() {
    curl -s $1 --max-time 4 >/dev/null
    return $?
}

function spawn_port_forwarding_command() {
    service_name=$1
    external_port=$2
    namespace=$3
    namespace_index=$4
    profile=$5

    filename=${service_name}__${namespace}__${namespace_index}__assisted_installer

    cat <<EOF >build/xinetd-$filename
service ${service_name}
{
  flags		= IPv4
  bind		= 0.0.0.0
  type		= UNLISTED
  socket_type	= stream
  protocol	= tcp
  user		= root
  wait		= no
  redirect	= $(minikube -p $profile ip) $(kubectl --server $(get_profile_url $profile) --kubeconfig=${KUBECONFIG} get svc/${service_name} -n ${NAMESPACE} -o=jsonpath='{.spec.ports[0].nodePort}')
  port		= ${external_port}
  only_from	= 0.0.0.0/0
  per_source	= UNLIMITED
  instances	= UNLIMITED
}
EOF
    sudo mv build/xinetd-$filename /etc/xinetd.d/$filename --force
    sudo systemctl restart xinetd
}

function run_in_background() {
    bash -c "nohup $1  >/dev/null 2>&1 &"
}

function kill_port_forwardings() {
    services=$1
    sudo systemctl stop xinetd
    for s in $services; do
        for f in $(sudo ls /etc/xinetd.d/ | grep $s); do
            sudo rm -f /etc/xinetd.d/$f
        done
    done
}

function get_main_ip() {
    echo "$(ip route get 1 | sed 's/^.*src \([^ ]*\).*$/\1/;q')"
}

function wait_for_url_and_run() {
    RETRIES=15
    RETRIES=$((RETRIES))
    STATUS=1
    url_reachable "$1" && STATUS=$? || STATUS=$?

    until [ $RETRIES -eq 0 ] || [ $STATUS -eq 0 ]; do

        RETRIES=$((RETRIES - 1))

        echo "Running given function"
        $2

        echo "Sleeping for 30 seconds"
        sleep 30s

        echo "Verifying URL and port are accessible"
        url_reachable "$1" && STATUS=$? || STATUS=$?
    done
    if [ $RETRIES -eq 0 ]; then
        echo "Timeout reached, URL $1 not reachable"
        exit 1
    fi
}

function close_external_ports() {
    ports=$1
    for p in $ports; do
        sudo firewall-cmd --zone=public --remove-port=$p/tcp
    done
}

function add_firewalld_port() {
    port=$1
    if [ "${EXTERNAL_PORT}" = "y" ]; then
        echo "configuring external ports"
        sudo firewall-cmd --zone=public --add-port=$port/tcp
    fi
    echo "configuring libvirt zone ports ports"
    sudo firewall-cmd --zone=libvirt --add-port=$port/tcp
}

function as_singleton() {
    func=$1
    interval=${2:-15s}

    lockfile=/tmp/$func.lock

    while [ -e "$lockfile" ]; do
        echo "Can run only one instance of $func at a time..."
        echo "Waiting for other instances of $func to be completed..."
        sleep $interval
    done

    trap 'rm "$lockfile"; exit' EXIT INT TERM HUP
    touch $lockfile

    $func
}

function get_profile_url() {
    profile=$1
    echo https://$(minikube ip --profile $profile):8443
}


function validate_namespace() {
    namespace=$1
    if [[ $namespace =~ ^[0-9a-zA-Z\-]+$ ]]; then
        return
    fi
    echo "Invalid namespace '$namespace'"
    echo "It can contain only letters, numbers and '-'"
    exit 1
}

function get_profile_url() {
    profile=$1
    echo https://$(minikube ip --profile $profile):8443
}

"$@"
