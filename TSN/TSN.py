from data_processor import Data_reader


class Time_space_network:
    def __init__(self, timestep_count):
        self.timestep_duration = 4  # h TODO: Check unit

        self.network = []

        self.flight_arc_lst = []
        self.ground_arc_lst = []
        self.ns_arc_lst = []

        self.data = Data_reader()

        for _ in range(timestep_count):
            self.add_timestep()

        return

    def add_timestep(self):
        # -> Creating timestep node layer
        network_layer = {}

        for airport_ref in self.data.airport_dict.keys():
            network_layer[airport_ref] = Node(airport_ref=airport_ref,
                                              TSN=self)

        self.network.append(network_layer)
        return


class Node:
    def __init__(self, airport_ref, TSN):
        self.airport_ref = airport_ref
        self.timestep = len(TSN.network) + 1
        self.node_ref = f"{self.timestep}-{self.airport_ref}"

        self.flight_arc_lst = []
        self.ground_arc_lst = []
        self.ns_arc_lst = []

        self.connect_node(TSN=TSN)

    def connect_node(self, TSN):
        if len(TSN.network) != 0:
            # Iterating through all networks timesteps backward
            for timestep in range(len(TSN.network), 0, -1):
                delta_time = (self.timestep - timestep) * TSN.timestep_duration

                for node_ref, node in TSN.network[timestep].items():

                    # -> Add ground arc
                    if self.airport_ref == node.airport_ref and delta_time == TSN.timestep_duration:
                        new_ground_arc = Arc(origin=node.node_ref,
                                             destination=self.node_ref)

                        TSN.ground_arc_lst.append(new_ground_arc)
                        self.ground_arc_lst.append(new_ground_arc)

                    # -> Add flight arcs
                    elif ...
                        new_flight_arc = Arc(origin=node.node_ref,
                                             destination=self.node_ref)

                        TSN.flight_arc_lst.append(new_flight_arc)
                        self.flight_arc_lst.append(new_flight_arc)

                    pass
        return



class Arc:
    def __init__(self, origin, destination):
        self.origin = origin
        self.destination = destination

        self.ac1_used = None
        self.ac2_used = None

if __name__ == '__main__':
    net = Time_space_network(timestep_count=10)
    print(net.network)
