import pytest

from tests.base_test import BaseTest


class TestCancelReset(BaseTest):
    @pytest.mark.regression
    def test_cancel_reset_before_node_boot(self, api_client, node_controller):
        # Define new cluster
        cluster_id = self.create_cluster(api_client=api_client).id
        # Generate and download cluster ISO
        self.generate_and_download_image(cluster_id=cluster_id, api_client=api_client)
        # Boot nodes into ISO
        node_controller.start_all_nodes()
        # Wait until hosts are discovered and update host roles
        self.wait_until_hosts_are_discovered(cluster_id=cluster_id, api_client=api_client)
        self.set_host_roles(cluster_id=cluster_id, api_client=api_client)
        self.set_ingress_and_api_vips(cluster_id=cluster_id,
                                      api_client=api_client,
                                      controller=node_controller
                                      )
        # Start cluster install
        self.start_cluster_install(cluster_id=cluster_id, api_client=api_client)
        # Cancel cluster install once cluster installation start
        self.wait_for_installing_in_progress(cluster_id=cluster_id, api_client=api_client)
        self.cancel_cluster_install(cluster_id=cluster_id, api_client=api_client)
        assert self.is_cluster_in_cancelled_status(
            cluster_id=cluster_id,
            api_client=api_client
        )
        # Reset cluster install
        self.reset_cluster_install(cluster_id=cluster_id, api_client=api_client)
        assert self.is_cluster_in_insufficient_status(
            cluster_id=cluster_id,
            api_client=api_client
        )
        # Reboot required nodes into ISO
        self.reboot_required_nodes_into_iso_after_reset(
            cluster_id=cluster_id,
            api_client=api_client,
            controller=node_controller
        )
        # Wait for hosts to be rediscovered
        self.wait_until_hosts_are_discovered(cluster_id=cluster_id, api_client=api_client)
        self.wait_until_cluster_is_ready_for_install(cluster_id=cluster_id, api_client=api_client)
        # Install Cluster
        self.start_cluster_install(cluster_id=cluster_id, api_client=api_client)
        # wait until all nodes are in Installed status, will fail in case one host in error
        self.wait_for_nodes_to_install(cluster_id=cluster_id, api_client=api_client)
        self.wait_for_cluster_to_install(cluster_id=cluster_id, api_client=api_client)

    @pytest.mark.regression
    def test_cancel_reset_after_node_boot(self, api_client, node_controller):
        cluster_id = self.create_cluster(api_client=api_client).id
        self.generate_and_download_image(cluster_id=cluster_id, api_client=api_client)
        node_controller.start_all_nodes()
        self.wait_until_hosts_are_discovered(cluster_id=cluster_id, api_client=api_client)
        self.set_host_roles(cluster_id=cluster_id, api_client=api_client)
        self.set_ingress_and_api_vips(cluster_id=cluster_id,
                                      api_client=api_client,
                                      controller=node_controller
                                      )
        self.start_cluster_install(cluster_id=cluster_id, api_client=api_client)
        # Cancel cluster install once at least one host booted
        self.wait_for_one_host_to_boot_during_install(cluster_id=cluster_id, api_client=api_client)
        self.cancel_cluster_install(cluster_id=cluster_id, api_client=api_client)
        assert self.is_cluster_in_cancelled_status(
            cluster_id=cluster_id,
            api_client=api_client
        )
        # Reset cluster install
        self.reset_cluster_install(cluster_id=cluster_id, api_client=api_client)
        assert self.is_cluster_in_insufficient_status(
            cluster_id=cluster_id,
            api_client=api_client
        )
        # Reboot required nodes into ISO
        self.reboot_required_nodes_into_iso_after_reset(
            cluster_id=cluster_id,
            api_client=api_client,
            controller=node_controller
        )
        # Wait for hosts to be rediscovered
        self.wait_until_hosts_are_discovered(cluster_id=cluster_id, api_client=api_client)
        self.wait_until_cluster_is_ready_for_install(cluster_id=cluster_id, api_client=api_client)
        # Install Cluster
        self.start_cluster_install(cluster_id=cluster_id, api_client=api_client)
        self.wait_for_nodes_to_install(cluster_id=cluster_id, api_client=api_client)
        self.wait_for_cluster_to_install(cluster_id=cluster_id, api_client=api_client)
