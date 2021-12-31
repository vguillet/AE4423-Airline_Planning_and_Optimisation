from Data_processor import Data_processor


class Time_space_network:
    def __init__(self):
        self.network = []

        self.flight_arc_lst = []
        self.ground_arc_lst = []
        self.ns_arc_lst = []

        self.data = Data_processor()
        timestep_count = int(self.data.planning_horizon/self.data.timestep_duration + 1)

        for _ in range(timestep_count):
            self.add_timestep()

        self.add_ns_arcs()

    @property
    def arc_lst(self):
        return self.flight_arc_lst + self.ground_arc_lst + self.ns_arc_lst

    def add_timestep(self):
        # -> Creating timestep node layer
        network_layer = {}

        for airport_ref in self.data.airport_dict.keys():
            network_layer[airport_ref] = Node(airport_ref=airport_ref,
                                              TSN=self)

        self.network.append(network_layer)

    def add_ns_arcs(self):
        for request_id, request in self.data.request_dict.items():
            start_node = self.network[request["release_step"]][request["airport_O"]]
            end_node = self.network[request["due_step"]][request["airport_D"]]

            ns_arc = Arc(type="NS",
                         origin=start_node.ref,
                         origin_timestep=start_node.timestep, # TODO: double check if release step == this
                         destination=end_node.ref,
                         destination_timestep=end_node.timestep, # TODO: double check if due step == this
                         request_id=request_id)

            # -> Add arc to origin node
            start_node.out_ns_arc_lst.append(ns_arc)

            # -> Add arc to destination node
            end_node.in_ns_arc_lst.append(ns_arc)

            # -> Add arc to overall arc list
            self.ns_arc_lst.append(ns_arc)


class Node:
    def __init__(self, airport_ref, TSN):
        self.airport_ref = airport_ref
        self.timestep = len(TSN.network)
        self.ref = f"{self.timestep}-{self.airport_ref}"

        self.out_flight_arc_lst = []
        self.out_ground_arc_lst = []
        self.out_ns_arc_lst = []

        self.in_flight_arc_lst = []
        self.in_ground_arc_lst = []
        self.in_ns_arc_lst = []

        self.v = self.build_v(TSN=TSN)
        self.connect_node(TSN=TSN)

    def __str__(self):
        return f"Node: {self.ref}"

    def __repr__(self):
        return self.__str__()

    @property
    def in_arc_lst(self):
        return self.in_flight_arc_lst + self.in_ground_arc_lst + self.in_ns_arc_lst

    @property
    def out_arc_lst(self):
        return self.out_flight_arc_lst + self.out_ground_arc_lst + self.out_ns_arc_lst

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
                                                     origin=node.ref,
                                                     origin_timestep=node.timestep,
                                                     destination=self.ref,
                                                     destination_timestep=self.timestep)

                                # -> Add arc to origin node
                                node.out_ground_arc_lst.append(new_ground_arc)  # Start (previous) node

                                # -> Add arc to destination node
                                self.in_ground_arc_lst.append(new_ground_arc)  # End (current) node

                                # -> Add arc to overall arc list
                                TSN.ground_arc_lst.append(new_ground_arc)

                        # -> Add flight arcs
                        elif TSN.data.duration_df.loc[node.airport_ref, self.airport_ref] == delta_t:
                            # -> If arc is viable
                            if TSN.data.OD_df.loc[node.airport_ref, self.airport_ref] == 1:
                                new_flight_arc = Arc(type="Flight",
                                                     origin=node.ref,
                                                     origin_timestep=node.timestep,
                                                     destination=self.ref,
                                                     destination_timestep=self.timestep)

                                # -> Add arc to origin node
                                node.out_flight_arc_lst.append(new_flight_arc)  # Start (previous) node

                                # -> Add arc to destination node
                                self.in_flight_arc_lst.append(new_flight_arc)  # End (current) node

                                # -> Add arc to overall arc list
                                TSN.flight_arc_lst.append(new_flight_arc)

                else:
                    break

    def build_v(self, TSN: Time_space_network):
        v = {}
        for r, request in TSN.data.request_dict.items():
            if request["release_step"] == self.timestep and request["airport_O"] == self.airport_ref:
                v[r] = -1
            elif request["due_step"] == self.timestep and request["airport_D"] == self.airport_ref:
                v[r] = 1
            else:
                v[r] = 0
        return v



class Arc:
    def __init__(self, type, origin, origin_timestep, destination, destination_timestep, request_id=None):
        self.type = type

        self.origin = origin
        self.origin_timestep = origin_timestep

        self.destination = destination
        self.destination_timestep = destination_timestep

        self.request_id = request_id

        if self.request_id is None:
            self.ref = f"Arc: {self.type} - {self.origin}->{self.destination}"
        else:
            self.ref = f"Arc: {self.type} (id:{self.request_id}) - {self.origin}->{self.destination}"

        self.ac1_used = None
        self.ac2_used = None

    def __str__(self):
        return self.ref

    def __repr__(self):
        return self.__str__()


if __name__ == '__main__':
    net = Time_space_network()
    print(net.network)

    node_count = 0
    for timestep in range(len(net.network)):
        if 10 < timestep < 15:
            print(len(net.network[timestep]["LUX"].in_flight_arc_lst) + len(net.network[timestep]["LUX"].out_flight_arc_lst))

        node_count += len(net.network[timestep])

    print(f"Node count: {node_count}")
    print(f"Flight arcs count: {len(net.flight_arc_lst)}")
    print(f"Ground arcs count: {len(net.ground_arc_lst)}")
    print(f"NS arcs count: {len(net.ns_arc_lst)}")

    print(f"Flight arcs: {net.flight_arc_lst}")
    print(f"Ground arcs: {net.ground_arc_lst}")
    print(f"NS arcs: {net.ns_arc_lst}")
