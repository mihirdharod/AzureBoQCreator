#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate synthetic test fixtures for the Azure BoQ Creator Agent.

Everything here is invented. No customer hostnames, subscription IDs, cost
figures or inventories appear in this repository.

The fixtures deliberately reproduce the messy shapes seen in real workbooks,
because those are what the parsers have to survive:

  - each sheet names its columns differently
  - storage written as "1.1TB", "610GB", "2 TB - Premium SSD Managed Disks", "?"
  - non-breaking spaces and stray whitespace in cells
  - a sheet with no OS column at all
  - a trailing "Note:" row that is not a server
  - a container/PaaS sheet that should be excluded from a VM BoQ

    python tests/make_fixtures.py
"""
import os
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")
os.makedirs(OUT, exist_ok=True)


def write(wb, name):
    path = os.path.join(OUT, name)
    wb.save(path)
    print(f"wrote {os.path.relpath(path, HERE)}")


# ---------------------------------------------------------------- target list
# Already carries Azure SKUs -> parse_inventory.py
wb = openpyxl.Workbook()

ws = wb.active
ws.title = "Orders"
ws.append(["Application name", "Role", "Environment", "Server Name at Source",
           "CPU at Source", "RAM at Source", "Server Name at Target", "OS Version",
           "VM Type at Target", "Storage Disks at Target", "Subscription ID"])
for r in [
    ("Orders", "App", "PROD", "SRCORDAPP01", 8, 32, "AZWORDAPP01", "Windows Server 2022",
     "Standard_D8s_v5", "\xa0512GB", "00000000-0000-0000-0000-000000000001"),
    ("Orders", "App", "PROD", "SRCORDAPP02", 8, 32, "AZWORDAPP02", "Windows Server 2022",
     "Standard_D8s_v5", " 512GB", "00000000-0000-0000-0000-000000000001"),
    ("Orders", "DB", "PROD", "SRCORDDB01", 16, 128, "AZLORDDB01", "RHEL 9",
     "Standard_E16s_v5", "2 TB - Premium SSD Managed Disks", "00000000-0000-0000-0000-000000000001"),
    ("Orders", "App", "QA", "SRCORDAPPQ01", 8, 32, "AZWORDAPQ01", "Windows Server 2022",
     "Standard_D8s_v5", "512GB - Standard SSD Managed Disks", "00000000-0000-0000-0000-000000000002"),
    ("Orders", "App", "DEV", "SRCORDAPPD01", 4, 16, "AZWORDAPD01", "Windows Server 2022",
     "Standard_D4s_v5", "?", "00000000-0000-0000-0000-000000000002"),
]:
    ws.append(list(r))

# second sheet: different headers, no OS column at all
ws2 = wb.create_sheet("Billing")
ws2.append(["Server Role", "Server Name", "Server Name (Actual)",
            "Environment(DEV/QA/PROD)", "CPU", "RAM [GB]", "Storage Size [GB]",
            "Azure VM SKU", "Storage Media"])
for r in [
    ("App", "Billing Portal", "AZWBILAPP01", "PROD", 4, 16, 460, "Standard_F8s_v2", "PremiumSSD"),
    ("App", "Billing Portal", "AZWBILAPP02", "PROD", 4, 16, 160, "Standard_F4s_v2", "PremiumSSD"),
    ("App", "Billing Portal", "AZWBILAPT01", "Test", 4, 16, 320, "Standard_D4s_v4", "StandardSSD"),
    ("App", "Billing Portal", "AZWBILAPT02", "Test", 4, 16, "?", "Standard_D4s_v4", "StandardSSD"),
]:
    ws2.append(list(r))

# container sheet - excluded from a VM BoQ via --exclude
ws3 = wb.create_sheet("Platform")
ws3.append(["Cluster #", "VM", "CPU", "Mem", "Workload Env", "Zone1", "SKU Recommendation"])
for r in [
    ("Cluster1", "control-plane-1", "8vCPU", "32GB", "MGMT", "AZ1", "Standard_D8s_v5"),
    ("Cluster1", "control-plane-2", "8vCPU", "32GB", "MGMT", "AZ2", "Standard_D8s_v5"),
    ("Cluster1", "worker-1", "16vCPU", "128GB", "Internal STG/PRD", "AZ1", "Standard_E16s_v5"),
]:
    ws3.append(list(r))

write(wb, "sample-target-list.xlsx")


# ------------------------------------------------------------ source hardware
# Physical estate with utilisation data -> size_from_source.py
wb = openpyxl.Workbook()
HDR = ["Server", "Physical or VM", "OS", "Environment", "Total RAM GB",
       "Peak RAM Utilization GB", "Total Disk GB/TB", "Disk Utilization",
       "Total CPU", "MAX CPU Utilization", "Comment"]

ws = wb.active
ws.title = "AppTier UAT"
ws.append(HDR)
for r in [
    ("lx1appnode01", "Physical", "RHEL 8.10", "UAT", "96", "60", "1TB", "850GB", "64 Lcpu", "0.4", ""),
    ("lx1appnode02", "Physical", "RHEL 8.10", "UAT", "96", "40", "1TB", "850GB", "64 Lcpu", "0.4", ""),
    ("lx1queue01",   "Physical", "RHEL 8.10", "UAT", "16", "10", "300 GB", "280 GB", "16 Lcpu", "0.4", ""),
]:
    ws.append(list(r))
ws.append([])
ws.append(["Note: \nCPU and Memory utilization are based on historical stats"])

# heavily over-provisioned: rightsize vs lift should differ dramatically
ws2 = wb.create_sheet("Analytics UAT")
ws2.append(HDR)
for r in [
    ("lx1analytics01", "physical", "oracle Linux 8.10", "UAT", "755 GB", "150G",
     "8.79TB", "3TB", "72 Lcpu", "0.25", ""),
    ("lx1analytics02", "physical", "oracle Linux 8.10", "UAT", "755 GB", "150G",
     "8.79TB", "3TB", "72 Lcpu", "0.25", ""),
]:
    ws2.append(list(r))
ws2.append([])
ws2.append(["Note: \nCPU and Memory utilization are based on historical stats"])

ws3 = wb.create_sheet("Web UAT")
ws3.append(HDR)
for r in [
    ("wn1web01", "Physical", "Windows 2022", "UAT", "64", "55", "1TB", "650GB", "64 Lcpu", "0.8", ""),
    ("wn1web02", "Physical", "Windows 2022", "UAT", "64", "55", "1TB", "650GB", "64 Lcpu", "0.8", ""),
]:
    ws3.append(list(r))

write(wb, "sample-source-hardware.xlsx")


# ---------------------------------------------------------- exported estimate
# Mimics the calculator's export: header on row 3, "Total" label in the REGION
# column, shared services with a blank Custom name, trailing disclaimer rows.
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Sample BoQ Export"
ws.append(["Microsoft Azure Estimate"])
ws.append(["Sample estimate"])
ws.append(["Service category", "Service type", "Custom name", "Region",
           "Description", "Estimated monthly cost", "Estimated upfront cost"])

data = [
    ("Compute", "Virtual Machines", "Orders | AZWORDAPP01 | D8s v5 | Premium SSD ~512GB",
     "West Europe", "1 D8s v5 (8 vCPUs, 32 GB RAM) (3 year reserved), Windows (License included), "
     "OS Only; 1 managed disk - P20", 444.33, 0),
    ("Compute", "Virtual Machines", "Orders | AZWORDAPP02 | D8s v5 | Premium SSD ~512GB",
     "West Europe", "1 D8s v5 (8 vCPUs, 32 GB RAM) (3 year reserved), Windows (License included), "
     "OS Only; 1 managed disk - P20", 444.33, 0),
    ("Compute", "Virtual Machines", "Orders | AZLORDDB01 | E16s v5 | Premium SSD ~2048GB",
     "West Europe", "1 E16s v5 (16 vCPUs, 128 GB RAM) (3 year reserved), Linux, (Pay as you go); "
     "1 managed disk - P40", 972.09, 0),
    ("Compute", "Virtual Machines", "Billing | AZWBILAPP01 | F8s v2 | Premium SSD ~460GB",
     "West Europe", "1 F8s v2 (8 vCPUs, 16 GB RAM) (3 year savings plan), Windows (License included), "
     "OS Only; 1 managed disk - P20", 502.45, 0),
    # shared services: no Custom name, must still be counted
    ("Storage", "Storage Accounts", "", "West Europe",
     "Block Blob Storage, General Purpose V2, LRS Redundancy, Hot Access Tier, 1,024 GB Capacity",
     21.50, 0),
    ("Networking", "Bandwidth", "Shared | Internet egress | 1 TB", "",
     "Internet egress, 1024 GB outbound data transfer from West Europe", 87.04, 0),
    ("Analytics", "Microsoft Fabric", "Analytics | Fabric F64 | OneLake 1024 GB", "West Europe",
     "F64, 64 Capacity units x 730 Hours, OneLake hot storage 1,024 GB", 10327.00, 0),
]
for r in data:
    ws.append(list(r))

ws.append(["Support", "", "", "Support", "", 0, 0])
ws.append(["", "", "", "Licensing Program", "Microsoft Customer Agreement (MCA)"])
ws.append(["", "", "", "Total", "", round(sum(d[5] for d in data), 2), 0])
ws.append([])
ws.append(["Disclaimer"])
ws.append(["All prices shown are in United States - Dollar ($) USD."])

write(wb, "sample-exported-estimate.xlsx")

print("\nAll fixtures are synthetic. No customer data in this repository.")
