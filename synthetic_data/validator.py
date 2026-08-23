import pandas as pd

# Load data
nodes = pd.read_csv("artifacts/synthetic_graph/nodes.csv")

# Filter only Person nodes
persons = nodes[nodes["entity_type"] == "Person"]

print("=" * 50)
print("REPEAT OFFENDER CLUSTERS")
print("=" * 50)

repeat = persons["repeat_cluster_id"].dropna().value_counts()

print(repeat.head(15))
print(f"\nTotal repeat clusters: {len(repeat)}")
print(f"Persons in repeat clusters: {repeat.sum()}")

print("\n" + "=" * 50)
print("SHARED PHONE CLUSTERS")
print("=" * 50)

phones = persons["shared_phone_cluster_id"].dropna().value_counts()

print(phones.head(15))
print(f"\nTotal shared phone clusters: {len(phones)}")
print(f"Persons sharing phones: {phones.sum()}")

print("\n" + "=" * 50)
print("SHARED VEHICLE CLUSTERS")
print("=" * 50)

vehicles = persons["shared_vehicle_cluster_id"].dropna().value_counts()

print(vehicles.head(15))
print(f"\nTotal shared vehicle clusters: {len(vehicles)}")
print(f"Persons sharing vehicles: {vehicles.sum()}")

print("\n" + "=" * 50)
print("SHARED ADDRESS CLUSTERS")
print("=" * 50)

addresses = persons["shared_address_cluster_id"].dropna().value_counts()

print(addresses.head(15))
print(f"\nTotal shared address clusters: {len(addresses)}")
print(f"Persons sharing addresses: {addresses.sum()}")

print("\n" + "=" * 50)
print("SAMPLE ASSIGNED CASE IDS")
print("=" * 50)

print(persons["assigned_case_ids"].dropna().head(10))