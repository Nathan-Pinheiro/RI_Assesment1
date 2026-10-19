from controller import Supervisor

supervisor = Supervisor()

robot_nodes = {
    f"robot_{i}": supervisor.getFromDef(f"ROBOT_{i}")
    for i in range(5)
}