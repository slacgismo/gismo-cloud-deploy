class Node(object):
    def __init__(
        self, nodegroup, cluster, hostname, instance_type, region, status, status_type
    ):
        self.nodegroup = nodegroup
        self.cluster = cluster
        self.hostname = hostname
        self.instance_type = instance_type
        self.region = region
        self.status = status
        self.status_type = status_type
