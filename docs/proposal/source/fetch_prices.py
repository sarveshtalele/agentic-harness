"""Fetch Azure Retail Prices (East US 2) for every meter the proposal uses, in USD and INR. Uses curl (system trust store)."""
import json, subprocess, sys, datetime
OUT = sys.argv[1]
Q = {
 "app_service": "armRegionName eq 'eastus2' and serviceName eq 'Azure App Service' and priceType eq 'Consumption' and (skuName eq 'B1' or skuName eq 'B2' or skuName eq 'B3' or skuName eq 'P0v3' or skuName eq 'P1v3')",
 "pg_compute": "armRegionName eq 'eastus2' and serviceName eq 'Azure Database for PostgreSQL' and priceType eq 'Consumption' and (skuName eq 'B1MS' or skuName eq 'B2S' or skuName eq 'B2ms')",
 "pg_storage": "armRegionName eq 'eastus2' and serviceName eq 'Azure Database for PostgreSQL' and priceType eq 'Consumption' and contains(meterName,'Storage')",
 "blob": "armRegionName eq 'eastus2' and serviceName eq 'Storage' and skuName eq 'Hot LRS' and productName eq 'Blob Storage' and priceType eq 'Consumption'",
 "key_vault": "armRegionName eq 'eastus2' and serviceName eq 'Key Vault' and skuName eq 'Standard' and meterName eq 'Operations'",
 "automation": "armRegionName eq 'eastus2' and serviceName eq 'Automation' and meterName eq 'Basic Runtime'",
 "bandwidth": "armRegionName eq 'eastus2' and serviceName eq 'Bandwidth' and productName eq 'Rtn Preference: MGN' and meterName eq 'Standard Data Transfer Out' and priceType eq 'Consumption'",
 "log_analytics": "armRegionName eq 'eastus2' and serviceName eq 'Log Analytics' and meterName eq 'Analytics Logs Data Ingestion' and priceType eq 'Consumption'",
}
data = {"fetched_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "items": {}}
for cur in ("USD", "INR"):
    for key, f in Q.items():
        items, url = [], None
        args = ["curl", "-sG", "https://prices.azure.com/api/retail/prices", "--data-urlencode", f"$filter={f}", "--data-urlencode", f"currencyCode={cur}"]
        while True:
            page = json.loads(subprocess.run(args if url is None else ["curl", "-s", url], capture_output=True, text=True, timeout=60, check=True).stdout)
            items += page["Items"]
            url = page.get("NextPageLink")
            if not url:
                break
        data["items"][f"{key}|{cur}"] = items
        print(cur, key, len(items))
json.dump(data, open(OUT, "w"), indent=1)
