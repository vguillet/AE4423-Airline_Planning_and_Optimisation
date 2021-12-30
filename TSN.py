from Data_processor import Data_reader


class Time_space_network:
    def __init__(self, timestep_count):
        self.network = []

        self.flight_arc_lst = []
        self.ground_arc_lst = []
        self.ns_arc_lst = []

        self.data = Data_reader()

        for _ in range(timestep_count):
            self.add_timestep()

        self.add_ns_arcs()

    def add_timestep(self):
        # -> Creating timestep node layer
        network_layer = {}

        for airport_ref in self.data.airport_dict.keys():
            network_layer[airport_ref] = Node(airport_ref=airport_ref,
                                              TSN=self)

        self.network.append(network_layer)

    def add_ns_arcs(self):
        for request_id, request in self.data.request_dict.items():
            ns_arc = Arc(type="NS",
                         origin=request["airport_O"],
                         destination=request["airport_D"],
                         request_id=request_id)

            # -> Add arc to origin node
            self.network[request["release_stamp"]][request["airport_O"]].ns_arc_lst.append(ns_arc)

            # -> Add arc to destination node
            self.network[request["due_stamp"]][request["airport_D"]].ns_arc_lst.append(ns_arc)

            # -> Add arc to overall arc list
            self.ns_arc_lst.append(ns_arc)


class Node:
    def __init__(self, airport_ref, TSN):
        self.airport_ref = airport_ref
        self.timestep = len(TSN.network)
        self.node_ref = f"{self.timestep}-{self.airport_ref}"

        self.flight_arc_lst = []
        self.ground_arc_lst = []
        self.ns_arc_lst = []

        self.connect_node(TSN=TSN)

    def __str__(self):
        return f"Node: {self.node_ref}"

    def __repr__(self):
        return self.__str__()

    def connect_node(self, TSN: Time_space_network):
        if len(TSN.network) != 0:
            # Iterating through all networks timesteps backward
            for timestep in range(len(TSN.network)-1, -1, -1):
                delta_t = (self.timestep - timestep) * TSN.data.timestep_duration

                # -> Limiting node parsing to maximum arc duration
                if delta_t < TSN.data.max_arc_time + TSN.data.timestep_duration:
                    # -> Connect every node
                    for node_ref, node in TSN.network[timestep].items():

                        # -> Add ground arc
                        if self.airport_ref == node.airport_ref:
                            if delta_t == TSN.data.timestep_duration:
                                new_ground_arc = Arc(type="Ground",
                                                     origin=node.node_ref,
                                                     destination=self.node_ref)

                                TSN.ground_arc_lst.append(new_ground_arc)
                                self.ground_arc_lst.append(new_ground_arc)

                        # -> Add flight arcs
                        elif TSN.data.duration_df.loc[node.airport_ref, self.airport_ref] == delta_t:
                            # -> If arc is viable
                            if TSN.data.OD_df.loc[node.airport_ref, self.airport_ref] == 1:
                                new_flight_arc = Arc(type="Flight",
                                                     origin=node.node_ref,
                                                     destination=self.node_ref)

                                # -> Add arc to origin node
                                node.flight_arc_lst.append(new_flight_arc)  # Start (previous) node

                                # -> Add arc to destination node
                                self.flight_arc_lst.append(new_flight_arc)  # End (current) node

                                # -> Add arc to overall arc list
                                TSN.flight_arc_lst.append(new_flight_arc)

                else:
                    break


class Arc:
    def __init__(self, type, origin, destination, request_id=None):
        self.type = type
        self.origin = origin
        self.destination = destination
        self.request_id = request_id

        self.ac1_used = None
        self.ac2_used = None

    def __str__(self):
        if self.request_id is None:
            return f"Arc: {self.type} - {self.origin}->{self.destination}"
        else:
            return f"Arc: {self.type} (id:{self.request_id}) - {self.origin}->{self.destination}"

    def __repr__(self):
        return self.__str__()


if __name__ == '__main__':
    net = Time_space_network(timestep_count=25)
    print(net.network)

    node_count = 0
    for timestep in range(len(net.network)):
        if 10 < timestep < 15:
            print(len(net.network[timestep]["LUX"].flight_arc_lst))

        node_count += len(net.network[timestep])

    print(f"Node count: {node_count}")
    print(f"Flight arcs count: {len(net.flight_arc_lst)}")
    print(f"Ground arcs count: {len(net.ground_arc_lst)}")
    print(f"NS arcs count: {len(net.ns_arc_lst)}")

    print(f"Flight arcs: {net.flight_arc_lst}")
    print(f"Ground arcs: {net.ground_arc_lst}")
    print(f"NS arcs: {net.ns_arc_lst}")
