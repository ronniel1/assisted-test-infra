import os
import pytest

import utils
import consts
import assisted_service_api
from tests.conftest import env_variables

if os.environ.get('NODE_ENV') == 'QE_VM':
    from node_controlers.qe_vm_controler import QeVmController as nodeController
else:
    raise NotImplementedError


class BaseTest:
    @pytest.fixture()
    def api_client(self):
        client = assisted_service_api.create_client(env_variables['REMOTE_SERVICE_URL'])
        self.delete_cluster_if_exists(api_client=client, cluster_name=env_variables['CLUSTER_NAME'])
        return client

    @pytest.fixture()
    def node_controller(self):
        controller = nodeController()
        yield controller
        controller.shutdown_all_nodes()
        controller.format_all_node_disks()

    @staticmethod
    def create_cluster(api_client):
        return api_client.create_cluster(
            env_variables['CLUSTER_NAME'], 
            ssh_public_key=env_variables['SSH_PUBLIC_KEY'], 
            pull_secret=env_variables['PULL_SECRET'], 
            openshift_version=env_variables['OPENSHIFT_VERSION'], 
            base_dns_domain=env_variables['BASE_DOMAIN'], 
            vip_dhcp_allocation=env_variables['VIP_DHCP_ALLOCATION']
        )
    
    def delete_cluster_if_exists(self, api_client, cluster_name):
        cluster_to_delete = self.get_cluster_by_name(
            api_client=api_client, 
            cluster_name=cluster_name
        )

        if cluster_to_delete:
            api_client.delete_cluster(cluster_id=cluster_to_delete['id'])

    @staticmethod
    def get_cluster_by_name(api_client, cluster_name):
        clusters = api_client.clusters_list()
        for cluster in clusters:
            if cluster['name'] == cluster_name:
                return cluster
        return None

    @staticmethod
    def generate_and_download_image(cluster_id, api_client):
        api_client.generate_and_download_image(
            cluster_id=cluster_id, 
            ssh_key=env_variables['SSH_PUBLIC_KEY'], 
            image_path=env_variables['ISO_DOWNLOAD_PATH']
        )

    @staticmethod
    def wait_until_hosts_are_discovered(cluster_id, api_client):
        utils.wait_till_all_hosts_are_in_status(
            client=api_client, 
            cluster_id=cluster_id, 
            nodes_count=env_variables['NUM_NODES'], 
            statuses=[consts.NodesStatus.PENDING_FOR_INPUT, consts.NodesStatus.KNOWN]
        )

    @staticmethod
    def set_host_roles(cluster_id, api_client):
        utils.set_hosts_roles_based_on_requested_name(
            client=api_client,
            cluster_id=cluster_id
        )

    @staticmethod
    def set_ingress_and_api_vips(cluster_id, api_client, controller):
        vips = controller.get_ingress_and_api_vips()
        api_client.update_cluster(cluster_id, vips)

    @staticmethod
    def start_cluster_install(cluster_id, api_client):
        api_client.install_cluster(cluster_id=cluster_id)

    @staticmethod
    def cancel_cluster_install(cluster_id, api_client):
        api_client.cancel_cluster_install(cluster_id=cluster_id)

    @staticmethod
    def wait_for_installing_in_progress(cluster_id, api_client):
        utils.wait_till_at_least_one_host_is_in_status(
            client=api_client,
            cluster_id=cluster_id,
            statuses=[consts.NodesStatus.INSTALLING_IN_PROGRESS]
        )

    @staticmethod
    def wait_for_one_host_to_boot_during_install(cluster_id, api_client):
        utils.wait_till_at_least_one_host_is_in_stage(
            client=api_client,
            cluster_id=cluster_id,
            stages=[consts.HostsProgressStages.REBOOTING])

    @staticmethod
    def is_cluster_in_error_status(cluster_id, api_client):
        return utils.is_cluster_in_status(
            client=api_client,
            cluster_id=cluster_id, 
            statuses=[consts.ClusterStatus.ERROR]
        )

    @staticmethod
    def is_cluster_in_cancelled_status(cluster_id, api_client):
        return utils.is_cluster_in_status(
            client=api_client,
            cluster_id=cluster_id, 
            statuses=[consts.ClusterStatus.CANCELLED]
        )

    @staticmethod
    def reset_cluster_install(cluster_id, api_client):
        api_client.reset_cluster_install(cluster_id=cluster_id)

    @staticmethod
    def is_cluster_in_insufficient_status(cluster_id, api_client):
        return utils.is_cluster_in_status(
            client=api_client, 
            cluster_id=cluster_id, 
            statuses=[consts.ClusterStatus.INSUFFICIENT]
        )

    @staticmethod
    def is_hosts_in_wrong_boot_order(cluster_id, api_client):
        return utils.wait_till_all_hosts_are_in_status()

    @staticmethod
    def reboot_required_nodes_into_iso_after_reset(cluster_id, api_client, controller):
        nodes_to_reboot = api_client.get_hosts_in_statuses(
            cluster_id=cluster_id, 
            statuses=[consts.NodesStatus.RESETING_PENDING_USER_ACTION]
        )
        for node in nodes_to_reboot:
            node_name = node["requested_hostname"]
            controller.shutdown_node(node_name)
            controller.format_node_disk(node_name)
            controller.start_node(node_name)

    @staticmethod
    def wait_until_cluster_is_ready_for_install(cluster_id, api_client):
        utils.wait_till_cluster_is_in_status(
            client=api_client, 
            cluster_id=cluster_id,
            statuses=[consts.ClusterStatus.READY]
        )

    @staticmethod
    def wait_for_cluster_to_install(cluster_id, api_client, timeout=consts.CLUSTER_INSTALLATION_TIMEOUT):
        utils.wait_till_cluster_is_in_status(
            client=api_client, 
            cluster_id=cluster_id,
            statuses=[consts.ClusterStatus.INSTALLED],
            timeout=timeout,
        )

    @staticmethod
    def wait_for_nodes_to_install(cluster_id, api_client, timeout=consts.CLUSTER_INSTALLATION_TIMEOUT):
        utils.wait_till_all_hosts_are_in_status(
            client=api_client,
            cluster_id=cluster_id,
            statuses=[consts.ClusterStatus.INSTALLED],
            nodes_count=env_variables['NUM_NODES'],
            timeout=timeout,
        )
